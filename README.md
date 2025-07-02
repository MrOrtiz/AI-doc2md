# AI-doc2md 🚀  
*A multi-format document-to-Markdown pipeline you can plug into any RAG / LLM project.*

---

## ✨ What it does
| Step | Purpose |
|------|---------|
| 1. **Convert** | Turn PDFs, EPUB, MOBI/AZW/LIT, DOC/DOCX, TXT into clean **Markdown** files. |
| 2. **Split**   | Slice each Markdown book into **per-chapter files** (# headings) for easy review. |
| 3. **Clean**   | You (or GPT) remove junk: page headers, hyphens, etc. |
| 4. **Ready**   | Final chapters live in `data_final/` and can be indexed by FAISS, Chroma, Pinecone … |

Everything runs from **two scripts** in `/scripts`, so you can reuse this repo for unlimited corpora.

---

## ☁ Folder layout

```
AI-doc2md/
│  README.md
│  .gitignore
│  requirements.txt
│
├─ scripts/
│   ├─ convert_any_to_md.py     # multi-format converter
│   └─ split_md_by_heading.py   # chapter splitter
│
└─ corpora/
    └─ <your_project_name>/
        ├─ data_raw/    # drop original files here
        ├─ data_md/     # auto-generated Markdown (one file per book)
        ├─ data_clean/  # chapter files for human / GPT editing
        └─ data_final/  # ONLY files you want indexed downstream
```

Create **one sub-folder per corpus** inside `corpora/`; scripts work on the current folder only, so projects never collide.

---

## 🛠 Requirements

```bash
pip install -r requirements.txt
```

| Package | Why |
|---------|-----|
| `unstructured[local-inference]` | Best PDF-→-Markdown (handles OCR if you add `--ocr`). |
| `ebooklib` + **Calibre** CLI* | Converts EPUB / MOBI / AZW / LIT. |
| `python-docx` & `pypandoc` | DOC / DOCX → Markdown (falls back gracefully). |

*Install Calibre from https://calibre-ebook.com; ensure `ebook-convert` is in your PATH (Windows: `C:\Program Files\Calibre2\ebook-convert.exe`).

---

## ⚡ Quick start

```bash
# 0) clone & set up venv once
git clone https://github.com/yourname/AI-doc2md.git
cd AI-doc2md
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1) create a corpus
cd corpora
mkdir gov_contracting\data_raw -p
#   ➜ drop PDFs/EPUBs/etc. into data_raw/

# 2) convert ALL files to Markdown
cd gov_contracting
pwsh ../../scripts/convert_any_to_md.py       # PowerShell
# or: python ../../scripts/convert_any_to_md.py

# 3) split each .md into chapters
python ../../scripts/split_md_by_heading.py

# 4) review & tidy files in data_clean/
#    when satisfied:
mkdir data_final && cp -R data_clean/* data_final/

# 5) point your RAG project's ingest.py at:
#    C:\path\to\AI-doc2md\corpora\gov_contracting\data_final
```

---

## 📝 Script details

### `convert_any_to_md.py`
| Extension | Converter |
|-----------|-----------|
| `.pdf`        | `unstructured partition pdf` |
| `.epub`       | `pypandoc` |
| `.doc/.docx`  | `pypandoc` → fallback `python-docx` |
| `.txt`        | direct copy |
| `.mobi/.azw/.azw3/.lit` | Calibre’s `ebook-convert` CLI |

### `split_md_by_heading.py`
Splits on level-1 headings (`# Heading`) → writes

```
data_clean/<BookName>/ch00_intro.md
```

---

## 🏎 Daily usage checklist
1. **Add** new docs → `corpora/<project>/data_raw/`.
2. Run `convert_any_to_md.py`.
3. Run `split_md_by_heading.py`.
4. **Edit** chapters in `data_clean/`.
5. Copy approved files → `data_final/`.
6. Re-run your downstream RAG ingestion (FAISS, Chroma, etc.).

---

## 🧩 Integrating with your RAG

```python
SOURCE_DIR = pathlib.Path(r"C:\AI-doc2md\corpora\gov_contracting\data_final")
```
That’s **literally the only change** required in your `ingest.py`.

---

## 🤖 FAQ

| Question | Answer |
|----------|--------|
| **Scanned PDF?** | Add `--ocr` in `convert_any_to_md.py` (`unstructured partition pdf … --ocr`). |
| **Large file chokes Pandoc?** | Converter logs an error and skips; you can handle manually. |
| **Want multiprocess?** | Wrap converter calls in `concurrent.futures.ThreadPoolExecutor`. |
| **Need re-runs nightly?** | Schedule `pwsh process.ps1` that calls both scripts. |

---

## 📜 License
MIT – use it for anything. Pull requests welcome!

Enjoy painless, repeatable document ingestion for *any* future RAG project 🪄
