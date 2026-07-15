from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .client import QidiLegacyClient
from .discovery import discover
from .exceptions import QidiError


def _client(args: argparse.Namespace) -> QidiLegacyClient:
    return QidiLegacyClient(args.host, port=args.port, timeout=args.timeout, retries=args.retries)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe and use a legacy QIDI network printer")
    subparsers = parser.add_subparsers(dest="action", required=True)

    discovery = subparsers.add_parser("discover", help="broadcast-discover compatible printers")
    discovery.add_argument("--port", type=int, default=3000)
    discovery.add_argument("--duration", type=float, default=3.0)

    for name in ("probe", "status", "upload"):
        command = subparsers.add_parser(name)
        command.add_argument("host")
        command.add_argument("--port", type=int, default=3000)
        command.add_argument("--timeout", type=float, default=0.5)
        command.add_argument("--retries", type=int, default=3)
        if name == "upload":
            command.add_argument("file")
            command.add_argument("--remote-name")
            command.add_argument(
                "--start",
                action="store_true",
                help="start printing after upload; omitted by default for safety",
            )
    return parser


def run(args: argparse.Namespace) -> dict[str, object] | list[dict[str, object]]:
    if args.action == "discover":
        return [asdict(item) for item in discover(port=args.port, duration=args.duration)]

    with _client(args) as client:
        handshake = client.connect()
        if args.action == "probe":
            return {"handshake": asdict(handshake), "firmware": client.firmware_version()}
        if args.action == "status":
            return asdict(client.status())

        def progress(done: int, total: int) -> None:
            print(f"uploaded {done}/{total} bytes", file=sys.stderr, flush=True)

        remote = client.upload_file(args.file, remote_filename=args.remote_name, progress=progress)
        result: dict[str, object] = {"uploaded": remote, "started": False}
        if args.start:
            result["start_response"] = client.start_print(remote)
            result["started"] = True
        return result


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except (QidiError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
