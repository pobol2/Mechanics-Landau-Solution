# Solution Manual to Mechanics by Landau and Lifshitz

These are my humble, unofficial solutions to *Mechanics* by Landau and
Lifshitz (Volume 1 of the Course of Theoretical Physics). I am an engineer,
not a physicist, and this manual is a personal learning project. The work is
ongoing, and corrections and suggestions are welcome: feel free to open an
issue or a pull request.

Author: P.O. Bolduc

**[Read the manual (main.pdf)](main.pdf)**

## How it is built

The manual uses the
[Solution Manual Template](https://github.com/pobol2/Solution-Manual-Template),
included as a Git submodule in `template/`. Its `template/solution-manual/`
folder provides the shared framework: the document classes (problem, solution
and answer boxes, title page, headers), the general figure class and the
`latexmk` build rules. The template's own sources are never edited here.

Everything specific to Mechanics stays in this repository:

```
main.tex              Titles, author, 10pt option and chapter list
Chapters/             One file per chapter of the book
Figures/*.tex         Standalone TikZ figures (compiled with LuaLaTeX)
mypackages.sty        Packages of the manual
mycommands.sty        Commands of the manual
myfigures.sty         Physics figure styles: bodies, vectors, 3D views, fields
SolutionFigure.lua    Numerical field lines and equipotentials for the figures
latexmkrc             Loads template/solution-manual/latexmkrc
```

The physics-specific figure styles and the Lua field tools are deliberately
kept local in `myfigures.sty` and `SolutionFigure.lua`: the template stays
general, and the shared figure class loads `myfigures.sty` automatically.

## Getting the sources

Clone with the submodule:

```sh
git clone --recurse-submodules https://github.com/pobol2/Mechanics-Landau-Solution.git
```

In an existing clone, or if `template/` is empty:

```sh
git submodule update --init --recursive
```

## Building

Prerequisites: a TeX distribution (MiKTeX or TeX Live) with pdfLaTeX,
LuaLaTeX and `latexmk`, and Perl (on Windows, e.g. Strawberry Perl). Allow
MiKTeX to install missing packages when prompted.

From the repository root, run:

```sh
latexmk
```

pdfLaTeX compiles the manual, and LuaLaTeX compiles each figure only when its
source, `myfigures.sty`, `SolutionFigure.lua` or a shared class changes.

| Location      | Contents                                                  |
| ------------- | --------------------------------------------------------- |
| `main.pdf`    | The finished manual: the only generated file in the root |
| `Figures/*.pdf` | Generated figures (ignored by Git)                      |
| `build/`      | Temporary files: logs, SyncTeX, figure compilations (`build/figures-aux/`) |

### VS Code

Install the LaTeX Workshop extension and open the repository folder. The
tracked `.vscode/settings.json` makes **LaTeX Workshop: Build LaTeX project**
(or saving a file) run the same `latexmk` command. The viewer shows
`build/main.pdf`, with SyncTeX forward and inverse search.

## Updating the template

The submodule is pinned to a specific template commit, so template changes
are adopted deliberately:

```sh
git submodule update --remote template
latexmk
```

Review the rebuilt manual, then commit the new `template` reference together
with any needed project changes. Never edit files inside `template/`; put
customizations in this repository's own files instead.
