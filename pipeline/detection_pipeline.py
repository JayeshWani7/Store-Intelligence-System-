"""Realtime detection pipeline for CCTV clips."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from pipeline.event_schema import DetectionEvent
from pipeline.layout import Layout, Zone


@dataclass
class TrackState:
    visitor_id: str
    in_store: bool = False
    current_zone_id: Optional[str] = None
    last_zone_ts: Optional[datetime] = None
    last_dwell_emit: Optional[datetime] = None
    session_seq: int = 0
    exited_at: Optional[datetime] = None
    in_billing_queue: bool = False


class DetectionPipeline:
    def __init__(
        self,
        layout: Layout,
        store_id: str,
        camera_id: str,
        entry_zone_id: str = "ENTRY_THRESHOLD",
        billing_queue_zone_id: str = "BILLING_QUEUE",
        dwell_interval_seconds: int = 30,
        model_name: str = "yolov8n.pt",
    ) -> None:
        self.layout = layout
        self.store_id = store_id
        self.camera_id = camera_id
        self.entry_zone_id = entry_zone_id
        self.billing_queue_zone_id = billing_queue_zone_id
        self.dwell_interval = timedelta(seconds=dwell_interval_seconds)
        self.model_name = model_name

    def run(
        self,
        video_path: str,
        start_time: datetime,
        realtime: bool = False,
        on_event: Optional[callable] = None,
        max_seconds: Optional[float] = None,
        max_frames: Optional[int] = None,
        min_confidence: float = 0.25,
        default_zone_id: Optional[str] = None,
        debug: bool = False,
        debug_every: int = 30,
        ocr_timestamp: bool = False,
        ocr_region: Optional[tuple[int, int, int, int]] = None,
        ocr_every: int = 30,
        ocr_dump_path: Optional[str] = None,
    ) -> List[DetectionEvent]:
        import cv2
        import numpy as np
        import supervision as sv
        from ultralytics import YOLO

        model = YOLO(self.model_name)
        tracker = sv.ByteTrack()

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_idx = 0
        events: List[DetectionEvent] = []
        track_states: Dict[int, TrackState] = {}
        ocr_reader = None
        last_ocr_text: Optional[str] = None
        last_ocr_time: Optional[datetime] = None
        last_ocr_frame_idx: Optional[int] = None
        ocr_dumped = False

        def emit(event: DetectionEvent) -> None:
            events.append(event)
            if on_event:
                on_event(event)

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if max_frames is not None and frame_idx >= max_frames:
                break

            if max_seconds is not None and (frame_idx / fps) >= max_seconds:
                break

            timestamp = start_time + timedelta(seconds=frame_idx / fps)
            frame_idx += 1

            if ocr_timestamp and frame_idx % max(ocr_every, 1) == 0:
                if ocr_reader is None:
                    import easyocr

                    ocr_reader = easyocr.Reader(["en"], gpu=False)
                ocr_text, ocr_crop = _extract_timestamp_text(
                    frame,
                    ocr_reader,
                    region=ocr_region,
                )
                if ocr_dump_path and not ocr_dumped and ocr_crop is not None:
                    import cv2

                    cv2.imwrite(ocr_dump_path, ocr_crop)
                    ocr_dumped = True
                last_ocr_text = ocr_text or last_ocr_text
                parsed = _parse_timestamp_text(last_ocr_text)
                if parsed is not None:
                    last_ocr_time = parsed
                    last_ocr_frame_idx = frame_idx
                if debug:
                    print(f"ocr_text='{ocr_text}' parsed={parsed}")

            if last_ocr_time is not None and last_ocr_frame_idx is not None:
                offset_seconds = (frame_idx - last_ocr_frame_idx) / fps
                timestamp = last_ocr_time + timedelta(seconds=offset_seconds)

            results = model(frame, verbose=False)[0]
            if results.boxes is None or len(results.boxes) == 0:
                if realtime:
                    _sleep_frame(fps)
                continue

            xyxy = results.boxes.xyxy.cpu().numpy()
            conf = results.boxes.conf.cpu().numpy()
            cls = results.boxes.cls.cpu().numpy().astype(int)

            person_mask = cls == 0
            xyxy = xyxy[person_mask]
            conf = conf[person_mask]
            cls = cls[person_mask]

            if min_confidence is not None:
                conf_mask = conf >= min_confidence
                xyxy = xyxy[conf_mask]
                conf = conf[conf_mask]
                cls = cls[conf_mask]

            if xyxy.size == 0:
                if realtime:
                    _sleep_frame(fps)
                continue

            detections = sv.Detections(
                xyxy=xyxy,
                confidence=conf,
                class_id=cls,
            )
            tracked = tracker.update_with_detections(detections)

            default_zone = (
                self.layout.zones_by_id.get(default_zone_id)
                if default_zone_id
                else None
            )
            zone_by_track: Dict[int, Optional[Zone]] = {}
            for box, track_id, confidence in zip(
                tracked.xyxy, tracked.tracker_id, tracked.confidence
            ):
                if track_id is None:
                    continue
                cx = float((box[0] + box[2]) / 2)
                cy = float((box[1] + box[3]) / 2)
                zone = self.layout.zone_for_point((cx, cy)) or default_zone
                zone_by_track[int(track_id)] = zone

            queue_depth = sum(
                1
                for zone in zone_by_track.values()
                if zone is not None and zone.zone_id == self.billing_queue_zone_id
            )

            for track_id, zone in zone_by_track.items():
                state = track_states.get(track_id)
                if state is None:
                    state = TrackState(visitor_id=f"VIS_{track_id}")
                    track_states[track_id] = state

                self._handle_track(
                    state=state,
                    zone=zone,
                    confidence=_confidence_for_track(tracked, track_id),
                    timestamp=timestamp,
                    queue_depth=queue_depth,
                    emit=emit,
                )

            if realtime:
                _sleep_frame(fps)

            if debug and frame_idx % max(debug_every, 1) == 0:
                matched = sum(1 for zone in zone_by_track.values() if zone is not None)
                print(
                    f"frame={frame_idx} detections={len(detections)} tracks={len(zone_by_track)} "
                    f"matched_zones={matched} queue_depth={queue_depth}"
                )

        cap.release()
        return events

    def _handle_track(
        self,
        state: TrackState,
        zone: Optional[Zone],
        confidence: float,
        timestamp: datetime,
        queue_depth: int,
        emit: callable,
    ) -> None:
        zone_id = zone.zone_id if zone else None
        previous_zone = state.current_zone_id

        if zone_id == self.entry_zone_id and not state.in_store:
            event_type = "REENTRY" if state.exited_at else "ENTRY"
            self._emit_event(
                emit=emit,
                state=state,
                event_type=event_type,
                timestamp=timestamp,
                zone_id=None,
                confidence=confidence,
                metadata={"session_seq": state.session_seq + 1},
            )
            state.in_store = True
            state.exited_at = None
            state.current_zone_id = zone_id
            state.last_zone_ts = timestamp
            return

        if zone_id == self.entry_zone_id and state.in_store and previous_zone != self.entry_zone_id:
            self._emit_event(
                emit=emit,
                state=state,
                event_type="EXIT",
                timestamp=timestamp,
                zone_id=None,
                confidence=confidence,
                metadata={"session_seq": state.session_seq + 1},
            )
            state.in_store = False
            state.exited_at = timestamp
            state.current_zone_id = zone_id
            state.last_zone_ts = timestamp
            state.in_billing_queue = False
            return

        if zone_id != previous_zone:
            if previous_zone and previous_zone != self.entry_zone_id:
                self._emit_event(
                    emit=emit,
                    state=state,
                    event_type="ZONE_EXIT",
                    timestamp=timestamp,
                    zone_id=previous_zone,
                    confidence=confidence,
                    metadata={"session_seq": state.session_seq + 1},
                )

            if zone_id and zone_id != self.entry_zone_id:
                self._emit_event(
                    emit=emit,
                    state=state,
                    event_type="ZONE_ENTER",
                    timestamp=timestamp,
                    zone_id=zone_id,
                    confidence=confidence,
                    metadata={"session_seq": state.session_seq + 1},
                )
                state.last_zone_ts = timestamp
                state.last_dwell_emit = timestamp

            if zone_id == self.billing_queue_zone_id:
                if queue_depth > 0:
                    self._emit_event(
                        emit=emit,
                        state=state,
                        event_type="BILLING_QUEUE_JOIN",
                        timestamp=timestamp,
                        zone_id=zone_id,
                        confidence=confidence,
                        metadata={
                            "queue_depth": queue_depth,
                            "session_seq": state.session_seq + 1,
                        },
                    )
                state.in_billing_queue = True
            elif previous_zone == self.billing_queue_zone_id and state.in_billing_queue:
                self._emit_event(
                    emit=emit,
                    state=state,
                    event_type="BILLING_QUEUE_ABANDON",
                    timestamp=timestamp,
                    zone_id=previous_zone,
                    confidence=confidence,
                    metadata={
                        "queue_depth": queue_depth,
                        "session_seq": state.session_seq + 1,
                    },
                )
                state.in_billing_queue = False

            state.current_zone_id = zone_id

        if zone_id and zone_id == state.current_zone_id and zone_id != self.entry_zone_id:
            if state.last_dwell_emit and timestamp - state.last_dwell_emit >= self.dwell_interval:
                self._emit_event(
                    emit=emit,
                    state=state,
                    event_type="ZONE_DWELL",
                    timestamp=timestamp,
                    zone_id=zone_id,
                    confidence=confidence,
                    dwell_ms=int(self.dwell_interval.total_seconds() * 1000),
                    metadata={
                        "sku_zone": zone.label if zone else zone_id,
                        "session_seq": state.session_seq + 1,
                    },
                )
                state.last_dwell_emit = timestamp

    def _emit_event(
        self,
        emit: callable,
        state: TrackState,
        event_type: str,
        timestamp: datetime,
        zone_id: Optional[str],
        confidence: float,
        metadata: Optional[Dict[str, object]] = None,
        dwell_ms: int = 0,
    ) -> None:
        state.session_seq += 1
        event = DetectionEvent(
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=state.visitor_id,
            event_type=event_type,
            timestamp=timestamp,
            zone_id=zone_id,
            dwell_ms=dwell_ms,
            is_staff=False,
            confidence=float(confidence),
            metadata=metadata or {},
        )
        emit(event)


def _confidence_for_track(tracked, track_id: int) -> float:
    for tid, confidence in zip(tracked.tracker_id, tracked.confidence):
        if tid == track_id:
            return float(confidence)
    return 0.0


def _sleep_frame(fps: float) -> None:
    import time

    delay = 1.0 / max(fps, 1.0)
    time.sleep(delay)


def _extract_timestamp_text(
    frame,
    reader,
    region: Optional[tuple[int, int, int, int]] = None,
) -> tuple[str, Optional[object]]:
    import cv2

    height, width = frame.shape[:2]
    if region is None:
        # Default to top-right 25% width and 15% height
        x = int(width * 0.75)
        y = int(height * 0.0)
        w = int(width * 0.25)
        h = int(height * 0.15)
    else:
        x, y, w, h = region

    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width - x))
    h = max(1, min(h, height - y))

    crop = frame[y : y + h, x : x + w]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return " ".join(reader.readtext(gray, detail=0)), crop


def _parse_timestamp_text(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None

    import re
    from datetime import timezone

    cleaned = (
        text.replace("|", ":")
        .replace(";", ":")
        .replace("*", ":")
        .replace("'", "")
        .replace("O", "0")
        .replace("o", "0")
        .replace("S", "5")
        .strip()
    )

    # Fix OCR variant: '10/0412026' -> '10/04/2026' (extra '1' between month and year).
    cleaned = re.sub(r"(\d{2})/(\d{2})1(\d{4})", r"\1/\2/\3", cleaned)
    # Fix OCR variant: '10/042026' -> '10/04/2026' (missing slash before year).
    cleaned = re.sub(r"(\d{2})/(\d{2})(\d{4})", r"\1/\2/\3", cleaned)
    # Normalize time separators like '20:09.45' -> '20:09:45'.
    cleaned = re.sub(r"(\d{2}:\d{2})[\.:](\d{2})", r"\1:\2", cleaned)

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
