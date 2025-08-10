# 📚 SLR Automation

A Python-based utility to automatically detect and remove duplicate research entries from **BibTeX (.bib)** or **CSV (.csv)** files. Perfect for researchers, students, and librarians managing large bibliographic datasets for literature reviews, systematic reviews, or personal research libraries. Also, it searches several referral articles and matches with the inclusion and exclusion criteria. Lastly, it finalizes those final candidate articles that fit accurately.

---

## 🚀 Features

- ✅ **Supports CSV and BibTeX files** – Automatically detects the file type and handles accordingly.
- 🔍 **Accurate Duplicate Detection** – Matches entries based on normalized values of:
  - `title`
  - `author`
  - `publication`
  - `doi`
  - `url`
- 🧠 **Smart Normalization** – Case-insensitive, whitespace-tolerant, and LaTeX encoding handled using `bibtexparser`.
- 📂 **Folder Selection GUI** – Uses `tkinter` for a clean file selection interface.
- 📊 **Summary Report** – Outputs total entries, duplicates removed, and unique entries per file.
- 💾 **Clean Output Files** – Saves:
  - `deduplicated_output.csv` or `deduplicated_output.bib`
  - `deduplication_summary.txt`

---

## 🛠️ Requirements

- Python 3.x
- `pandas`
- `bibtexparser`
- `tkinter` (included in most Python installations)

You can install dependencies with:

```bash
pip install pandas bibtexparser
