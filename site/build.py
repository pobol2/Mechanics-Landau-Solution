#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Build the website of the manual (GitHub Pages).

It reads two files written by latexmk (neither is tracked):

  main.pdf            chapters (top-level bookmarks), positions of the
                      problems and their parts (hyperref anchors) and links
                      between problems
  problems.json       the problem index of SolutionManual.cls: sections,
                      problems with their titles (title={...} in
                      Chapters/*.tex), completion, page ranges and parts

The output folder (default: _site, ignored by Git) receives:

  index.html          the catalogue: progress and every problem by chapter
  problems/<id>.html  one page per solved problem, showing its PDF
  pdf/<id>.pdf        one PDF per problem, its parts included
  main.pdf            the full manual
  catalogue.json      catalogue data
  sitemap.xml         the homepage, the solved-problem pages, the full manual
                      and the solved-problem PDFs
  style.css

Unsolved problems have no page: the catalogue links to their PDF (the
statement only), and they are left out of the sitemap.

Problem IDs follow the book's numbering, so they do not change when problems
are solved or pages move: s9-p3 is §9 Problem 3, s9-p3a its part (a).

Usage: python site/build.py [--out DIR] [--base-url URL] [--repository URL]
"""

import argparse
import html
import json
import posixpath
import re
import shutil
import sys
import urllib.parse
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DictionaryObject, Fit, NameObject,
                               TextStringObject)
except ImportError:
    sys.exit("pypdf is missing: python -m pip install -r site/requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
# Copy of build/main-problems.json ($problems_json in latexmkrc)
INDEX = "problems.json"

DEFAULT_REPOSITORY = "https://github.com/pobol2/Mechanics-Landau-Solution"
# Google Search Console ownership check of the site (HTML tag method)
GOOGLE_SITE_VERIFICATION = "I9Mnn8Ch39GMAo9_cUExA_0P-YiiCN3OjdxbqU2lAYk"
# The author's full name, shown on the website (the PDFs keep the author of
# main.pdf)
SITE_AUTHOR = "Pierre-Olivier Bolduc"
SITE_TITLE = "Solutions to Landau and Lifshitz, Mechanics"
SITE_NAME = "Landau Mechanics"      # short, in page titles when it fits
# Lengths that search results show in full (titles are cut at about 60
# characters, descriptions at about 160); the build checks every page
TITLE_MAX = 60
DESCRIPTION_RANGE = (25, 160)
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
BOOK = "Mechanics"
BOOK_AUTHORS = "Landau and Lifshitz"
BOOK_SERIES = "Course of Theoretical Physics, Volume 1"
# The edition the problems and section numbers refer to
BOOK_REFERENCE = {
    "authors": ["L. D. Landau", "E. M. Lifshitz"],
    "title": BOOK,
    "edition": "Third edition",
    "year": 1976,
    "series": BOOK_SERIES,
    "publisher": "Butterworth-Heinemann",
    "isbn": "9780750628969",
    "isbn_display": "978-0-7506-2896-9",
}

# Labels written by SolutionManual.cls (its defaults)
PROBLEM = "Problem"
CHAPTER = "Chapter"
# Bottom of the text area above the page bottom: the 25 mm margin of
# SolutionManual.cls, in points
TEXT_BOTTOM = 25 / 25.4 * 72

# Anchors of a problem (hyperref names ending with the problem key, plus the
# part number for SubProblemNum and the bookmark level for problem)
PROBLEM_ANCHORS = {"problem-title": 0, "ProblemNum": 0, "problem": 1, "SubProblemNum": 1}
# Link targets that make a cross-problem reference (\probref, \eqref)
REFERENCE_ANCHORS = {"problem-title", "ProblemNum", "problem", "SubProblemNum", "equation", "AMS"}


class Errors(list):
    """Problems found while reading the inputs; any of them stops the build."""

    def check(self, stage):
        if self:
            for message in self:
                print(f"error: {message}", file=sys.stderr)
            sys.exit(f"{stage}: {len(self)} error(s), nothing published")


def warn(message):
    print(f"warning: {message}", file=sys.stderr)


# ============ Model ============ #

@dataclass
class Part:
    letter: str
    page: int                 # page index in main.pdf
    left: float | None
    top: float | None
    done: bool = True


@dataclass
class Problem:
    number: int
    key: str                  # hyperref key, "2.3.0.3"
    start: int                # page indexes in main.pdf
    section: "Section"
    end: int = -1
    parts: list = field(default_factory=list)
    done: bool = True
    refs: set = field(default_factory=set)       # IDs of the problems it links to
    cited_by: set = field(default_factory=set)
    title: str = ""           # from problems.json

    @property
    def id(self):
        return f"{self.section.id}-p{self.number}"

    @property
    def heading(self):
        """Descriptive title, or the label when there is none."""
        return self.title or self.label

    @property
    def label(self):
        return f"{self.section.label} {PROBLEM} {self.number}"

    @property
    def pages(self):
        return self.end - self.start + 1

    @property
    def pdf(self):
        return f"pdf/{self.id}.pdf"

    @property
    def page(self):
        """Its web page, for a solved problem only."""
        return f"problems/{self.id}.html" if self.done else None

    @property
    def href(self):
        """Where the catalogue sends a visitor: the page, or the PDF."""
        return self.page or self.pdf


@dataclass
class Section:
    number: str               # the book's number, "9"
    title: str
    chapter: "Chapter"
    problems: list = field(default_factory=list)

    @property
    def id(self):
        return "s" + self.number.replace(".", "-")

    @property
    def label(self):
        return f"§{self.number}"


@dataclass
class Chapter:
    number: int
    title: str
    page: int
    sections: list = field(default_factory=list)

    @property
    def id(self):
        return f"chapter-{self.number}"

    @property
    def problems(self):
        return [p for s in self.sections for p in s.problems]


def done_count(problems):
    return sum(p.done for p in problems)


# ============ main.pdf ============ #

@dataclass
class Target:
    name: str | None          # named destination, if any
    page: int
    view: list                # destination array after the page reference
    left: float | None
    top: float | None


def number_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Anchors:
    """Destinations of main.pdf, named (hyperref anchors) or explicit."""

    def __init__(self, reader):
        self.reader = reader
        self.page_of_ref = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages)}
        self.named = {}
        for name, dest in reader.named_destinations.items():
            array = list(dest.dest_array)
            page = self.page_of_ref.get(getattr(array[0], "idnum", None))
            if page is not None:
                self.named[str(name)] = Target(str(name), page, array[1:],
                                               number_or_none(dest.left),
                                               number_or_none(dest.top))

    def resolve(self, dest):
        if dest is None:
            return None
        dest = dest.get_object()
        if isinstance(dest, ArrayObject):
            page = self.page_of_ref.get(getattr(dest[0], "idnum", None))
            if page is None:
                return None
            view = list(dest[1:])
            left = number_or_none(view[1]) if len(view) > 1 else None
            top = number_or_none(view[2]) if len(view) > 2 else None
            return Target(None, page, view, left, top)
        return self.named.get(str(dest))


def outline_entries(reader):
    """(level, title, destination) of each bookmark, in document order."""
    entries = []

    def walk(node, level):
        while node is not None:
            item = node.get_object()
            dest = item.get("/Dest")
            action = item.get("/A")
            if dest is None and action is not None:
                action = action.get_object()
                if action.get("/S") == "/GoTo":
                    dest = action.get("/D")
            entries.append((level, str(item["/Title"]), dest))
            if "/First" in item:
                walk(item["/First"], level + 1)
            node = item.get("/Next")

    outlines = reader.trailer["/Root"].get("/Outlines")
    if outlines is not None and "/First" in outlines.get_object():
        walk(outlines.get_object()["/First"], 0)
    return entries


def anchor_key(name):
    """(prefix, problem key) of a problem anchor, or None."""
    prefix, _, rest = name.partition(".")
    if prefix not in PROBLEM_ANCHORS:
        return None
    if PROBLEM_ANCHORS[prefix]:
        rest = rest.rpartition(".")[0]
    return prefix, rest


UNIT_RE = re.compile(r"§\s*(\d+(?:\.\d+)*)")
STATUSES = {"done": True, "not done": False}


def read_index(path, errors):
    """Problems of problems.json, in document order, after a check of their
    fields."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        errors.append(f"{path.name}: {e}")
        errors.check("problem index")
    texts = ("anchor", "number", "unit", "heading_title", "title", "first_page", "last_page")
    entries = data.get("problems") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        entries = []
        errors.append(f"{path.name}: no list of problems")
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) \
                or not all(isinstance(entry.get(k), str) for k in texts) \
                or entry.get("status") not in STATUSES \
                or not isinstance(entry.get("parts"), list) \
                or not all(isinstance(x, dict) and isinstance(x.get("anchor"), str)
                           and isinstance(x.get("number"), str) and x.get("status") in STATUSES
                           for x in entry["parts"]):
            errors.append(f"{path.name}: problem {i} has missing or invalid fields")
    errors.check("problem index")
    return entries


def read_manual(reader, anchors, index, errors):
    """Chapters from the top-level bookmarks of main.pdf; their sections and
    problems from the problem index, located in main.pdf by their anchors."""
    tops, boundaries = [], set()
    for level, title, dest in outline_entries(reader):
        if level:
            continue          # sections and problems: from the problem index
        target = anchors.resolve(dest)
        if target is None:
            errors.append(f'bookmark "{title}" has no destination in main.pdf')
            continue
        # Every top-level bookmark starts new pages; only the chapters
        # (hyperref anchor chapter.N) group problems
        boundaries.add(target.page)
        m = re.fullmatch(r"chapter\.(\d+)", target.name or "")
        tops.append((target.page, Chapter(int(m[1]), title, target.page) if m else None))
    errors.check("main.pdf bookmarks")

    # Problems: in a textbook section (unit §N) of a chapter, at the anchor
    # of the index, which starts on the page given by the index
    labels = reader.page_labels
    stale = f"(rebuild with latexmk: are main.pdf and {INDEX} from the same build?)"
    part_entries = {}
    for entry in index:
        where = f'{INDEX}: {entry["unit"]} {PROBLEM} {entry["number"]}'
        unit = UNIT_RE.fullmatch(entry["unit"])
        key = anchor_key(entry["anchor"])
        if not unit or not entry["number"].isdigit() or not key or key[0] != "ProblemNum":
            errors.append(f"{where} is not a problem of a textbook section (§N)")
            continue
        target = anchors.named.get(entry["anchor"])
        if target is None:
            errors.append(f'{where}: no anchor {entry["anchor"]} in main.pdf {stale}')
            continue
        chapter = next((c for p, c in reversed(tops) if p <= target.page), None)
        if chapter is None:
            errors.append(f"{where} is not in a chapter")
            continue
        if not chapter.sections or chapter.sections[-1].number != unit[1]:
            chapter.sections.append(Section(unit[1], entry["heading_title"], chapter))
        section = chapter.sections[-1]
        problem = Problem(int(entry["number"]), key[1], target.page, section,
                          done=STATUSES[entry["status"]],
                          title=" ".join(entry["title"].split()))
        title_anchor = anchors.named.get(f"problem-title.{problem.key}")
        if title_anchor is None or title_anchor.page != target.page:
            errors.append(f"{problem.label}: its title is not on the page of its anchor")
        if labels[problem.start] != entry["first_page"]:
            errors.append(f'{where}: starts on page {entry["first_page"]}, on page '
                          f"{labels[problem.start]} in main.pdf {stale}")
        # Page labels can repeat (front matter): the first match from the start
        problem.end = next((i for i in range(problem.start, len(labels))
                            if labels[i] == entry["last_page"]), -1)
        if problem.end < 0:
            errors.append(f'{where}: no page {entry["last_page"]} after its start in main.pdf {stale}')
        part_entries[problem.key] = entry["parts"]
        section.problems.append(problem)
    chapters = [c for _, c in tops if c is not None and c.sections]
    errors.check(f"{INDEX} against main.pdf")

    problems = [p for c in chapters for p in c.problems]
    by_key = {p.key: p for p in problems}

    # Numbering: unique sections, problems numbered 1, 2, ... in each section
    seen = set()
    for chapter in chapters:
        for section in chapter.sections:
            if section.id in seen:
                errors.append(f"{section.label} appears twice")
            seen.add(section.id)
            numbers = [p.number for p in section.problems]
            if numbers != list(range(1, len(numbers) + 1)):
                errors.append(f"{section.label}: problems numbered {numbers}")

    # Parts: those of the index, (a), (b), ..., at the SubProblemNum anchors
    # of their problem, numbered 1, 2, ..., which main.pdf has all of
    found = {}
    for name in anchors.named:
        key = anchor_key(name)
        if key and key[0] == "SubProblemNum":
            found.setdefault(key[1], set()).add(int(name.rpartition(".")[2]))
    for key in found.keys() - by_key.keys():
        errors.append(f"part anchor of an unknown problem: SubProblemNum.{key}")
    for problem in problems:
        entries = part_entries[problem.key]
        numbers = range(1, len(entries) + 1)
        if len(entries) > 26 \
                or [x["anchor"] for x in entries] != [f"SubProblemNum.{problem.key}.{k}" for k in numbers] \
                or [x["number"] for x in entries] != [f"({chr(96 + k)})" for k in numbers] \
                or found.get(problem.key, set()) != set(numbers):
            errors.append(f"{problem.label}: parts {[x['number'] for x in entries]} in {INDEX}, "
                          f"part anchors {sorted(found.get(problem.key, ()))} in main.pdf {stale}")
            continue
        targets = [anchors.named[x["anchor"]] for x in entries]
        problem.parts = [Part(chr(96 + k), t.page, t.left, t.top, STATUSES[x["status"]])
                         for k, x, t in zip(numbers, entries, targets)]

    # Page ranges: each problem starts on a new page (problem on new page, the
    # default of the class) and ends before the next problem or top-level
    # bookmark (chapter title page)
    starts = [p.start for p in problems]
    if len(set(starts)) != len(starts):
        errors.append("two problems start on the same page: "
                      "every problem must start on a new page")
    boundaries = sorted(boundaries | set(starts))
    last = len(reader.pages) - 1
    for problem in problems:
        later = [b for b in boundaries if b > problem.start]
        if later and problem.end >= later[0]:
            errors.append(f"{problem.label}: pages {problem.start + 1}-{problem.end + 1} "
                          f"run into page {later[0] + 1}, which starts something else")
    errors.check("main.pdf page ranges")

    # A part's anchor is set just before its box; when the box does not fit,
    # it moves to the next page and the anchor stays below the text area of
    # the previous one. Such a part starts at the top of the next page.
    for problem in problems:
        for part in problem.parts:
            box = reader.pages[part.page].mediabox
            if part.top is not None and part.top < float(box.bottom) + TEXT_BOTTOM \
                    and part.page < problem.end:
                part.page += 1
                part.top = float(reader.pages[part.page].mediabox.top)

    # Checks: every anchor of a problem is in its range, and every page after
    # the first chapter is a chapter title or belongs to one problem
    owner = {}
    for problem in problems:
        for page in range(problem.start, problem.end + 1):
            owner[page] = problem
    for name, target in anchors.named.items():
        key = anchor_key(name)
        if key:
            problem = by_key.get(key[1])
            if problem is None:
                errors.append(f"anchor {name} belongs to no problem")
            elif not problem.start <= target.page <= problem.end:
                errors.append(f"anchor {name} of {problem.label} is on page {target.page + 1}, "
                              f"outside its pages {problem.start + 1}-{problem.end + 1}")
    chapter_pages = {c.page for c in chapters}
    if chapters:
        for page in range(min(chapter_pages), last + 1):
            if page not in owner and page not in boundaries:
                errors.append(f"page {page + 1} of main.pdf belongs to no problem")
    errors.check("main.pdf page ranges")
    return chapters, owner


# ============ Titles ============ #

def check_titles(problems, errors):
    """Titles of the problems (title={...} in Chapters/*.tex), as the index
    gives them: plain text, which must fit in the page title."""
    for problem in problems:
        if re.search(r"[\\$]", problem.title):
            errors.append(f'{problem.label}: the title "{problem.title}" is TeX, not plain text '
                          f"(give its plain text with \\texorplain{{TeX}}{{plain text}})")
        # Every problem, so that its page fits once it is solved
        elif len(page_title(problem)) > TITLE_MAX:
            errors.append(f"{problem.label}: its title is too long for the page title "
                          f'"{page_title(problem)}" ({TITLE_MAX} characters at most)')
    errors.check("problem titles")
    for problem in problems:
        if not problem.title:
            warn(f"{problem.label} has no title (title={{...}} in Chapters/*.tex)")


# ============ Problem PDFs ============ #

class Links:
    """URLs of the website, used in the PDFs (absolute, so that a downloaded
    PDF keeps working links)."""

    def __init__(self, base_url, repository):
        self.base = base_url.rstrip("/") + "/"
        self.repository = repository.rstrip("/")

    def site(self, path=""):
        return self.base + path


def page_labels(reader, start, end):
    """Printed page number of the first page if pages start..end are numbered
    consecutively in main.pdf (decimal page labels), else None."""
    labels = reader.page_labels[start:end + 1]
    if all(l.isdigit() for l in labels) and \
            [int(l) for l in labels] == list(range(int(labels[0]), int(labels[0]) + len(labels))):
        return int(labels[0])
    return None


def chapter_at(chapters, page):
    previous = [c for c in chapters if c.page <= page]
    return previous[-1] if previous else None


def write_problem_pdf(reader, anchors, problem, chapters, owner, links, author, path, errors):
    writer = PdfWriter()
    for page in range(problem.start, problem.end + 1):
        writer.add_page(reader.pages[page])

    # Links: named destinations of main.pdf do not exist in the extract
    for page in writer.pages:
        for ref in page.get("/Annots") or []:
            annot = ref.get_object()
            if annot.get("/Subtype") != "/Link":
                continue
            dest, action = annot.get("/Dest"), annot.get("/A")
            if dest is None:
                if action is None or action.get_object().get("/S") != "/GoTo":
                    continue  # external links stay as they are
                dest = action.get_object().get("/D")
            target = anchors.resolve(dest)
            if target is None:
                errors.append(f"{problem.id}: link to an unknown destination {dest}")
                continue
            if "/Dest" in annot:
                del annot["/Dest"]
            prefix = (target.name or "").partition(".")[0]
            other = owner.get(target.page)
            if problem.start <= target.page <= problem.end:
                # Same problem: internal link to the copied page
                new = DictionaryObject({
                    NameObject("/S"): NameObject("/GoTo"),
                    NameObject("/D"): ArrayObject(
                        [writer.pages[target.page - problem.start].indirect_reference] + target.view),
                })
                url = None
            elif prefix in ("chapter-title", "chapter"):
                url = links.site(f"#{chapter_at(chapters, target.page).id}")
            elif other is not None and prefix != "page":
                # Another problem (\probref, \eqref): its PDF, at the page
                url = links.site(f"{other.pdf}#page={target.page - other.start + 1}")
                if prefix in REFERENCE_ANCHORS:
                    problem.refs.add(other.id)
            else:
                url = links.site(f"main.pdf#page={target.page + 1}")
            if url is not None:
                new = DictionaryObject({NameObject("/S"): NameObject("/URI"),
                                        NameObject("/URI"): TextStringObject(url)})
            annot[NameObject("/A")] = new

    # Bookmarks: the problem and its parts
    title = anchors.named[f"problem-title.{problem.key}"]
    top = writer.add_outline_item(problem.label, 0, fit=Fit.xyz(title.left, title.top))
    for part in problem.parts:
        writer.add_outline_item(f"({part.letter})", part.page - problem.start, parent=top,
                                fit=Fit.xyz(part.left, part.top))
    if problem.parts:
        writer.page_mode = "/UseOutlines"

    # The manual's page numbers, as printed in the footers
    first = page_labels(reader, problem.start, problem.end)
    if first is not None:
        writer.set_page_label(0, problem.pages - 1, "/D", start=first)

    status = "" if problem.done else " (not solved yet)"
    title = f"{problem.title} ({problem.label})" if problem.title else \
        f"{problem.label}, {problem.section.title}"
    writer.add_metadata({
        "/Title": f"{title}{status} | Solutions to {BOOK} by {BOOK_AUTHORS}",
        "/Author": author,
        "/Subject": f"Unofficial solution to {problem.label} ({problem.section.title}) of "
                    f"{BOOK} by {BOOK_AUTHORS}, {BOOK_SERIES}",
        "/Keywords": f"Landau, Lifshitz, {BOOK}, classical mechanics, {problem.label}, "
                     f"{problem.section.title}, solution",
    })
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    with open(path, "wb") as out:
        writer.write(out)


# ============ Checks of the output ============ #

HEADER_RE = re.compile(rf"(?:§|(?<!\S))([^\s§]+) {PROBLEM} (\d+)\.$")


def count_bookmarks(outline):
    return sum(count_bookmarks(x) if isinstance(x, list) else 1 for x in outline)


def verify_pdfs(out, problems, links, errors):
    """Reopen every problem PDF: pages (running header of each page), links
    and bookmarks."""
    pages = {p.id: p.pages for p in problems}
    pdf_url = re.compile(re.escape(links.site("pdf/")) + r"([\w-]+)\.pdf#page=(\d+)$")
    for problem in problems:
        reader = PdfReader(out / problem.pdf)
        where = problem.id
        if len(reader.pages) != problem.pages:
            errors.append(f"{where}: {len(reader.pages)} pages, expected {problem.pages}")
        refs = {p.indirect_reference.idnum for p in reader.pages}
        for i, page in enumerate(reader.pages, 1):
            lines = (page.extract_text() or "").strip().splitlines()
            m = HEADER_RE.search(lines[0]) if lines else None
            if not m or m[1].lstrip("§") != problem.section.number or int(m[2]) != problem.number:
                errors.append(f"{where}: page {i} has the header {lines[:1]}, "
                              f"expected {problem.label}.")
            for ref in page.get("/Annots") or []:
                annot = ref.get_object()
                action = annot.get("/A")
                if annot.get("/Subtype") != "/Link" or action is None:
                    continue
                action = action.get_object()
                if action.get("/S") == "/GoTo":
                    dest = action.get("/D")
                    if not isinstance(dest, ArrayObject) or getattr(dest[0], "idnum", None) not in refs:
                        errors.append(f"{where}: page {i} has a link outside the PDF ({dest})")
                elif action.get("/S") == "/URI":
                    m = pdf_url.match(str(action["/URI"]))
                    if m and not (m[1] in pages and 1 <= int(m[2]) <= pages[m[1]]):
                        errors.append(f"{where}: page {i} links to a missing page {action['/URI']}")
        bookmarks = count_bookmarks(reader.outline)
        if bookmarks != 1 + len(problem.parts):
            errors.append(f"{where}: {bookmarks} bookmarks, expected {1 + len(problem.parts)}")
    errors.check("problem PDFs")


class PageParser(HTMLParser):
    """Links, ids and metadata of a generated page."""

    def __init__(self):
        super().__init__()
        self.links, self.ids, self.meta, self.canonical = [], set(), {}, []
        self.title, self.h1, self._in = "", 0, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for name in ("href", "src", "data"):
            if attrs.get(name) is not None and not (tag == "link" and attrs.get("rel") == "canonical"):
                self.links.append(attrs[name])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical.append(attrs.get("href"))
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key:
                self.meta[key] = attrs.get("content")
        if tag == "h1":
            self.h1 += 1
        self._in = tag

    def handle_endtag(self, tag):
        self._in = None

    def handle_data(self, data):
        if self._in == "title":
            self.title += data


def verify_site(out, problems, links, manual_pages, errors):
    """Reopen every page: one canonical URL (its own address), unique titles and
    descriptions, and links to files, anchors and PDF pages that exist; then
    the sitemap: exactly the expected URLs, all published."""
    pages = {"index.html": ""} | {p.page: p.page for p in problems if p.done}
    pdf_pages = {p.pdf: p.pages for p in problems} | {"main.pdf": manual_pages}
    if sorted(f.relative_to(out).as_posix() for f in out.rglob("*.html")) != sorted(pages):
        errors.append("the HTML pages are not the homepage and the solved-problem pages")
    errors.check("website pages")
    parsed = {}
    for path in pages:
        parser = PageParser()
        parser.feed((out / path).read_text(encoding="utf-8"))
        parsed[path] = parser
    for path, page in parsed.items():
        if page.canonical != [links.site(pages[path])]:
            errors.append(f"{path}: canonical {page.canonical}, expected {links.site(pages[path])}")
        if page.meta.get("og:url") != links.site(pages[path]):
            errors.append(f"{path}: og:url {page.meta.get('og:url')}")
        if not page.title.strip() or not page.meta.get("description") or page.h1 != 1:
            errors.append(f"{path}: needs a title, a description and one h1")
        elif not DESCRIPTION_RANGE[0] <= len(page.meta["description"]) <= DESCRIPTION_RANGE[1]:
            errors.append(f"{path}: description of {len(page.meta['description'])} characters, "
                          f"not {DESCRIPTION_RANGE[0]}-{DESCRIPTION_RANGE[1]} "
                          f"(shorten its title in Chapters/*.tex)")
        elif len(page.title) > TITLE_MAX:
            errors.append(f"{path}: title of {len(page.title)} characters, over {TITLE_MAX}")
        for link in page.links:
            url = urllib.parse.urlsplit(link)
            if url.scheme or url.netloc:
                continue      # external
            target = (Path(path).parent / urllib.parse.unquote(url.path)).as_posix() \
                if url.path else path
            target = posixpath.normpath(target)
            if url.path.endswith("/") or target == ".":
                target = posixpath.join(target, "index.html").removeprefix("./")
            if target.startswith("../") or not (out / target).is_file():
                errors.append(f"{path}: broken link {link}")
            elif url.fragment and target.endswith(".html") and url.fragment not in parsed[target].ids:
                errors.append(f"{path}: link to a missing anchor {link}")
            elif url.fragment and target.endswith(".pdf"):
                m = re.fullmatch(r"page=(\d+)", url.fragment)
                if not m or not 1 <= int(m[1]) <= pdf_pages[target]:
                    errors.append(f"{path}: link to a missing PDF page {link}")
    for key in ("title", "description"):
        values = [p.title if key == "title" else p.meta.get("description") for p in parsed.values()]
        if len(set(values)) != len(values):
            errors.append(f"two pages have the same {key}")
    if parsed["index.html"].meta.get("google-site-verification") != GOOGLE_SITE_VERIFICATION:
        errors.append("index.html: the Google Search Console verification tag is missing")

    root = ElementTree.parse(out / "sitemap.xml").getroot()
    locs = [e.text for e in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    if locs != [links.site(u) for u in site_paths(problems)]:
        errors.append("sitemap.xml does not list the expected URLs")
    for loc in locs:
        path = loc.removeprefix(links.site()) or "index.html"
        if not loc.startswith(links.site()) or not (out / path).is_file():
            errors.append(f"sitemap.xml: {loc} is not a published file")
    errors.check("website pages")


# ============ Catalogue ============ #

def catalogue_data(chapters, links, manual_pages, author):
    problems = [p for c in chapters for p in c.problems]

    def problem_data(p):
        return {
            "id": p.id,
            "number": p.number,
            "label": p.label,
            "title": p.title or None,
            "done": p.done,
            "page": p.page,
            "pdf": p.pdf,
            "pages": p.pages,
            "manual_pages": [p.start + 1, p.end + 1],
            "parts": [{"id": f"{p.id}{x.letter}", "letter": x.letter, "done": x.done,
                       "page": x.page - p.start + 1} for x in p.parts],
            "references": sorted(p.refs, key=order.get),
            "referenced_by": sorted(p.cited_by, key=order.get),
        }

    order = {p.id: i for i, p in enumerate(problems)}
    return {
        "schema": 1,
        "title": f"Solutions to {BOOK} by {BOOK_AUTHORS}",
        "book": BOOK_REFERENCE,
        "author": author,
        "site": links.site(),
        "repository": links.repository,
        "manual": {"pdf": "main.pdf", "pages": manual_pages},
        "done": done_count(problems),
        "total": len(problems),
        "chapters": [{
            "id": c.id,
            "number": c.number,
            "title": c.title,
            "manual_page": c.page + 1,
            "done": done_count(c.problems),
            "total": len(c.problems),
            "sections": [{
                "id": s.id,
                "number": s.number,
                "label": s.label,
                "title": s.title,
                "done": done_count(s.problems),
                "total": len(s.problems),
                "problems": [problem_data(p) for p in s.problems],
            } for s in c.sections],
        } for c in chapters],
    }


# ============ Website ============ #
# The catalogue lists every problem by chapter and section; a solved problem
# links to its page, which shows its PDF, and an unsolved one to its PDF. No
# script: the pages are plain HTML and CSS. Links between pages are relative,
# so the site works under any base URL; canonical URLs are absolute.

def esc(text):
    return html.escape(str(text), quote=True)


def rich(text):
    """Escaped text with subscripts: M_z (a title's \\texorplain{$M_z$}{M\\_z})."""
    return re.sub(r"(?<=\S)_([A-Za-z0-9]+)", r"<sub>\1</sub>", esc(text))


def plain(text):
    """Text without the subscript marks, for titles and metadata."""
    return re.sub(r"(?<=\S)_([A-Za-z0-9]+)", r"\1", text)


def json_ld(data):
    text = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{text}\n</script>'


def person(name):
    return {"@type": "Person", "name": name}


def book_ld():
    b = BOOK_REFERENCE
    return {"@type": "Book", "name": b["title"], "author": [person(a) for a in b["authors"]],
            "bookEdition": b["edition"], "datePublished": str(b["year"]),
            "isbn": b["isbn"], "publisher": {"@type": "Organization", "name": b["publisher"]}}


def render_head(title, description, canonical, root, og_type, structured, extra=""):
    """<head> of a page; root is the relative path to the site root."""
    return f"""<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{esc(SITE_AUTHOR)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(SITE_TITLE)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary">
{extra}<link rel="stylesheet" href="{root}style.css">
{json_ld(structured)}
</head>"""


def render_footer(links):
    return f"""<footer>
<p>Solutions © 2026 {esc(SITE_AUTHOR)},
<a href="{LICENSE_URL}">CC BY 4.0</a>.
Unofficial: not endorsed by the authors or the publisher of the book.
<a href="{esc(links.repository)}/issues/new">Report an error on GitHub</a>.</p>
</footer>"""


def render_problem(problem):
    title = f'<span class="number">{PROBLEM} {problem.number}</span> {rich(problem.heading)}'
    if problem.done:
        return f'<li id="{problem.id}"><a href="{problem.href}">{title}</a></li>'
    return (f'<li id="{problem.id}" class="todo"><a href="{problem.href}">{title}</a> '
            f'<span class="status">Not done</span></li>')


def render_index(chapters, links, manual_pages, manual_size):
    problems = [p for c in chapters for p in c.problems]
    done, total = done_count(problems), len(problems)
    b = BOOK_REFERENCE
    body = []
    for c in chapters:
        body.append(f'<section id="{c.id}">')
        body.append(f'<h2>{CHAPTER} {c.number}. {esc(c.title)}</h2>')
        for s in c.sections:
            body.append(f'<h3 id="{s.id}">{esc(s.label)} {esc(s.title)}</h3>')
            body.append('<ul class="problems">')
            body.extend(render_problem(p) for p in s.problems)
            body.append("</ul>")
        body.append("</section>")
    title = f"{BOOK_AUTHORS} {BOOK}: Solution Manual"
    description = (f"Unofficial solution manual for {BOOK_AUTHORS}, {BOOK} (Course of "
                   f"Theoretical Physics, Vol. 1): worked solutions to the problems, "
                   f"{done} of {total} so far.")
    structured = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_TITLE,
        "url": links.site(),
        "description": description,
        "inLanguage": "en",
        "author": person(SITE_AUTHOR),
        "license": LICENSE_URL,
        "about": book_ld(),
    }
    verification = f'<meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">\n'
    return f"""<!doctype html>
<html lang="en">
{render_head(title, description, links.site(), "", "website", structured, verification)}
<body>
<header>
<h1>Solutions to {esc(BOOK_AUTHORS)}, <em>{esc(BOOK)}</em></h1>
<p class="lead">An unofficial solution manual: worked solutions to the problems of
<cite>{esc(BOOK)}</cite>, {esc(BOOK_SERIES)}, by chapter and section of the book.
Each solved problem has its own page and PDF; the whole manual is a single PDF.</p>
<p class="reference">{esc(" and ".join(b["authors"]))}, <cite>{esc(BOOK)}</cite>, 3rd ed. ({b["year"]}) ·
solutions by {esc(SITE_AUTHOR)}</p>
<p class="actions"><a class="button" href="main.pdf">Download the full manual</a>
<span class="note">PDF, {manual_pages} pages, {human_size(manual_size)}</span> ·
<a href="{esc(links.repository)}">GitHub</a></p>
<p class="progress">{done} of {total} problems solved</p>
</header>
<main>
{chr(10).join(body)}
</main>
{render_footer(links)}
</body>
</html>
"""


def page_title(problem):
    """<title> of a problem page: label and title, with the site name when it
    fits in TITLE_MAX characters."""
    title = f"{problem.label}: {plain(problem.title or problem.section.title)}"
    named = f"{title} | {SITE_NAME}"
    return named if len(named) <= TITLE_MAX else title


def render_problem_page(problem, previous, following, links, pdf_size):
    s, c = problem.section, problem.section.chapter
    subject = problem.title or s.title
    canonical = links.site(problem.page)
    pdf = f"../{problem.pdf}"
    pages = f"{problem.pages} page{'s' if problem.pages > 1 else ''}"
    title = page_title(problem)
    # At most 160 characters, as search results show (checked by verify_site)
    description = (f"Worked solution to {problem.label} of {BOOK_AUTHORS}, {BOOK}: "
                   f"{plain(subject)}. PDF, {pages}.")
    crumbs = [(SITE_TITLE, links.site(), "../"),
              (f"{CHAPTER} {c.number}. {c.title}", links.site(f"#{c.id}"), f"../#{c.id}"),
              (f"{s.label} {s.title}", links.site(f"#{s.id}"), f"../#{s.id}"),
              (problem.label, canonical, None)]
    structured = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i, "name": name, "item": url}
                for i, (name, url, _) in enumerate(crumbs, 1)]},
            {"@type": "LearningResource",
             "name": f"{problem.label}: {plain(subject)}",
             "description": description,
             "url": canonical,
             "learningResourceType": "Worked solution",
             "inLanguage": "en",
             "author": person(SITE_AUTHOR),
             "license": LICENSE_URL,
             "isPartOf": {"@type": "WebSite", "name": SITE_TITLE, "url": links.site()},
             "about": book_ld(),
             "encoding": {"@type": "MediaObject", "contentUrl": links.site(problem.pdf),
                          "encodingFormat": "application/pdf"}},
        ],
    }

    trail = " › ".join(f'<a href="{href}">{esc(name)}</a>' for name, _, href in crumbs[:-1])
    body = [f'<nav class="breadcrumb" aria-label="Breadcrumb">{trail}</nav>',
            "<header>",
            f'<h1><span class="label">{esc(problem.label)}</span> {rich(subject)}</h1>',
            f'<p class="lead">A worked solution to {PROBLEM} {problem.number} of {esc(s.label)}, '
            f'<i>{esc(s.title)}</i>, in {CHAPTER} {c.number}, <i>{esc(c.title)}</i>, of '
            f'{esc(" and ".join(BOOK_REFERENCE["authors"]))}, <cite>{esc(BOOK)}</cite>, '
            f'3rd ed. ({BOOK_REFERENCE["year"]}). Solution by {esc(SITE_AUTHOR)}.</p>',
            f'<p class="actions"><a class="button" href="{pdf}">Open the solution (PDF)</a> '
            f'<a href="{pdf}" download>Download</a> '
            f'<span class="note">{pages}, {human_size(pdf_size)} · pages '
            f'{problem.start + 1}–{problem.end + 1} of the '
            f'<a href="../main.pdf#page={problem.start + 1}">full manual</a></span></p>',
            "</header>",
            "<main>",
            f'<object class="viewer" data="{pdf}" type="application/pdf" '
            f'aria-label="{esc(problem.label)} solution (PDF)">',
            f'<p class="note">Your browser cannot show the PDF here: '
            f'<a href="{pdf}">open the solution (PDF)</a>.</p>',
            "</object>"]
    if problem.parts:
        parts = " · ".join(f'<a href="{pdf}#page={x.page - problem.start + 1}">({x.letter})</a>'
                           for x in problem.parts)
        body.append(f'<p class="parts">Parts: {parts}</p>')
    pager = []
    if previous:
        pager.append(f'<a rel="prev" href="{previous.id}.html">← {esc(previous.label)}</a>')
    pager.append('<a href="../">All problems</a>')
    if following:
        pager.append(f'<a rel="next" href="{following.id}.html">{esc(following.label)} →</a>')
    body.append(f'<nav class="pager" aria-label="Solved problems">{" ".join(pager)}</nav>')
    body.append("</main>")
    return f"""<!doctype html>
<html lang="en">
{render_head(title, description, canonical, "../", "article", structured)}
<body class="problem-page">
{chr(10).join(body)}
{render_footer(links)}
</body>
</html>
"""


def site_paths(problems):
    """Paths of the sitemap: the homepage, the solved-problem pages, the full
    manual and the solved-problem PDFs."""
    solved = [p for p in problems if p.done]
    return [""] + [p.page for p in solved] + ["main.pdf"] + [p.pdf for p in solved]


def render_sitemap(problems, links):
    entries = "".join(f"  <url><loc>{esc(links.site(u))}</loc></url>\n"
                      for u in site_paths(problems))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{entries}</urlset>\n")


def human_size(size):
    return f"{size / 1e6:.1f} MB" if size >= 1e6 else f"{size / 1e3:.0f} kB"


def write_text(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


# ============ Main ============ #

# Marks an output folder as written by this script, even after a failed build
# (a hidden file, left out of the Pages artifact)
MARKER = ".website-build"


def prepare_output(out):
    """Empty the output folder, refusing anything but a previous build."""
    if out == ROOT or out in ROOT.parents:
        sys.exit(f"--out {out} would overwrite the project")
    if out.exists():
        if any(out.iterdir()) and not (out / MARKER).is_file():
            sys.exit(f"{out} is not empty and is not a previous website build: choose another --out")
        shutil.rmtree(out)
    (out / "pdf").mkdir(parents=True)
    (out / "problems").mkdir()
    write_text(out / MARKER, "Written by site/build.py: deleted at each build.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=str(ROOT / "_site"), help="output folder (default: _site)")
    parser.add_argument("--base-url", default="",
                        help="public URL of the site (default: the GitHub Pages URL of --repository)")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY, help="GitHub repository URL")
    args = parser.parse_args()

    base_url = args.base_url
    if not base_url:
        owner, repo = urllib.parse.urlparse(args.repository).path.strip("/").split("/")[:2]
        base_url = f"https://{owner.lower()}.github.io/{repo}/"
    links = Links(base_url, args.repository)
    out = Path(args.out).resolve()
    errors = Errors()

    for name in ("main.pdf", INDEX):
        if not (ROOT / name).is_file():
            sys.exit(f"{name} is missing: build the manual first with latexmk")
    reader = PdfReader(ROOT / "main.pdf")
    anchors = Anchors(reader)
    author = (reader.metadata or {}).get("/Author") or "P.O. Bolduc"
    chapters, owner = read_manual(reader, anchors, read_index(ROOT / INDEX, errors), errors)
    problems = [p for c in chapters for p in c.problems]
    check_titles(problems, errors)

    prepare_output(out)
    for problem in problems:
        write_problem_pdf(reader, anchors, problem, chapters, owner, links, author,
                          out / problem.pdf, errors)
    errors.check("problem PDFs")
    by_id = {p.id: p for p in problems}
    for problem in problems:
        for ref in problem.refs:
            by_id[ref].cited_by.add(problem.id)
    verify_pdfs(out, problems, links, errors)

    shutil.copyfile(ROOT / "main.pdf", out / "main.pdf")
    manual_pages = len(reader.pages)
    data = catalogue_data(chapters, links, manual_pages, author)
    write_text(out / "catalogue.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    write_text(out / "index.html", render_index(chapters, links, manual_pages,
                                                (ROOT / "main.pdf").stat().st_size))
    solved = [p for p in problems if p.done]
    for i, problem in enumerate(solved):
        previous = solved[i - 1] if i > 0 else None
        following = solved[i + 1] if i + 1 < len(solved) else None
        write_text(out / problem.page,
                   render_problem_page(problem, previous, following, links,
                                       (out / problem.pdf).stat().st_size))
    write_text(out / "sitemap.xml", render_sitemap(problems, links))
    shutil.copyfile(HERE / "style.css", out / "style.css")
    verify_site(out, problems, links, manual_pages, errors)

    sections = [s for c in chapters for s in c.sections]
    pdf_size = sum((out / p.pdf).stat().st_size for p in problems)
    print(f"{len(chapters)} chapters, {len(sections)} sections, {len(problems)} problems "
          f"({done_count(problems)} solved, {sum(len(p.parts) for p in problems)} parts, "
          f"{sum(len(p.refs) for p in problems)} cross-problem links)")
    print(f"{len(problems)} problem PDFs, {sum(p.pages for p in problems)} pages, "
          f"{human_size(pdf_size)}; {len(solved)} problem pages; website in {out}")


if __name__ == "__main__":
    main()
