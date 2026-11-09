# Python File Tools

Two small command-line tools for messy folders. **Pure Python 3.9+, nothing to install.** Windows, macOS and Linux.

| Tool | What it does |
|---|---|
| `folder_organizer.py` | Sorts a messy folder (Downloads, Desktop) into Images, Documents, Video... or into Year/Month folders. One command to undo. |
| `bulk_renamer.py` | Renames hundreds of files with a template, numbering, find & replace or regex. Preview first, undo included. |

Nothing is ever deleted, and both tools keep an undo log.

## Quick start
1. Install Python from [python.org](https://www.python.org/downloads/) (Windows: tick **"Add python.exe to PATH"**).
2. Download this repository (green **Code** button → **Download ZIP**) and unzip it.
3. Open a terminal in the folder and run:

```bash
# sort Downloads by file type: preview, do it, undo it
python folder_organizer.py "C:/Users/me/Downloads" --dry-run
python folder_organizer.py "C:/Users/me/Downloads"
python folder_organizer.py "C:/Users/me/Downloads" --undo

# or by date: 2026/2026-11/...
python folder_organizer.py ~/Downloads --by date

# rename photos to trip_001.jpg, trip_002.jpg ... (preview first, then --apply)
python bulk_renamer.py ./photos --glob "*.jpg" --template "trip_{n:03}{ext}"
python bulk_renamer.py ./photos --glob "*.jpg" --template "trip_{n:03}{ext}" --apply
python bulk_renamer.py ./photos --undo --apply
```

Every script has `--help` with all options.

## Need more automation?
The **[Python Automation Starter Pack](https://whop.com/chaboss/products/python-automation-starter-pack-ba/)**
($9) adds four more tools in the same style:

- **Report Builder:** CSV/Excel to a summary report in Excel, a pivot table without Excel.
- **CSV Cleaner:** duplicates, empty rows, stray spaces, broken e-mails.
- **Duplicate Finder:** identical files by content, shows the wasted space.
- **Site Monitor:** price, stock or page-change alerts to Telegram.

More ready-made code (Telegram and Discord bot templates, TradingView indicators, a Roblox starter kit) is in the
**[Chaboss Dev Kits](https://whop.com/chaboss/)** store.

## License
MIT. Use, change and share freely.
