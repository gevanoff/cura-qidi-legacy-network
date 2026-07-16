#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SOURCE = REPO_ROOT / "cura_plugin" / "QidiLegacyNetwork"
PROTOCOL_SOURCE = REPO_ROOT / "src" / "qidi_legacy"


def stage_plugin(destination: Path, *, host: str, port: int) -> Path:
    host = host.strip()
    if not host or any(character.isspace() for character in host):
        raise ValueError("host must be a non-empty hostname or IP address without whitespace")
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")

    plugin_dir = destination / "QidiLegacyNetwork"
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)

    shutil.copytree(
        PLUGIN_SOURCE,
        plugin_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "config.json"),
    )
    shutil.copytree(
        PROTOCOL_SOURCE,
        plugin_dir / "qidi_legacy",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (plugin_dir / "config.json").write_text(
        json.dumps(
            {
                "host": host,
                "port": port,
                "timeout": 0.5,
                "retries": 3,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return plugin_dir


def install_plugin(cura_config: Path, *, host: str, port: int) -> Path:
    plugins_dir = cura_config / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return stage_plugin(plugins_dir, host=host, port=port)


def build_zip(output_path: Path, *, host: str, port: int) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cura-qidi-plugin-") as temporary:
        staged = stage_plugin(Path(temporary), host=host, port=port)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in sorted(staged.rglob("*")):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(staged.parent))
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install or package the QIDI Legacy Network plugin for Cura 5"
    )
    parser.add_argument("--host", required=True, help="QIDI printer hostname or IP address")
    parser.add_argument("--port", type=int, default=3000)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--cura-config",
        type=Path,
        help=(
            "Cura version configuration directory, for example "
            "/mnt/c/Users/name/AppData/Roaming/cura/5.13"
        ),
    )
    group.add_argument("--zip-out", type=Path, help="write an installable development ZIP")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.cura_config is not None:
        result = install_plugin(args.cura_config, host=args.host, port=args.port)
        print(f"Installed QIDI Legacy Network plugin at: {result}")
    else:
        result = build_zip(args.zip_out, host=args.host, port=args.port)
        print(f"Built QIDI Legacy Network plugin ZIP at: {result}")
    print("Close Cura before installing, then start Cura and slice a model to see the new actions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
