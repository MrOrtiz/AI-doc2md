#!/usr/bin/env python
"""
Split Markdown files into chapter files by heading level (default H1).

Key CLI flags
-------------
--src <dir>            source tree containing *.md
--dst <dir>            destination root for book folders
--level N              heading level to split on (1–6, default=1)
--workers N            parallel processes (0 = auto; 1 = sequential)
--force                overwrite existing book directories
--no-split-action      {skip|copy}   what to do if no headings found
--dry-run              log actions but don’t write files
--verbose              DEBUG logging
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import logging
import os
import pathlib
import re
import shutil
from typing import Iterable, List, Tuple

###############################################################################
# Logging
###############################################################################
_FMT = "%(asctime)s | %(levelname)-8s | %(message)s"
logging.basicConfig(level=logging.INFO, format=_FMT, datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

###############################################################################
# Helper utilities
###############################################################################
INVALID_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str, max_len: int = 80) -> str:
    clean = INVALID_CHARS.sub("_", name.lower()).strip("_")
    return clean[:max_len] or "untitled"


def iter_markdown_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    return (p for p in root.rglob("*.md") if p.is_file())


# --------------------------------------------------------------------------- #
# Markdown splitting
# --------------------------------------------------------------------------- #
def split_markdown(
    text: str,
    level: int = 1,
) -> List[Tuple[str, str]]:
    """
    Return list[(title, chapter_text)].

    chapter_text **includes** its heading line, e.g. '# Intro\nBody…'
    Content before the first heading is returned as ('prologue', text).
    """
    pattern = rf"^({'#' * level})\s+(.+)$"
    h_re = re.compile(pattern, re.MULTILINE)

    parts: List[Tuple[str, str]] = []
    last_pos = 0
    last_title = "prologue"

    for m in h_re.finditer(text):
        body = text[last_pos : m.start()]
        if body.strip():
            parts.append((last_title, body.strip()))

        heading_line = m.group(0)
        last_title = m.group(2).strip()
        last_pos = m.start()

    tail = text[last_pos:].strip()
    if tail:
        parts.append((last_title, tail))

    # Ensure heading lines are included in each chapter_text
    refined: List[Tuple[str, str]] = []
    for title, chunk in parts:
        if not chunk.startswith("#"):
            chunk = f"{'#' * level} {title}\n\n{chunk}"
        refined.append((title, chunk))

    return refined


# --------------------------------------------------------------------------- #
# File processing
# --------------------------------------------------------------------------- #
def _write_chapters(
    book_dir: pathlib.Path,
    chapters: List[Tuple[str, str]],
    force: bool,
    dry_run: bool,
) -> None:
    if force and book_dir.exists():
        shutil.rmtree(book_dir)
    book_dir.mkdir(parents=True, exist_ok=True)

    for idx, (title, content) in enumerate(chapters):
        fname = f"ch{idx:02d}_{sanitize_filename(title)}.md"
        path = book_dir / fname
        if dry_run:
            log.debug("[DRY-RUN] would write %s", path)
            continue
        path.write_text(content + "\n", encoding="utf-8")
        log.debug("Wrote %s", path)


def process_file(
    src_path: pathlib.Path,
    dst_root: pathlib.Path,
    level: int,
    force: bool,
    no_split_action: str,
    dry_run: bool,
) -> None:
    try:
        book_dir = dst_root / src_path.stem
        md_text = src_path.read_text(encoding="utf-8", errors="ignore")
        chapters = split_markdown(md_text, level)

        if len(chapters) <= 1:
            if no_split_action == "copy":
                dst = book_dir.with_suffix(".md")
                if dry_run:
                    log.info("[DRY-RUN] would copy %s → %s", src_path, dst)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(src_path, dst)
                    log.info("Copied (no headings): %s", src_path.name)
            else:
                log.info("Skipped (no headings): %s", src_path.name)
            return

        _write_chapters(book_dir, chapters, force, dry_run)
        log.info("Processed %s (%d chapters)", src_path.name, len(chapters))
    except Exception as e:
        log.error("Failed %s: %s", src_path.name, e)


###############################################################################
# CLI
###############################################################################
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split Markdown files into chapters.")
    p.add_argument("--src", required=True, type=pathlib.Path, help="Source dir with .md files")
    p.add_argument("--dst", required=True, type=pathlib.Path, help="Destination root for book folders")
    p.add_argument("--level", type=int, default=1, choices=range(1, 7), metavar="[1-6]",
                   help="Heading level to split on (default 1 = '#')")
    p.add_argument("--force", action="store_true", help="Overwrite existing book directories")
    p.add_argument("--no-split-action", choices=("skip", "copy"), default="skip",
                   help="What to do when file lacks chosen heading level")
    p.add_argument("--workers", type=int, default=1,
                   help="Parallel worker processes (0 = os.cpu_count())")
    p.add_argument("--dry-run", action="store_true", help="Log actions without writing files")
    p.add_argument("--verbose", action="store_true", help="Verbose (DEBUG) logging")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.verbose:
        log.setLevel(logging.DEBUG)

    if not args.src.exists():
        log.error("Source directory does not exist: %s", args.src)
        return
    args.dst.mkdir(parents=True, exist_ok=True)

    md_files = list(iter_markdown_files(args.src))
    if not md_files:
        log.warning("No Markdown files found under %s", args.src)
        return

    workers = os.cpu_count() if args.workers == 0 else max(1, args.workers)
    log.info("Splitting %d file(s) using %d worker(s)…", len(md_files), workers)

    # Sequential path for workers == 1 (keeps error tracebacks simple)
    if workers == 1:
        for fp in md_files:
            process_file(fp, args.dst, args.level, args.force, args.no_split_action, args.dry_run)
        return

    with cf.ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(
                process_file,
                fp,
                args.dst,
                args.level,
                args.force,
                args.no_split_action,
                args.dry_run,
            )
            for fp in md_files
        ]
        # simple progress wait
        for f in cf.as_completed(futures):
            _ = f.result()  # re-raise exceptions here

    log.info("Done.")


if __name__ == "__main__":
    main()
