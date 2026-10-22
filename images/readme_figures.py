#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Build the image at the top of README.md.

It shows one solved problem from end to end, in a single picture: the
physical system (its figure), the derived solution (its answer box in the
manual) and the numerical check (its measured results). It is made from the
outputs of latexmk, which are not tracked: run latexmk from the repository
root first, so that main.pdf and Figures/*.pdf exist and are up to date.

  1. The answer box of the problem is cut out of main.pdf and made compact
     (its empty width around the answer removed, its edges and header kept):
     build/readme-figures/<id>-answer.pdf.
  2. images/<id>-flow.tex arranges the three steps; it is compiled with
     LuaLaTeX, as latexmk compiles Figures/*.tex (the template submodule
     provides its class): build/readme-figures/<id>-flow.pdf.
  3. The PDF is rendered to images/<id>-flow.png (tracked), WIDTH pixels wide,
     opaque so that it stays readable in GitHub's dark mode.

The build stops if an input is missing, the compilation fails or the image
exceeds MAX_BYTES.

Usage: python images/readme_figures.py
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    sys.exit("PyMuPDF is missing: python -m pip install -r images/requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
FRAMEWORK = ROOT / "template" / "solution-manual"   # SolutionFigure.cls
BUILD = ROOT / "build" / "readme-figures"

# The problem shown: its section and number in the book, and its ID
SECTION, PROBLEM, ID = "11", "1", "S11P1"
PAD = 12                    # margin around the answer in its box (pt)
WIDTH = 1760                # pixels: twice the width of the README column
MAX_BYTES = 200_000


def problem_pages(document):
    """Pages of the problem, from the bookmarks of main.pdf."""
    toc = document.get_toc()
    for i, (level, title, page) in enumerate(toc):
        if level == 2 and title.startswith(f"§{SECTION} "):
            for j in range(i + 1, len(toc)):
                if toc[j][0] <= 2:
                    break
                # "Problem 1", or "Problem 1. Title" for a titled problem
                if toc[j][1].split(". ")[0] == f"Problem {PROBLEM}":
                    end = next((t[2] for t in toc[j + 1:] if t[0] <= 3), document.page_count)
                    return range(toc[j][2] - 1, end)
    sys.exit(f"main.pdf has no bookmark for §{SECTION} Problem {PROBLEM}")


def answer_box(document):
    """Page number, outer and inner rectangles of the answer box, its header
    text and the rectangle of the answer in it."""
    for pno in problem_pages(document):
        page = document[pno]
        headers = [pymupdf.Rect(line["bbox"])
                   for block in page.get_text("dict")["blocks"] for line in block.get("lines", [])
                   if "".join(s["text"] for s in line["spans"]).startswith("Answer to Problem")]
        if not headers:
            continue
        header = headers[0]
        boxes = [d["rect"] for d in page.get_drawings() if d["rect"].width > 300]
        outer = next(r for r in boxes if r.contains(header))
        inner = next(r for r in boxes if r != outer and outer.contains(r) and r.y0 >= header.y1 - 1)
        answer = pymupdf.Rect()
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                if inner.intersects(line["bbox"]):
                    answer |= line["bbox"]
        for d in page.get_drawings():
            if d["rect"] != inner and inner.contains(d["rect"]):
                answer |= d["rect"]
        return pno, outer, inner, header, answer
    sys.exit(f"main.pdf has no answer box for §{SECTION} Problem {PROBLEM}")


def compact_answer():
    """build/readme-figures/<id>-answer.pdf: the answer box with its empty
    width cut out. The box is cut into vertical strips (its left edge, a
    window around the answer, its right edge, and the header bar) put side by
    side on a new page; the fills are uniform, so the joins do not show."""
    pdf = ROOT / "main.pdf"
    if not pdf.exists():
        sys.exit("main.pdf is missing: run latexmk first")
    with pymupdf.open(pdf) as document:
        pno, outer, inner, header, answer = answer_box(document)
        left = inner.x0 - outer.x0 + PAD           # left edge strip
        right = outer.x1 - inner.x1 + PAD          # right edge strip
        # window around the answer, wide enough for the header text
        window = max(answer.width + 2 * PAD, header.x1 + PAD - outer.x0 - left)
        width = left + window + right
        centre = (answer.x0 + answer.x1) / 2
        with pymupdf.open() as out:
            page = out.new_page(width=width, height=outer.height)
            strips = [
                # (x in the new page, clip in main.pdf)
                (0, (outer.x0, outer.y0, outer.x0 + left + window, inner.y0)),   # header bar
                (width - right, (outer.x1 - right, outer.y0, outer.x1, inner.y0)),
                (0, (outer.x0, inner.y0, outer.x0 + left, outer.y1)),            # body
                (left, (centre - window / 2, inner.y0, centre + window / 2, outer.y1)),
                (width - right, (outer.x1 - right, inner.y0, outer.x1, outer.y1)),
            ]
            for x, clip in strips:
                clip = pymupdf.Rect(clip)
                y = clip.y0 - outer.y0
                page.show_pdf_page(pymupdf.Rect(x, y, x + clip.width, y + clip.height),
                                   document, pno, clip=clip)
            out.save(BUILD / f"{ID}-answer.pdf")


def compile_flow():
    """Compile images/<id>-flow.tex to build/readme-figures/<id>-flow.pdf."""
    if not (FRAMEWORK / "SolutionFigure.cls").exists():
        sys.exit("template/ is empty: git submodule update --init template")
    for figure in (ID, f"{ID}-period"):
        if not (ROOT / "Figures" / f"{figure}.pdf").exists():
            sys.exit(f"Figures/{figure}.pdf is missing: run latexmk first")
    # Find the framework's classes, then the default paths (trailing separator)
    env = dict(os.environ)
    env["TEXINPUTS"] = os.pathsep.join(
        p for p in (str(FRAMEWORK), env.get("TEXINPUTS", "").strip(os.pathsep)) if p) + os.pathsep
    # Run from the root, where myfigures.sty, Figures/ and build/ are
    result = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-halt-on-error",
         f"-output-directory={BUILD}", f"images/{ID}-flow.tex"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode:
        sys.exit(f"images/{ID}-flow.tex failed to compile: see {BUILD / ID}-flow.log")
    return BUILD / f"{ID}-flow.pdf"


def render(pdf):
    """Render the first page of the PDF to images/<id>-flow.png."""
    with pymupdf.open(pdf) as document:
        page = document[0]
        zoom = WIDTH / page.rect.width
        # alpha=False: opaque, on white
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    png = HERE / f"{ID}-flow.png"
    pixmap.save(png)
    size = png.stat().st_size
    print(f"{png.relative_to(ROOT)}: {pixmap.width}x{pixmap.height}, {size // 1000} kB")
    if size > MAX_BYTES:
        sys.exit(f"{png.relative_to(ROOT)} is larger than {MAX_BYTES // 1000} kB")


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    compact_answer()
    render(compile_flow())


if __name__ == "__main__":
    main()
