# 🚀 JoshRenamer

> Batch-renames call recordings by matching them to a call log using timestamp proximity.

JoshRenamer is a Python desktop app that takes a folder of audio recordings with cryptic auto-generated filenames and renames each one to match the corresponding entry in an exported call log (TXT/CSV), by comparing timestamps.

Built with CustomTkinter, it walks through a simple 4-step flow — load data, select files, preview matches, confirm rename — with validation and logging along the way so nothing gets renamed blind.

---

## ✨ Features

- 📂 Load a structured TXT/CSV call log
- 📁 Select multiple audio files at once
- 🔍 Timestamp-based matching, with automatic 12-hour offset retry for AM/PM ambiguity in filenames
- 📊 Live preview table before anything is touched — unmatched files are flagged in-line, not just silently skipped
- ⚠️ Validation checks for stale previews, duplicate targets, and existing files before renaming
- ✅ Confirmation dialog before any rename actually runs
- 📜 Persistent logs window with timestamped history of every action and failure
- ❓ Built-in Help window with step-by-step screenshots
- 🔁 Reset to start a new batch without restarting the app

---

## 🧠 How Matching Works

1. Parse the call log — extract each entry's name, timestamp, and duration
2. Extract a timestamp from each audio filename
3. Find the closest call-log entry within a tolerance window
4. If nothing's close enough, retry the match 12 hours off (handles filenames that don't encode AM/PM)
5. Anything still unmatched is flagged `NO_MATCH_FOUND` and shown clearly in the preview — never renamed

---

## 🛠️ Tech Stack

- Python 3
- CustomTkinter — UI
- CTkTable — preview table rendering
- CTkMessagebox — confirmations & alerts
- Pillow — image handling (icon, logo, help screenshots)
- `csv` / `os` / `datetime` — parsing, file ops, timestamp math

---

## 📸 Preview

> *SOON

---

## ⚙️ Installation

```bash
pip install customtkinter
pip install CTkTable
pip install CTkMessagebox
pip install pillow
```

Then run:

```bash
python renamer.py
```

---

## 📁 Expected Folder Layout

```
project/
├── renamer.py
├── yourimage.png          # window icon / sidebar logo
└── help/
    ├── help_load_txt.png
    ├── help_select_files.png
    ├── help_preview.png
    └── help_rename.png
```

The `help/` images power the in-app Help window and aren't required for the app to run — without them it just shows a "screenshot missing" note instead of crashing.

---

## 🗒️ Notes

- Renaming only ever happens after an explicit confirmation — the app never overwrites an existing file, it skips it and logs a failure instead.