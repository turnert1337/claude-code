#!/usr/bin/env python3
"""
prepare_documents.py
====================
Downloads and prepares freely available Charlie Munger speeches and documents
for ingestion into the Qdrant vector knowledge base.

Usage:
    python3 prepare_documents.py

Output:
    documents/ directory containing clean .txt files ready for ingestion.

After running this script:
    1. Review the downloaded files in documents/
    2. Optionally add your own documents (PDFs, paste-ins) to documents/
    3. Update workflow 02 in n8n to point to these files
       (either host them somewhere, or use n8n's file system nodes)
"""

import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


DOCUMENTS_DIR = Path(__file__).parent / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Free source documents — these are publicly available transcripts and texts
# ─────────────────────────────────────────────────────────────────────────────
FREE_SOURCES = [
    {
        "filename": "munger_1995_psychology_of_human_misjudgment.txt",
        "title": "The Psychology of Human Misjudgment (1995)",
        "category": "mental_models",
        "source": "speech",
        "year": "1995",
        # Multiple mirrors — try in order
        "urls": [
            "https://fs.blog/great-talks/the-psychology-of-human-misjudgment/",
            "https://valueinvestingworld.substack.com/p/munger-psychology-human-misjudgment",
        ],
        "note": "If automated download fails, search 'Munger Psychology Human Misjudgment full text' and paste into this file.",
    },
    {
        "filename": "munger_1994_elementary_worldly_wisdom.txt",
        "title": "A Lesson on Elementary Worldly Wisdom (USC 1994)",
        "category": "mental_models",
        "source": "speech",
        "year": "1994",
        "urls": [
            "https://fs.blog/a-lesson-on-elementary-worldly-wisdom/",
        ],
        "note": "Search 'Munger elementary worldly wisdom USC 1994 full transcript'",
    },
    {
        "filename": "munger_2023_acquired_interview.txt",
        "title": "Acquired Podcast Interview with Charlie Munger (October 2023)",
        "category": "investing_current",
        "source": "interview",
        "year": "2023",
        "urls": [],
        "note": "Get transcript from https://www.acquired.fm/episodes/charlie-munger — this was his final major interview. Paste the full transcript into this file.",
    },
]

# Manually-acquired documents (no auto-download possible)
MANUAL_SOURCES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENTS REQUIRING MANUAL ACQUISITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Place these as .txt files in the documents/ directory:

1. munger_wesco_letters_1977_2010.txt
   → Wesco Financial Annual Reports, Munger's Chairman Letters
   → Download PDFs from: https://www.berkshirehathaway.com/wesco/annual.html
   → Convert PDFs to text: pip install pdfplumber
     python3 -c "
     import pdfplumber, glob, os
     for f in sorted(glob.glob('wesco_*.pdf')):
         with pdfplumber.open(f) as pdf:
             text = '\\n'.join(page.extract_text() or '' for page in pdf.pages)
         out = f.replace('.pdf', '.txt')
         open(out, 'w').write(text)
     "
   → Concatenate all years into one file

2. munger_poor_charlies_almanack_talks.txt
   → From the book "Poor Charlie's Almanack" (Kaufman, ed.)
   → Contains 11 talks — the most complete Munger anthology
   → Type or paste key sections. Focus on:
     - Introduction by Peter Kaufman
     - All 11 talks
     - The recommended reading list

3. munger_djco_meetings_2014_2023.txt
   → Daily Journal Corporation Annual Meeting transcripts
   → Sources:
     - SeekingAlpha.com (search "DJCO annual meeting transcript")
     - ValueInvestorClub.com
     - Gurufocus.com Charlie Munger section
   → 2021 and 2019 meetings are especially content-rich

4. munger_berkshire_annual_meeting_excerpts.txt
   → Berkshire Hathaway Annual Meeting Q&A — Munger's portions only
   → Full transcripts: Morningstar, CNBC archives, BeyondProxy.com
   → Key years: 1999, 2001, 2008, 2013, 2017, 2020, 2022

5. munger_miscellaneous_quotes_verified.txt
   → Compiled verified Munger quotes with source citations
   → Farnam Street has excellent compilations: https://fs.blog/munger/
   → Only use quotes with clear source attribution
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def clean_html(text: str) -> str:
    """Very basic HTML tag removal for text cleanup."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'\s{3,}', '\n\n', text)
    return text.strip()


def download_url(url: str, timeout: int = 30) -> Optional[str]:
    """Attempt to download text content from a URL."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; MungerBot/1.0; research)'
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode('utf-8', errors='replace')
            return content
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"    Failed ({e})")
        return None


