"""
Converts various document formats (PDF, EPUB, DOCX, etc.) to Markdown.

Features:
- Walks a source directory recursively.
- Converts files to Markdown in a parallel destination directory.
- Uses command-line arguments for source, destination, and options.
- Skips already converted files unless forced.
- Runs conversions in parallel for speed.
- Checks for required external command-line tools.

Usage:
  python convert_any_to_md.py data_raw/ data_md/ --workers 4 --force
"""

import argparse
import logging
import pathlib
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

# --- Dependency Checks ------------------------------------------------------

def check_dependencies():
    """Check for required command-line tools."""
    required_tools = ["unstructured", "ebook-convert"]
    missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
    if missing_tools:
        logging.error(f"Missing required tools: {', '.join(missing_tools)}. Please install them and ensure they are in your PATH.")
        sys.exit(1)

# --- Logging Setup ----------------------------------------------------------

def setup_logging(verbose: bool):
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

# --- Converter Functions ----------------------------------------------------

def run_command(cmd: List[str]):
    """Execute a command and raise an error if it fails."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return result.stdout
    except FileNotFoundError:
        logging.error(f"Command not found: {cmd[0]}")
        raise
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(cmd)}\n{e.stderr.strip()}")
        raise

def pdf_to_md(src: pathlib.Path, dst: pathlib.Path):
    """Use unstructured's CLI for PDF conversion."""
    run_command([
        "unstructured", "partition", "pdf", str(src),
        "--output-file", str(dst),
        "--output-format", "md",
        "--chunking_strategy", "by_title"
    ])

def epub_to_md(src: pathlib.Path, dst: pathlib.Path):
    """Use pandoc for EPUB conversion."""
    try:
        import pypandoc
        pypandoc.convert_file(str(src), "md", outputfile=str(dst))
    except (OSError, ImportError):
        logging.error("pypandoc is not installed. Please install it with 'pip install pypandoc'.")
        raise

def doc_to_md(src: pathlib.Path, dst: pathlib.Path):
    """Use pandoc; fallback to python-docx."""
    try:
        import pypandoc
        pypandoc.convert_file(str(src), "md", outputfile=str(dst))
    except (OSError, ImportError):
        logging.warning("pypandoc not found, falling back to python-docx. Formatting may be suboptimal.")
        try:
            import docx
            document = docx.Document(str(src))
            text = "\n\n".join(p.text for p in document.paragraphs)
            dst.write_text(text, encoding="utf-8")
        except ImportError:
            logging.error("python-docx is not installed. Please install it with 'pip install python-docx'.")
            raise

def kindle_to_md(src: pathlib.Path, dst: pathlib.Path):
    """Use Calibre's ebook-convert CLI for Kindle formats."""
    run_command(["ebook-convert", str(src), str(dst)])

def plain_copy(src: pathlib.Path, dst: pathlib.Path):
    """Simply copy the file, changing the extension."""
    shutil.copy(src, dst)

# --- Extension Dispatch Table -----------------------------------------------

CONVERTERS: Dict[str, Callable[[pathlib.Path, pathlib.Path], None]] = {
    ".pdf": pdf_to_md,
    ".epub": epub_to_md,
    ".doc": doc_to_md,
    ".docx": doc_to_md,
    ".txt": plain_copy,
    ".mobi": kindle_to_md,
    ".azw": kindle_to_md,
    ".azw3": kindle_to_md,
    ".lit": kindle_to_md,
}

# --- Main Worker Function ---------------------------------------------------

def process_file(src_path: pathlib.Path, src_root: pathlib.Path, dst_root: pathlib.Path, force: bool) -> Optional[str]:
    """
    Process a single file: check if it needs conversion, convert it, and log status.
    """
    rel_path = src_path.relative_to(src_root)
    dst_path = dst_root / rel_path.with_suffix(".md")

    if not force and dst_path.exists() and dst_path.stat().st_mtime > src_path.stat().st_mtime:
        logging.debug(f"Skipping (already up-to-date): {rel_path}")
        return None

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    ext = src_path.suffix.lower()
    converter = CONVERTERS.get(ext)

    if not converter:
        logging.warning(f"No converter found for {ext}, skipping: {rel_path}")
        return None

    try:
        logging.info(f"Converting: {rel_path} -> {dst_path.relative_to(dst_root)}")
        converter(src_path, dst_path)
        return f"Successfully converted: {rel_path}"
    except Exception as e:
        logging.error(f"Failed to convert {rel_path}: {e}")
        # Optionally, write an error file
        error_file = dst_path.with_suffix(".error.txt")
        error_file.write_text(f"Failed to convert {src_path}:\n\n{e}", encoding="utf-8")
        return f"ERROR converting {rel_path}: {e}"

# --- Main Execution ---------------------------------------------------------

def main():
    """
    Parse arguments, find files, and process them in parallel.
    """
    parser = argparse.ArgumentParser(description="Convert documents to Markdown.")
    parser.add_argument("src_root", type=pathlib.Path, help="Source directory containing files to convert.")
    parser.add_argument("dst_root", type=pathlib.Path, help="Destination directory for Markdown files.")
    parser.add_argument("-w", "--workers", type=int, default=None, help="Number of parallel processes. Defaults to CPU count.")
    parser.add_argument("-f", "--force", action="store_true", help="Force reprocessing of all files.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging.")
    args = parser.parse_args()

    setup_logging(args.verbose)
    check_dependencies()

    if not args.src_root.is_dir():
        logging.error(f"Source directory not found: {args.src_root}")
        sys.exit(1)
    args.dst_root.mkdir(exist_ok=True)

    files_to_process = [p for p in args.src_root.rglob("*") if p.is_file() and p.suffix.lower() in CONVERTERS]
    total_files = len(files_to_process)
    logging.info(f"Found {total_files} files to process in '{args.src_root}'.")

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(process_file, f, args.src_root, args.dst_root, args.force)
            for f in files_to_process
        ]
        
        processed_count = 0
        for future in as_completed(futures):
            result = future.result()
            if result:
                logging.debug(result)
            processed_count += 1
            logging.info(f"Progress: {processed_count}/{total_files}")

    logging.info("All files processed. Done.")

if __name__ == "__main__":
    main()
