#!/usr/bin/env python3
"""Bulk Renamer - rename many files at once with a preview and an undo.

Nothing is renamed until you add --apply. Without it you only see the preview.

Examples:
    python bulk_renamer.py ./photos --glob "*.jpg" --template "trip_{n:03}{ext}"
    python bulk_renamer.py ./photos --glob "*.jpg" --template "trip_{n:03}{ext}" --apply
    python bulk_renamer.py ./docs --replace " " "_" --case lower --apply
    python bulk_renamer.py ./docs --regex "^IMG_(\\d+)" "photo-\\1" --apply
    python bulk_renamer.py ./photos --undo

Template placeholders: {name} (name without extension), {ext} (with the dot), {n} (counter),
{date} (file date, YYYY-MM-DD), {parent} (folder name). Format specs work: {n:03} -> 001.
Steps run in this order: template, regex, replace, prefix/suffix, case.
Pure Python 3.9+, no extra packages.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import uuid
from pathlib import Path

LOG_NAME = ".renamer_log.csv"


def collect(folder: Path, pattern: str, sort: str) -> list[Path]:
    files = [p for p in folder.glob(pattern) if p.is_file() and p.name != LOG_NAME]
    keys = {
        "name": lambda p: p.name.lower(),
        "date": lambda p: p.stat().st_mtime,
        "size": lambda p: p.stat().st_size,
    }
    return sorted(files, key=keys[sort])


def new_name(path: Path, index: int, args: argparse.Namespace) -> str:
    stem, ext = path.stem, path.suffix
    if args.template:
        date = dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        result = args.template.format(name=stem, ext=ext, n=index, date=date, parent=path.parent.name)
        stem, ext = Path(result).stem, Path(result).suffix
    if args.regex:
        stem = re.sub(args.regex[0], args.regex[1], stem)
    for old, new in args.replace or []:
        stem = stem.replace(old, new)
    stem = f"{args.prefix}{stem}{args.suffix}"
    if args.case == "lower":
        stem, ext = stem.lower(), ext.lower()
    elif args.case == "upper":
        stem = stem.upper()
    elif args.case == "title":
        stem = stem.title()
    return f"{stem}{ext}"


def build_plan(files: list[Path], args: argparse.Namespace) -> list[tuple[Path, Path]]:
    plan = []
    for i, path in enumerate(files, start=args.start):
        target = path.with_name(new_name(path, i, args))
        if target != path:
            plan.append((path, target))
    return plan


def check_plan(plan: list[tuple[Path, Path]]) -> list[str]:
    problems, sources = [], {src for src, _ in plan}
    seen: dict[str, Path] = {}
    for src, dst in plan:
        key = str(dst).lower()  # Windows and macOS treat names case-insensitively
        if key in seen:
            problems.append(f"two files would become {dst.name}: {seen[key].name} and {src.name}")
        seen[key] = src
        if not dst.name or dst.name in {".", ".."}:
            problems.append(f"empty name for {src.name}")
        same_file = str(dst).lower() == str(src).lower()
        if dst.exists() and dst not in sources and not same_file:
            problems.append(f"{dst.name} already exists (from {src.name})")
    return problems


def apply_plan(folder: Path, plan: list[tuple[Path, Path]]) -> None:
    # Two passes through temporary names, so swaps (a->b, b->a) and case-only renames work.
    temps = []
    for src, dst in plan:
        temp = src.with_name(f".tmp-{uuid.uuid4().hex}{src.suffix}")
        src.rename(temp)
        temps.append((temp, src, dst))
    log_path = folder / LOG_NAME
    new_log = not log_path.exists()
    stamp = dt.datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", newline="", encoding="utf-8") as log:
        writer = csv.writer(log)
        if new_log:
            writer.writerow(["time", "old", "new"])
        for temp, src, dst in temps:
            temp.rename(dst)
            writer.writerow([stamp, str(src.relative_to(folder)), str(dst.relative_to(folder))])


def undo(folder: Path, apply: bool) -> int:
    log_path = folder / LOG_NAME
    if not log_path.exists():
        print(f"No {LOG_NAME} in {folder}, nothing to undo.")
        return 1
    with log_path.open(newline="", encoding="utf-8") as log:
        rows = list(csv.DictReader(log))
    plan = [(folder / r["new"], folder / r["old"]) for r in reversed(rows) if (folder / r["new"]).exists()]
    for src, dst in plan:
        print(f"{src.name}  ->  {dst.name}")
    if not apply:
        print(f"\n{len(plan)} file(s) would be restored. Add --apply to do it.")
        return 0
    problems = check_plan(plan)
    if problems:
        print("\nCannot undo:\n  " + "\n  ".join(problems))
        return 1
    for src, dst in plan:
        temp = src.with_name(f".tmp-{uuid.uuid4().hex}{src.suffix}")
        src.rename(temp)
        temp.rename(dst)
    log_path.unlink()
    print(f"\nRestored {len(plan)} file(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rename many files at once (preview first, then --apply).")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--glob", default="*", help='which files, e.g. "*.jpg" (default: all files)')
    parser.add_argument("--sort", choices=["name", "date", "size"], default="name",
                        help="order used for the {n} counter")
    parser.add_argument("--template", help='new name pattern, e.g. "photo_{n:03}{ext}"')
    parser.add_argument("--start", type=int, default=1, help="first value of {n} (default 1)")
    parser.add_argument("--regex", nargs=2, metavar=("PATTERN", "REPLACEMENT"), help="regex replace in the name")
    parser.add_argument("--replace", nargs=2, action="append", metavar=("OLD", "NEW"), help="plain text replace")
    parser.add_argument("--prefix", default="", help="text to add at the start")
    parser.add_argument("--suffix", default="", help="text to add before the extension")
    parser.add_argument("--case", choices=["lower", "upper", "title"], help="change letter case")
    parser.add_argument("--apply", action="store_true", help="actually rename (otherwise preview only)")
    parser.add_argument("--undo", action="store_true", help="reverse the renames saved in the log")
    args = parser.parse_args(argv)

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        parser.error(f"not a folder: {folder}")
    if args.undo:
        return undo(folder, args.apply)
    if not any([args.template, args.regex, args.replace, args.prefix, args.suffix, args.case]):
        parser.error("say what to change: --template, --regex, --replace, --prefix, --suffix or --case")

    try:
        plan = build_plan(collect(folder, args.glob, args.sort), args)
    except (KeyError, IndexError, ValueError) as exc:
        parser.error(f"bad template: {exc}")
    except re.error as exc:
        parser.error(f"bad regex: {exc}")
    if not plan:
        print("No file names would change.")
        return 0
    for src, dst in plan:
        print(f"{src.name}  ->  {dst.name}")
    problems = check_plan(plan)
    if problems:
        print("\nStopped, nothing renamed:\n  " + "\n  ".join(problems))
        return 1
    if not args.apply:
        print(f"\n{len(plan)} file(s) would be renamed. Add --apply to do it.")
        return 0
    apply_plan(folder, plan)
    print(f"\nRenamed {len(plan)} file(s). Undo with: --undo --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
