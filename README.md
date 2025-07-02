# AI-doc2md 🚀  
*A reusable pipeline that converts mixed‑format document collections into clean, chapter‑level Markdown—ready for any Retrieval‑Augmented Generation (RAG) index.*

---

## ✨ What it does  
| Phase | Purpose | Key script |
|-------|---------|------------|
| **1. Convert** | Turn **PDF, EPUB, MOBI/AZW/LIT, DOC/DOCX, TXT** into Markdown. Parallel, dependency‑checked. | `scripts/convert_any_to_md.py` |
| **2. Split**   | Slice each Markdown book into per‑chapter files based on heading level, in parallel. | `scripts/split_md_by_heading.py` |
| **3. Clean**   | You or GPT tweak the Markdown in `data_clean/` (fix page headers, hyphens, etc.). | manual / GPT |
| **4. Ready**   | Approved chapters in `data_final/` feed directly to your RAG ingestion (FAISS, Chroma, Pinecone…). | any |

Everything is driven by two standalone CLI utilities—no hard‑coded paths, fully parallel, and safe “dry‑run” modes.

---

## 📂 Folder layout

```
AI-doc2md/
│  README.md
│  requirements.txt
│
├─ scripts/
│   ├─ convert_any_to_md.py      # multi‑format → Markdown
│   └─ split_md_by_heading.py    # Markdown → chapters
│
└─ corpora/
    └─ <project_name>/
        ├─ data_raw/     # original docs (any supported type)
        ├─ data_md/      # auto‑generated Markdown
        ├─ data_clean/   # chapter files for review
        └─ data_final/   # only files you want indexed
```

Create **one sub‑folder per corpus**; scripts run in that folder only, so projects never collide.

---

## 🛠 Installation

```bash
git clone https://github.com/<your-user>/AI-doc2md.git
cd AI-doc2md
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Runtime dependencies
| Tool | Used for |
|------|----------|
| **`unstructured`** (`[local-inference]` extra) | PDF → Markdown (with `--ocr` support). |
| **Calibre CLI** (`ebook-convert`) | EPUB / MOBI / AZW / LIT → Markdown. |
| **Pandoc + python-docx** | DOC / DOCX → Markdown fallback. |

> **Windows Calibre path**: `C:\Program Files\Calibre2\ebook-convert.exe` — add it to your `PATH`.

---

## ⚡ Quick start (one corpus)

```bash
# create corpus skeleton
cd corpora
mkdir gov_contracting/data_raw -p

# 1‑‑ Drop your PDFs/EPUBs/etc. into data_raw/

# 2‑‑ Convert everything to Markdown (4 workers, verbose)
cd gov_contracting
python ../../scripts/convert_any_to_md.py data_raw data_md --workers 4 --verbose

# 3‑‑ Split each .md into chapters at H1 (workers=auto CPU)
python ../../scripts/split_md_by_heading.py --src data_md --dst data_clean --workers 0

# 4‑‑ Open data_clean/ in VS Code, tidy, then:
mkdir data_final && cp -R data_clean/* data_final/

# 5‑‑ Point your RAG ingest:
# SOURCE_DIR = Path("AI-doc2md/corpora/gov_contracting/data_final")
```

### Command reference

#### `convert_any_to_md.py`
```
python convert_any_to_md.py <src_dir> <dst_dir> [--workers N] [--force] [--verbose]
```
* **Workers**: parallel processes (`0` = auto CPU count).  
* **--force**: re‑process even if up‑to‑date.  
* Skips unchanged files by mtime comparison.

#### `split_md_by_heading.py`
```
python split_md_by_heading.py --src <dir> --dst <dir> [--level N]
                              [--workers N] [--no-split-action skip|copy]
                              [--force] [--dry-run] [--verbose]
```
* **--level**: heading depth (1 = `#`, 2 = `##`, …).  
* **--workers 0**: auto parallel.  
* **--dry-run**: log planned writes without touching disk.  
* **--no-split-action copy**: copy whole file if no matching headings.

---

## 🧩 Integrating with your RAG

```python
from pathlib import Path
SOURCE_DIR = Path(r"C:/AI-doc2md/corpora/gov_contracting/data_final")
```

Point your `ingest.py` at `SOURCE_DIR`—done.

---

## 🚀  Typical daily workflow
1. **Add** new docs → `data_raw/`
2. `convert_any_to_md.py …`
3. `split_md_by_heading.py …`
4. **Edit** chapters in `data_clean/`
5. Copy approved files → `data_final/`
6. **Re‑index** with FAISS/Chroma etc.

---

## 🤖 FAQ
| Q | A |
|---|---|
| Scanned PDFs? | Add `--ocr` flag in `convert_any_to_md.py` (requires Tesseract). |
| Need only certain formats? | Use `--extensions .pdf,.epub` (see script help). |
| Re‑run nightly? | Schedule Task‑Scheduler / cron calling both scripts. |
| Multi‑gig corpora? | Raise `--workers`, ensure SSD; scripts stream files so RAM usage is low. |

---

## 📜 License
MIT – use it for anything. Contributions welcome!

Enjoy painless, repeatable document ingestion for *any* RAG project 🪄