def process_source(source: dict) -> bool:
    """Try to download and save a source document. Returns True if successful."""
    filepath = DOCUMENTS_DIR / source["filename"]

    # Skip if already exists
    if filepath.exists() and filepath.stat().st_size > 1000:
        print(f"  [SKIP] {source['filename']} already exists ({filepath.stat().st_size:,} bytes)")
        return True

    print(f"  [FETCH] {source['title']}")

    for url in source.get("urls", []):
        print(f"    Trying: {url[:80]}...")
        content = download_url(url)
        if content and len(content) > 2000:
            # Basic cleanup
            if '<html' in content.lower() or '<body' in content.lower():
                content = clean_html(content)

            # Write with header metadata
            header = (
                f"TITLE: {source['title']}\n"
                f"CATEGORY: {source['category']}\n"
                f"SOURCE: {source['source']}\n"
                f"YEAR: {source['year']}\n"
                f"DOWNLOADED: {time.strftime('%Y-%m-%d')}\n"
                f"{'─' * 60}\n\n"
            )
            filepath.write_text(header + content, encoding='utf-8')
            print(f"    Saved {len(content):,} chars to {source['filename']}")
            return True
        time.sleep(1)  # polite delay between requests

    # If all URLs failed, create a placeholder
    placeholder = (
        f"TITLE: {source['title']}\n"
        f"CATEGORY: {source['category']}\n"
        f"SOURCE: {source['source']}\n"
        f"YEAR: {source['year']}\n"
        f"STATUS: MANUAL ACQUISITION REQUIRED\n"
        f"{'─' * 60}\n\n"
        f"[PLACEHOLDER - Download failed]\n\n"
        f"NOTE: {source.get('note', 'See knowledge_sources.txt for acquisition instructions.')}\n\n"
        f"TO COMPLETE: Manually obtain this document and replace this file's\n"
        f"content with the actual text. Keep the header metadata above.\n"
    )
    filepath.write_text(placeholder, encoding='utf-8')
    print(f"    Created placeholder — manual acquisition needed")
    print(f"    NOTE: {source.get('note', '')}")
    return False


def generate_n8n_sources_json(documents_dir: Path) -> str:
    """Generate the sources array for the n8n workflow from actual documents."""
    import json

    txt_files = sorted(documents_dir.glob("*.txt"))
    if not txt_files:
        return "[]"

    sources = []
    for txt_file in txt_files:
        # Read header metadata
        content = txt_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        meta = {}
        for line in lines[:10]:
            if ':' in line:
                key, _, val = line.partition(':')
                meta[key.strip().lower()] = val.strip()

        if meta.get('status') == 'MANUAL ACQUISITION REQUIRED':
            continue

        sources.append({
            "type": "text",
            "title": meta.get('title', txt_file.stem),
            "source": meta.get('source', 'unknown'),
            "year": meta.get('year', 'unknown'),
            "category": meta.get('category', 'misc'),
            "text_file": str(txt_file),
            "note": f"Content from {txt_file.name}"
        })

    return json.dumps(sources, indent=2)


def main():
    print("=" * 60)
    print("MUNGER AI — Document Preparation Script")
    print("=" * 60)
    print(f"Output directory: {DOCUMENTS_DIR}\n")

    # Try to download free sources
    print("STEP 1: Attempting to download free sources...\n")
    success_count = 0
    for source in FREE_SOURCES:
        if process_source(source):
            success_count += 1
        time.sleep(0.5)

    # Print manual acquisition instructions
    print("\n" + "=" * 60)
    print(MANUAL_SOURCES)

    # Show what we have
    print("=" * 60)
    print(f"\nSTEP 2: Documents status in {DOCUMENTS_DIR}:\n")
    txt_files = sorted(DOCUMENTS_DIR.glob("*.txt"))
    if txt_files:
        for f in txt_files:
            size = f.stat().st_size
            content = f.read_text(encoding='utf-8', errors='ignore')
            is_placeholder = 'MANUAL ACQUISITION REQUIRED' in content
            status = "PLACEHOLDER" if is_placeholder else f"READY ({size:,} bytes)"
            print(f"  {'✗' if is_placeholder else '✓'} {f.name} — {status}")
    else:
        print("  No documents found yet.")

    # Optionally convert PDFs if pdfplumber is available
    pdf_files = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    if pdf_files:
        print(f"\nSTEP 3: Found {len(pdf_files)} PDF files to convert...")
        try:
            import pdfplumber
            for pdf_path in pdf_files:
                txt_path = pdf_path.with_suffix('.txt')
                if txt_path.exists():
                    print(f"  [SKIP] {txt_path.name} already exists")
                    continue
                print(f"  Converting {pdf_path.name}...")
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        pages = [page.extract_text() or '' for page in pdf.pages]
                        text = '\n\n'.join(pages)
                    txt_path.write_text(text, encoding='utf-8')
                    print(f"  Saved {len(text):,} chars to {txt_path.name}")
                except Exception as e:
                    print(f"  Error converting {pdf_path.name}: {e}")
        except ImportError:
            print("  pdfplumber not installed. Run: pip install pdfplumber")

    # Generate n8n-compatible sources list
    print("\nSTEP 4: Generated n8n sources configuration:")
    print("  (Copy this into the 'Define Source Documents' node in workflow 02)")
    print()
    sources_json = generate_n8n_sources_json(DOCUMENTS_DIR)
    print(sources_json[:500] + ("..." if len(sources_json) > 500 else ""))

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("  1. Manually acquire documents listed above (especially Wesco letters)")
    print("  2. Place any PDFs in the documents/ directory and re-run this script")
    print("  3. Host the .txt files somewhere n8n can fetch them (GitHub, S3, etc.)")
    print("  4. Update workflow 02 'Define Source Documents' node with your URLs")
    print("  5. Run workflow 02 in n8n to ingest into Qdrant")
    print("=" * 60)


if __name__ == "__main__":
    main()
