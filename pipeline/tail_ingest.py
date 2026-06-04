"""
tail_ingest.py – Tail events.jsonl and POST each new line to /events/ingest.

Usage:
    python -m pipeline.tail_ingest                        # defaults
    python -m pipeline.tail_ingest --file events.jsonl --api http://localhost:8000 --batch 20

Run this alongside the pipeline and the FastAPI server so that events flow
from the CCTV pipeline → events.jsonl → API → SSE dashboard in real-time.

It also supports a one-shot replay mode (--replay) that ingests the entire
existing file from the top without tailing for new lines.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

import urllib.request
import urllib.error


def _post_batch(api_base: str, events: List[Dict[str, Any]], verbose: bool) -> None:
    url = f"{api_base.rstrip('/')}/events/ingest"
    body = json.dumps({"events": events}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if verbose:
                print(
                    f"  → accepted={result.get('accepted')} "
                    f"rejected={result.get('rejected')} "
                    f"errors={result.get('errors', [])}"
                )
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        print(f"[tail_ingest] HTTP {exc.code}: {body_text[:200]}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[tail_ingest] POST failed: {exc}", file=sys.stderr)


def _wait_for_api(api_base: str, timeout: int = 30) -> bool:
    """Block until /health returns 200 or timeout expires."""
    url = f"{api_base.rstrip('/')}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3):
                return True
        except Exception:  # noqa: BLE001
            print("[tail_ingest] Waiting for API…", file=sys.stderr)
            time.sleep(2)
    return False


def tail(
    file_path: Path,
    api_base: str,
    batch_size: int = 50,
    poll_interval: float = 0.5,
    verbose: bool = True,
    replay: bool = False,
) -> None:
    if not _wait_for_api(api_base):
        print(f"[tail_ingest] API at {api_base} not reachable after 30s. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"[tail_ingest] Connected to {api_base}")
    print(f"[tail_ingest] {'Replaying' if replay else 'Tailing'} {file_path}")

    pending: List[Dict[str, Any]] = []
    total_sent = 0

    with file_path.open("r", encoding="utf-8") as fh:
        # Seek to end for tail mode (skip existing lines)
        if not replay:
            fh.seek(0, 2)  # seek to EOF
            print("[tail_ingest] Seeked to end of file – waiting for new events…")

        while True:
            line = fh.readline()
            if not line:
                # No new data
                if replay:
                    # Flush remaining and exit
                    if pending:
                        _post_batch(api_base, pending, verbose)
                        total_sent += len(pending)
                        pending = []
                    print(f"[tail_ingest] Replay complete. Sent {total_sent} events.")
                    return
                # Flush any partial batch then wait
                if pending:
                    _post_batch(api_base, pending, verbose)
                    total_sent += len(pending)
                    if verbose:
                        print(f"[tail_ingest] Flushed {len(pending)} events (total {total_sent})")
                    pending = []
                time.sleep(poll_interval)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                pending.append(event)
            except json.JSONDecodeError as exc:
                print(f"[tail_ingest] Bad JSON line: {exc}", file=sys.stderr)
                continue

            if len(pending) >= batch_size:
                _post_batch(api_base, pending, verbose)
                total_sent += len(pending)
                if verbose:
                    print(f"[tail_ingest] Sent batch of {len(pending)} (total {total_sent})")
                pending = []


def main() -> None:
    parser = argparse.ArgumentParser(description="Tail events.jsonl → POST to API")
    parser.add_argument("--file",     default="events.jsonl",       help="JSONL file to tail")
    parser.add_argument("--api",      default="http://localhost:8000", help="FastAPI base URL")
    parser.add_argument("--batch",    type=int, default=50,          help="Max events per POST")
    parser.add_argument("--interval", type=float, default=0.5,       help="Poll interval in seconds")
    parser.add_argument("--replay",   action="store_true",           help="Ingest entire file from top and exit")
    parser.add_argument("--quiet",    action="store_true",           help="Suppress per-batch output")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        # Create empty file so tail can open it immediately
        file_path.touch()
        print(f"[tail_ingest] Created {file_path} (empty)")

    tail(
        file_path=file_path,
        api_base=args.api,
        batch_size=args.batch,
        poll_interval=args.interval,
        verbose=not args.quiet,
        replay=args.replay,
    )


if __name__ == "__main__":
    main()
