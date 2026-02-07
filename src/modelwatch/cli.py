"""Command-line interface for catalog export and copied-text cleaning."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .catalog import fetch_catalog, free_models, parse_catalog, write_export
from .cleaner import clean_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modelwatch")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Fetch and export zero-priced catalog entries")
    fetch.add_argument("--out-dir", type=Path, required=True)
    export = commands.add_parser("export", help="Export zero-priced entries from a local catalog JSON file")
    export.add_argument("input", type=Path)
    export.add_argument("--out-dir", type=Path, required=True)
    export.add_argument(
        "--generated-at",
        type=_parse_timestamp,
        help="ISO-8601 timestamp for deterministic filenames (for example 2026-01-01T00:00:00Z)",
    )
    clean = commands.add_parser("clean", help="Clean a supported copied-text catalog")
    clean.add_argument("input", type=Path)
    clean.add_argument("output", type=Path)
    return parser


def _parse_timestamp(value: str) -> datetime:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("generated-at must be an ISO-8601 timestamp") from exc
    if moment.tzinfo is None:
        raise argparse.ArgumentTypeError("generated-at must include a timezone")
    return moment


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "fetch":
        models = free_models(fetch_catalog())
        json_path, markdown_path = write_export(models, args.out_dir)
        print(f"Wrote {len(models)} models to {json_path} and {markdown_path}")
        return 0
    if args.command == "export":
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        models = free_models(parse_catalog(payload))
        json_path, markdown_path = write_export(models, args.out_dir, now=args.generated_at)
        print(f"Wrote {len(models)} models to {json_path} and {markdown_path}")
        return 0
    raw = args.input.read_text(encoding="utf-8", errors="replace")
    if not raw.strip():
        raise SystemExit("input is empty")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(clean_text(raw), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0
