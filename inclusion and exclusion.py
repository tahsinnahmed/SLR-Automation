import os
import pandas as pd
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import homogenize_latex_encoding
from tkinter import Tk, filedialog
import re
from datetime import datetime
import requests
import time
from urllib.parse import urlparse
from collections import defaultdict

# Disable root Tk window
Tk().withdraw()

# Prompt for folder selection
folder_path = filedialog.askdirectory(title="Select Folder Containing BibTeX or CSV Files")
if not folder_path:
    print("❌ No folder selected.")
    exit()

# Ask user for the starting year
start_year_input = input("Enter the starting publication year (e.g., 2020): ").strip()
if not start_year_input.isdigit():
    print("❌ Invalid year input.")
    exit()

start_year = int(start_year_input)
current_year = datetime.now().year

# Get files
all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
             os.path.isfile(os.path.join(folder_path, f))]

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


def get_publication_type(doi):
    """Fetch publication type from Crossref API using DOI"""
    if not doi or pd.isna(doi):
        return "Unknown"

    # Clean DOI (remove URL parts if present)
    if doi.startswith(('http://', 'https://')):
        parsed = urlparse(doi)
        doi = parsed.path.lstrip('/')

    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        data = response.json()

        # Get publication type and normalize it
        pub_type = data['message'].get('type', 'unknown').lower()

        # Map Crossref types to our categories
        if pub_type in ['journal-article', 'article']:
            return "Original Research"
        elif pub_type in ['proceedings-article', 'conference-paper', 'conference']:
            return "Conference Paper"
        else:
            return "Other"

    except requests.exceptions.RequestException:
        return "Unknown"
    except (KeyError, ValueError):
        return "Unknown"


def normalize_columns(df):
    return {col.lower().strip().replace(" ", ""): col for col in df.columns}


filtered_entries = []
file_stats = {}
total_found = 0
total_filtered = 0
publication_types = defaultdict(int)

if csv_files:
    for file in csv_files:
        df = pd.read_csv(file)
        columns = normalize_columns(df)

        # Find relevant columns
        year_col = None
        doi_col = None
        type_col = None

        for key in columns:
            if 'year' in key:
                year_col = columns[key]
            elif 'doi' in key:
                doi_col = columns[key]
            elif 'type' in key or 'publicationtype' in key:
                type_col = columns[key]

        if not year_col:
            print(f"❌ No 'year' column found in {file}")
            continue

        df[year_col] = pd.to_numeric(df[year_col], errors='coerce')

        total_refs = len(df)
        # First filter by year
        year_filtered = df[(df[year_col] >= start_year) & (df[year_col] <= current_year)].copy()

        final_filtered = []
        for _, row in year_filtered.iterrows():
            pub_type = "Unknown"

            # First try to get type from DOI
            if doi_col and pd.notna(row[doi_col]):
                pub_type = get_publication_type(row[doi_col])
                time.sleep(0.5)  # Be polite to API

            # If still unknown, try to get from type column
            if pub_type == "Unknown" and type_col and pd.notna(row[type_col]):
                type_str = str(row[type_col]).lower()
                if 'journal' in type_str or 'article' in type_str:
                    pub_type = "Original Research"
                elif 'conference' in type_str or 'proceeding' in type_str:
                    pub_type = "Conference Paper"

            publication_types[pub_type] += 1

            if pub_type in ['Original Research', 'Conference Paper']:
                final_filtered.append(row)

        filtered_refs = len(final_filtered)

        if filtered_refs > 0:
            filtered_df = pd.DataFrame(final_filtered)
            filtered_entries.append(filtered_df)
            file_stats[os.path.basename(file)] = {
                'total': total_refs,
                'filtered': filtered_refs,
                'ignored': total_refs - filtered_refs
            }
            total_found += total_refs
            total_filtered += filtered_refs

    if filtered_entries:
        result_df = pd.concat(filtered_entries, ignore_index=True)
        output_file = os.path.join(folder_path, f"Included File.csv")
        result_df.to_csv(output_file, index=False)
        output_type = "CSV"
    else:
        print("⚠️ No references matched your filters.")
        exit()

else:  # BibTeX files
    for file in bib_files:
        with open(file, 'r', encoding='utf-8') as bibtex_file:
            parser = BibTexParser(common_strings=True)
            parser.customization = homogenize_latex_encoding
            bib_database = bibtexparser.load(bibtex_file, parser=parser)

            entries = bib_database.entries
            total_refs = len(entries)

            filtered = []
            for entry in entries:
                try:
                    year = int(entry.get('year', '').strip())
                    if start_year <= year <= current_year:
                        # Get publication type if DOI exists
                        doi = entry.get('doi', '')
                        if doi:
                            pub_type = get_publication_type(doi)
                            publication_types[pub_type] += 1

                            # Only include if it's Original Research or Conference Paper
                            if pub_type in ['Original Research', 'Conference Paper']:
                                entry['publication_type'] = pub_type
                                filtered.append(entry)

                            time.sleep(0.5)
                        else:
                            # If no DOI, we can't determine type, so exclude it
                            publication_types['No DOI'] += 1
                except ValueError:
                    continue

            filtered_refs = len(filtered)

            if filtered_refs > 0:
                filtered_entries.extend(filtered)
                file_stats[os.path.basename(file)] = {
                    'total': total_refs,
                    'filtered': filtered_refs,
                    'ignored': total_refs - filtered_refs
                }
                total_found += total_refs
                total_filtered += filtered_refs

    if filtered_entries:
        output_file = os.path.join(folder_path, f"Included File.bib")
        db = bibtexparser.bibdatabase.BibDatabase()
        db.entries = filtered_entries
        writer = bibtexparser.bwriter.BibTexWriter()
        with open(output_file, 'w', encoding='utf-8') as bibfile:
            bibfile.write(writer.write(db))
        output_type = "BibTeX"
    else:
        print("⚠️ No references matched your filters.")
        exit()

# Generate Summary
summary_lines = [
    f"📄 File Type: {output_type}",
    f"📂 Folder: {folder_path}",
    f"📅 Filtering from {start_year} to {current_year}",
    f"🔍 Included only: Original Research and Conference Papers\n",
    "📑 File-wise Reference Count:"
]

for fname, stats in file_stats.items():
    summary_lines.append(f"   - {fname}:")
    summary_lines.append(f"       Total References:   {stats['total']}")
    summary_lines.append(f"       Matched (Filtered): {stats['filtered']}")
    summary_lines.append(f"       Ignored (Too Old/Wrong Type):  {stats['ignored']}")

summary_lines.append(f"\n📊 Total References Found:    {total_found}")
summary_lines.append(f"✅ Total References Included: {total_filtered}")
summary_lines.append(f"❌ Total References Excluded: {total_found - total_filtered}")

# Add publication type statistics (showing what was excluded)
summary_lines.append("\n📝 Publication Type Breakdown (Before Final Filtering):")
for pub_type, count in sorted(publication_types.items(), key=lambda x: x[1], reverse=True):
    if pub_type in ['Original Research', 'Conference Paper']:
        summary_lines.append(f"   - {pub_type}: {count} ✅ INCLUDED")
    else:
        summary_lines.append(f"   - {pub_type}: {count} ❌ EXCLUDED")

summary_lines.append(f"\n📤 Output File: {os.path.basename(output_file)}")

summary = "\n".join(summary_lines)
summary_file = os.path.join(folder_path, f"Inclusion Summary.txt")
with open(summary_file, "w", encoding="utf-8") as f:
    f.write(summary)

print(summary)