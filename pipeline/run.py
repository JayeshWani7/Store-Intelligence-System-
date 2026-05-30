"""CLI entrypoint for the detection pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from pipeline.detection_pipeline import DetectionPipeline
from pipeline.layout import load_layout


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CCTV detection pipeline.")
    parser.add_argument("--video", required=True, help="Path to CCTV clip.")
    parser.add_argument("--camera-id", required=True, help="Camera id for the clip.")
    parser.add_argument("--store-layout", default="store_layout.json", help="Layout JSON.")
    parser.add_argument("--store-id", default=None, help="Override store id.")
    parser.add_argument("--output", default="events.jsonl", help="Output JSONL file.")
    parser.add_argument("--start-time", default=None, help="ISO-8601 UTC start time.")
    parser.add_argument("--realtime", action="store_true", help="Sleep to match fps.")
    parser.add_argument("--dwell-interval", type=int, default=30, help="Dwell interval seconds.")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLOv8 model path.")
    parser.add_argument("--max-seconds", type=float, default=None, help="Stop after N seconds.")
    parser.add_argument("--max-frames", type=int, default=None, help="Stop after N frames.")
    parser.add_argument("--min-confidence", type=float, default=0.25, help="Min detection confidence.")
    parser.add_argument("--default-zone", default=None, help="Fallback zone id for unmatched detections.")
    parser.add_argument("--debug", action="store_true", help="Print debug stats while running.")
    parser.add_argument("--debug-every", type=int, default=30, help="Debug print every N frames.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    layout = load_layout(args.store_layout)

    start_time = (
        datetime.fromisoformat(args.start_time.replace("Z", "+00:00"))
        if args.start_time
        else datetime.now(timezone.utc)
    )

    pipeline = DetectionPipeline(
        layout=layout,
        store_id=args.store_id or layout.store_id,
        camera_id=args.camera_id,
        dwell_interval_seconds=args.dwell_interval,
        model_name=args.model,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        def on_event(event) -> None:
            handle.write(json.dumps(event.model_dump(mode="json")) + "\n")

        pipeline.run(
            video_path=args.video,
            start_time=start_time,
            realtime=args.realtime,
            on_event=on_event,
            max_seconds=args.max_seconds,
            max_frames=args.max_frames,
            min_confidence=args.min_confidence,
            default_zone_id=args.default_zone,
            debug=args.debug,
            debug_every=args.debug_every,
        )


if __name__ == "__main__":
    main()
