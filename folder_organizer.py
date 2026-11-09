#!/usr/bin/env python3
"""Folder Organizer - sort the files in a folder into subfolders by type or by date.

Examples:
    python folder_organizer.py "C:/Users/me/Downloads" --dry-run
    python folder_organizer.py ~/Downloads                 # Images/, Documents/, Video/ ...
    python folder_organizer.py ~/Downloads --by date       # 2026/2026-11/ ...
    python folder_organizer.py ~/Downloads --undo          # put everything back

Only files directly inside the folder are moved; existing subfolders are left alone.
Every move is written to .organizer_log.csv inside the folder, so --undo can reverse it.
Pure Python 3.9+, no extra packages.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import shutil
import sys
from pathlib import Path

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg", ".tif", ".tiff", ".ico"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".epub"},
    "Spreadsheets": {".xls", ".xlsx", ".xlsm", ".csv", ".ods", ".tsv"},
    "Presentations": {".ppt", ".pptx", ".odp", ".key"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Video": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".m4v"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".sql",
             ".sh", ".bat", ".ps1", ".ipynb", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".lua"},
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
}
OTHER = "Other"
LOG_NAME = ".organizer_log.csv"


def category_for(path: Path) -> str:
    ext = path.suffix.lower()
    for name, extensions in CATEGORIES.items():
        if ext in extensions:
            return name
    return OTHER


def date_folder(path: Path) -> Path:
    modified = dt.datetime.fromtimestamp(path.stat().st_mtime)
    return Path(f"{modified:%Y}") / f"{modified:%Y-%m}"


def unique_target(target: Path, taken: set[Path]) -> Path:
    """Return target, or 'name (1).ext', 'name (2).ext' ... if that name is already used."""
    candidate, n = target, 1
    while candidate.exists() or candidate in taken:
        candidate = target.with_name(f"{target.stem} ({n}){target.suffix}")
        n += 1
    return candidate


def plan_moves(folder: Path, by: str, include_hidden: bool) -> list[tuple[Path, Path]]:
    moves, taken = [], set()
    script = Path(__file__).resolve()
    for item in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_file() or item.name == LOG_NAME or item.resolve() == script:
            continue
        if not include_hidden and item.name.startswith("."):
            continue
        subfolder = Path(category_for(item)) if by == "type" else date_folder(item)
        target = unique_target(folder / subfolder / item.name, taken)
        taken.add(target)
        moves.append((item, target))
    return moves


def organize(folder: Path, by: str, dry_run: bool, include_hidden: bool) -> int:
    moves = plan_moves(folder, by, include_hidden)
    if not moves:
        print("Nothing to organize.")
        return 0
    for src, dst in moves:
        print(f"{'[dry-run] ' if dry_run else ''}{src.name}  ->  {dst.relative_to(folder)}")
    if dry_run:
        print(f"\n{len(moves)} file(s) would be moved. Run again without --dry-run to apply.")
        return 0
    log_path = folder / LOG_NAME
    new_log = not log_path.exists()
    stamp = dt.datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", newline="", encoding="utf-8") as log:
        writer = csv.writer(log)
        if new_log:
            writer.writerow(["time", "source", "target"])
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            writer.writerow([stamp, src.name, str(dst.relative_to(folder))])
    print(f"\nMoved {len(moves)} file(s). Undo with: --undo")
    return 0


def undo(folder: Path, dry_run: bool) -> int:
    log_path = folder / LOG_NAME
    if not log_path.exists():
        print(f"No {LOG_NAME} in {folder}, nothing to undo.")
        return 1
    with log_path.open(newline="", encoding="utf-8") as log:
        rows = list(csv.DictReader(log))
    restored, touched_dirs = 0, set()
    for row in reversed(rows):
        current = folder / row["target"]
        original = folder / row["source"]
        if not current.exists():
            print(f"skip (missing): {row['target']}")
            continue
        if original.exists():
            print(f"skip (a file named {row['source']} is back in the folder already)")
            continue
        print(f"{'[dry-run] ' if dry_run else ''}{row['target']}  ->  {row['source']}")
        if not dry_run:
            shutil.move(str(current), str(original))
            touched_dirs.add(current.parent)
        restored += 1
    if dry_run:
        return 0
    for directory in sorted(touched_dirs, key=lambda p: len(p.parts), reverse=True):
        while directory != folder and directory.exists() and not any(directory.iterdir()):
            directory.rmdir()
            directory = directory.parent
    log_path.unlink()
    print(f"\nRestored {restored} file(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sort files into subfolders by type or date.")
    parser.add_argument("folder", type=Path, help="folder to organize")
    parser.add_argument("--by", choices=["type", "date"], default="type",
                        help="type: Images/, Documents/ ...; date: YYYY/YYYY-MM/ by modification time")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing")
    parser.add_argument("--undo", action="store_true", help="move files back using the log")
    parser.add_argument("--include-hidden", action="store_true", help="also move files starting with a dot")
    args = parser.parse_args(argv)

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        parser.error(f"not a folder: {folder}")
    if args.undo:
        return undo(folder, args.dry_run)
    return organize(folder, args.by, args.dry_run, args.include_hidden)


if __name__ == "__main__":
    sys.exit(main())
