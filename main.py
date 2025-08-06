import os
import pandas as pd
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import homogenize_latex_encoding
from tkinter import Tk, filedialog
import re

# Disable root Tk window
Tk().withdraw()

# Prompt for folder selection
folder_path = filedialog.askdirectory(title="Select Folder Containing BibTeX or CSV Files")
if not folder_path:
    print("❌ No folder selected.")
    exit()

# Get all file paths
all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

# Determine file type
csv_files = [f for f in all_files if f.lower().endswith(".csv")]
bib_files = [f for f in all_files if f.lower().endswith(".bib")]

# Validation
if csv_files and bib_files:
    print("❌ Mixed file types detected. Only one file type (CSV or BibTeX) is allowed.")
    exit()
elif not csv_files and not bib_files:
    print("❌ No supported files found.")
    exit()

REQUIRED_FIELDS = ['title', 'author', 'publication', 'doi', 'url']

def normalize_columns(df):
    column_mapping = {}
    for col in df.columns:
        cleaned = col.lower().replace(" ", "")
        for required in REQUIRED_FIELDS:
            if cleaned == required:
                column_mapping[col] = required
    return df.rename(columns=column_mapping)

def normalize_text(text):
    return re.sub(r'\s+', ' ', str(text).lower().strip())

def get_unique_key(entry, use_only_doi=False):
    if use_only_doi:
        return normalize_text(entry.get('doi', ''))
    return (
        normalize_text(entry.get('title', '')),
        normalize_text(entry.get('author', '')),
        normalize_text(entry.get('publication', '')),
        normalize_text(entry.get('doi', '')),
        normalize_text(entry.get('url', ''))
    )

unique_entries = {}
duplicate_count = 0
total_count = 0
file_entry_counts = {}

if csv_files:
    for file in csv_files:
        df = pd.read_csv(file)
        df = normalize_columns(df)

        if 'title' and 'author' and 'publication' and 'doi' and 'url' not in df.columns:
            print(f"❌ Error: CSV '{os.path.basename(file)}' must contain the following columns: {REQUIRED_FIELDS}")
            exit()

        file_total = 0
        for _, row in df.iterrows():
            total_count += 1
            file_total += 1
            key = get_unique_key(row, use_only_doi=False)
            if key not in unique_entries:
                unique_entries[key] = row
            else:
                duplicate_count += 1
        file_entry_counts[os.path.basename(file)] = file_total

    result_df = pd.DataFrame(unique_entries.values())
    output_file = os.path.join(folder_path, "deduplicated_output.csv")
    result_df.to_csv(output_file, index=False)
    output_type = "CSV"

else:
    for file in bib_files:
        with open(file, 'r', encoding='utf-8') as bibtex_file:
            parser = BibTexParser(common_strings=True)
            parser.customization = homogenize_latex_encoding
            bib_database = bibtexparser.load(bibtex_file, parser=parser)

            file_total = 0
            for entry in bib_database.entries:
                total_count += 1
                file_total += 1
                key = get_unique_key(entry, use_only_doi=False)
                if key not in unique_entries:
                    unique_entries[key] = entry
                else:
                    duplicate_count += 1
            file_entry_counts[os.path.basename(file)] = file_total

    output_file = os.path.join(folder_path, "deduplicated_output.bib")
    db = bibtexparser.bibdatabase.BibDatabase()
    db.entries = list(unique_entries.values())
    writer = bibtexparser.bwriter.BibTexWriter()
    with open(output_file, 'w', encoding='utf-8') as bibfile:
        bibfile.write(writer.write(db))
    output_type = "BibTeX"

# Write summary
summary_lines = [
    f"📄 File Type: {output_type}",
    f"📂 Folder: {folder_path}",
    "\n📑 Citations per file:"
]

for fname, count in file_entry_counts.items():
    summary_lines.append(f"   - {fname}: {count} citations")

summary_lines += [
    f"\n📊 Total Bibliography Entries: {total_count}",
    f"🔁 Duplicate Entries Removed: {duplicate_count}",
    f"✅ Unique Entries Saved: {len(unique_entries)}",
    f"📤 Output File: {os.path.basename(output_file)}"
]

summary = "\n".join(summary_lines)
summary_file = os.path.join(folder_path, "deduplication_summary.txt")
with open(summary_file, "w", encoding="utf-8") as f:
    f.write(summary)

print(summary)
