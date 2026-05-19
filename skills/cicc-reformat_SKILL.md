---
name: cicc-reformat
description: |
  Reformat existing LaTeX manuscripts to comply with CiCC (Communications in Computational Chemistry) journal standards. Use this skill whenever the user has an existing .tex file (not a Word document) that needs to be reformatted, standardized, or corrected to match CiCC journal requirements. Trigger on phrases like "reformat my tex", "fix this latex for CiCC", "standardize my latex", "cicc-reformat", or any request to convert or clean up an existing LaTeX file for CiCC submission. Input may include a .bib file or inline thebibliography. Do NOT use this skill for Word-to-LaTeX conversion — use cicc-latex for that.
---

# CiCC LaTeX Reformatting Workflow

This skill takes an existing `.tex` manuscript (originally written in LaTeX, not converted from Word) and reformats it to comply fully with CiCC journal standards. The content is already present — the work is diagnosis, structural correction, and rule enforcement.

## Overview of Steps

1. **Read the input** — `.tex` file plus any `.bib` file(s) and `figures/` folder
2. **Diagnose** — scan for all rule violations and produce a diff list before touching anything
3. **Fix preamble** — restructure to match CiCC template exactly
4. **Fix document body** — apply all formatting rules (capitalization, citations, floats, equations)
5. **Fix references** — handle `.bib` or inline `thebibliography` per the strategy below
6. **Package output** — zip `.tex` + `cicc.cls` + `figures/` (+ `.bib` if used)

---

## Step 1 — Read Input Files

Before making any changes, identify what has been provided:

```
Input checklist:
- [ ] .tex file (required)
- [ ] .bib file(s) (optional — triggers Situation A reference workflow)
- [ ] figures/ folder (optional — keep as-is if images already in correct format)
- [ ] cicc.cls (optional — will be needed for final zip)
```

Read the `.tex` file fully. Note the current `\documentclass`, preamble packages, bibliography method (`\bibliography{}` vs `\begin{thebibliography}`), and float environments used.

---
	
## Step 2 — Diagnose Before Modifying

Run a full diagnostic scan on the raw `.tex` file. Output a **Diagnostic Report** showing all issues found, grouped by category, before writing a single line of output. This lets the user see the scope of changes.

```python
import re

with open("manuscript.tex") as f:
    content = f.read()

issues = []

# Citation placement
for m in re.finditer(r'[.,;]\s*\\cite\{', content):
    line = content[:m.start()].count('\n') + 1
    issues.append(('CITE_PUNCT', line, m.group()))

# Fig. / Tab. abbreviations
for m in re.finditer(r'\b(Fig\.|Tab\.|Tbl\.)', content):
    line = content[:m.start()].count('\n') + 1
    issues.append(('ABBREV', line, m.group()))

# figure* / scheme* with wrong placement specifier
for m in re.finditer(r'\\begin\{(figure|scheme)\*\}\s*\[(.*?)\]', content):
    spec = m.group(2)
    if any(x in spec for x in ['h', 'b', 'H']):
        line = content[:m.start()].count('\n') + 1
        issues.append(('FLOAT_SPEC', line, m.group()))

# Wrong document class
if not re.search(r'\\documentclass\{cicc\}', content):
    issues.append(('DOCCLASS', 1, 'documentclass is not {cicc}'))

# Missing twocolumn block
if not re.search(r'\\twocolumn\s*\[', content):
    issues.append(('TWOCOL', 0, 'twocolumn[{...}] block missing'))

# keywords outside abstract
abstract_match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', content, re.DOTALL)
if abstract_match:
    if '\\keywords' not in abstract_match.group(1):
        issues.append(('KEYWORDS_POS', 0, '\\keywords not inside abstract environment'))

# Author name format in bibitem (initials-first)
for m in re.finditer(r'\\bibitem.*?\n\s*[A-Z]\.[~\s]', content, re.DOTALL):
    line = content[:m.start()].count('\n') + 1
    issues.append(('AUTHOR_FORMAT', line, 'possible initials-first author name'))

# \hline in tables (should use booktabs three-line style)
for m in re.finditer(r'\\hline', content):
    line = content[:m.start()].count('\n') + 1
    issues.append(('TABLE_HLINE', line, r'\hline found — replace with \toprule/\midrule/\bottomrule'))

# Vertical lines in tabular column spec
for m in re.finditer(r'\\begin\{tabular\}\{[^}]*\|[^}]*\}', content):
    line = content[:m.start()].count('\n') + 1
    issues.append(('TABLE_VLINE', line, 'vertical line | in tabular column spec — remove'))

# table* with wrong placement specifier
for m in re.finditer(r'\\begin\{table\*\}\s*\[([^\]]*)\]', content):
    spec = m.group(1)
    if '!t' not in spec and 'p' not in spec:
        line = content[:m.start()].count('\n') + 1
        issues.append(('TABLE_SPEC', line, f'table* uses [{spec}] — should be [!t]'))

# table (single-col) with wrong placement specifier
for m in re.finditer(r'\\begin\{table\}(?!\*)\s*\[([^\]]*)\]', content):
    spec = m.group(1)
    if spec not in ('h!', '!h'):
        line = content[:m.start()].count('\n') + 1
        issues.append(('TABLE_SPEC', line, f'table uses [{spec}] — should be [h!]'))

# Disallowed equation environments/syntax
for m in re.finditer(r'\\begin\{eqnarray\*?\}', content):
    line = content[:m.start()].count('\n') + 1
    issues.append(('EQUATION_ENV', line, 'eqnarray found — replace with equation+split, align, or widetext'))

for m in re.finditer(r'(?<!\\)\$\$', content):
    line = content[:m.start()].count('\n') + 1
    issues.append(('EQUATION_DOLLARS', line, '$$ display math found — replace with equation environment'))

# Long equation source lines likely to overflow in two-column layout
for m in re.finditer(r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', content, re.DOTALL):
    body = m.group(1)
    if '\\begin{split}' not in body and '\\begin{aligned}' not in body:
        long_lines = [ln for ln in body.splitlines() if len(ln.strip()) > 110]
        if long_lines:
            line = content[:m.start()].count('\n') + 1
            issues.append(('EQUATION_LONG', line, 'long one-line equation — split for two-column layout'))

print(f"Total issues found: {len(issues)}")
for cat, line, detail in issues:
    print(f"  [{cat}] line {line}: {detail}")
```

Present the diagnostic report to the user, then proceed with fixes.

---

## Step 3 — Fix Preamble

### 3.1 Document Class

The output file must start exactly with:

```latex
\documentclass{cicc}
```

Do not place comments or any other text before `\documentclass{cicc}`.

From `\documentclass{cicc}` through the end of the opening `\twocolumn[{...}]` abstract block, follow the fixed opening frame embedded in the Converter prompt. Do not copy the author's source preamble wholesale.

Keep only author packages that are actually required by the converted body. Remove any `\usepackage` commands that duplicate packages already loaded by `cicc.cls`. The following are built-in and must NOT be re-declared:

| Already in cicc.cls — REMOVE if present |
|---|
| `natbib` |
| `graphicx` |
| `amsmath`, `amssymb` |
| `hyperref` |
| `geometry` |
| `fontenc` |
| `inputenc` |
| `newtxtext`, `newtxmath` |
| `microtype` |
| `xcolor` (basic) |
| `etoolbox` |
| `calc`, `xstring` |
| `authblk` |
| `cuted`, `abstract` |
| `fancyhdr` |
| `caption` |

Keep any domain-specific packages the author added (e.g. `chemfig`, `mhchem`, `algorithm`, `listings`) only when the body actually uses them and they do not conflict with `cicc.cls`.

Do not load `amsthm`. If theorem-like environments are needed, use basic `\newtheorem` definitions. If evaluator feedback reports a package or command conflict, the next attempt must remove or replace the conflicting package or command instead of re-adding it.

### 3.2 Metadata Fields

Ensure all required metadata commands are present in this order after `\documentclass{cicc}`:

```latex
\articletype{...}

\doi{doi: 10.4208/cicc.2026.xxx.xx}
\publishedyear{2026}
\volume{xx}
\issue{xx}
\pagenumbers{xx - xx}

\receiveddate{dd/mm/yyyy}
\revisiondate{dd/mm/yyyy}
\accepteddate{dd/mm/yyyy}
\onlinedate{dd/mm/yyyy}
\publisheddate{dd/mm/yyyy}
```

If a field is missing from the original `.tex`, add it with the standard placeholder. **Never invent values.**

### 3.3 Author and Affiliation Structure

Each author must have a separate `\author[N]{Name}` command. If the original uses a combined author list (e.g. `\author{A, B and C}`), split into individual commands.

Affiliations must use `\affil[N]{\textit{...}}`. The last affiliation before `\affil[*]` must end with `\protect\vspace{1em}`.
All `\title`, `\author`, and `\affil` commands must appear before `\begin{document}`.

```latex
\author[1]{First Author}
\author[2,*]{Corresponding Author}

\affil[1]{\textit{Department, University, City, Country}}
\affil[2]{\textit{Department, University, City, Country}
\protect\vspace{1em}}

\affil[*]{Corresponding author: email@example.com}
```

---

## Step 4 — Fix Document Body

### 4.1 twocolumn Opening Block

The opening block must follow the fixed opening frame embedded in the Converter prompt. If the document does not have the `\twocolumn[{...}]` wrapper, restructure the opening to:

```latex
\begin{document}

\twocolumn[{
  \vspace*{0.5em}
  \maketitle
  \thispagestyle{firstpage}
  \label{firstpage}

\begin{abstract}
Abstract text here.

\keywords{...}
\end{abstract}

}]

\section{Introduction}
```

Move `\keywords{...}` inside `\begin{abstract}...\end{abstract}` if it is currently outside.
Keep `\maketitle`, `\thispagestyle{firstpage}`, `\label{firstpage}`, `abstract`, and `\keywords{...}` inside the same `\twocolumn[{...}]` block. Start the converted manuscript body after this block, normally with the first `\section{...}`.

### 4.2 Title Capitalization (Title Case)

The main title must capitalize all major words. Minor words (in, and, of, the, a, an, for, to, with, on, at, by, from) are lowercase unless first word.

Check and correct the argument of `\title[...]{...}`.

### 4.3 Section Heading Capitalization (Sentence Case)

All `\section{...}` and `\subsection{...}` must use sentence case — only first word capitalized, plus proper nouns and established abbreviations.
Do not use Title Case or ALL CAPS for section, subsection, or subsubsection headings. The evaluator reports obvious violations as `section-heading-case`; fix every reported heading.

**Common fixes:**
- `\section{Results and Discussion}` → `\section{Results and discussion}`
- `\section{Theoretical Method}` → `\section{Theoretical method}`
- `\section{Computational Details}` → `\section{Computational details}`
- `\section{Computational Methods}` → `\section{Computational methods}`
- `\section{COMPUTATIONAL METHODS}` → `\section{Computational methods}`

### 4.4 Keywords

`\keywords{...}` must use commas (not semicolons), be entirely lowercase except proper nouns/abbreviations, and end with a period.

- `\keywords{Valence Bond; DFT; Electron Transfer}` → `\keywords{valence bond, DFT, electron transfer.}`

### 4.5 Citation Placement

Move all `\cite{...}` that appear after punctuation to before the punctuation. Apply to both periods and commas.

- `...ago.\cite{ref1}` → `...ago\cite{ref1}.`
- `...concepts,\cite{ref7} with` → `...concepts\cite{ref7}, with`

### 4.6 Figure/Table Abbreviations

Replace all `Fig.` with `Figure` and `Tab.`/`Tbl.` with `Table` throughout body text and captions.

### 4.7 Float Environment Fixes

Placement specifiers — apply uniformly to all float types:
- `figure*`, `scheme*`, `table*`: change any of `[h]`, `[b]`, `[H]`, `[htbp]`, `[!htbp]` → `[!t]`
- `figure`, `scheme`, `table` (single-column): change `[t]`, `[H]`, `[htbp]`, `[!htbp]` → `[h!]`

Width fixes:
- Single-image `figure*` / `scheme*`: ensure `width=0.9\textwidth`
- Multi-panel `figure*` / `scheme*` with multiple `\includegraphics`, `\subfloat`, or subfigure markup: use per-panel relative widths such as `0.2--0.5\textwidth` so the combined panels fit; do not force each subimage to `0.9\textwidth`
- `figure` / `scheme`: ensure `width=1.0\linewidth`
- Multi-panel figures, figures with text labels, structural schemes, plots with axes/legends, and images wider than tall should use `figure*` / `scheme*` by default.

Caption position — **MANDATORY, NO EXCEPTIONS:**
- Figures/Schemes: `\includegraphics` **MUST come BEFORE** `\caption` (image above caption). `\caption` must NEVER appear before `\includegraphics` in a figure or scheme.
- Tables: `\caption` must come **before** `\begin{tabular}` (caption above table)
- `\label` must come immediately after `\caption` for both figure/scheme and table floats.
- Do not use `widefigure`, `widescheme`, or `widetable`; replace them with `figure*`, `scheme*`, or `table*`.

Add `\centering` inside every float if missing.

### 4.8 Three-Line Table Conversion

All tables must use `booktabs` three-line style. If `\usepackage{booktabs}` is not in the preamble, add it (unless already loaded by `cicc.cls`).

**For every `tabular` environment:**

1. Replace all `\hline` with the correct booktabs command:
   - First `\hline` (after column spec) → `\toprule`
   - Second `\hline` (after header row) → `\midrule`
   - Last `\hline` (at end) → `\bottomrule`
   - Any additional `\hline` between data rows → **delete** (no interior rules allowed)

2. Remove all vertical line characters `|` from the column specification:
   - `{|l|c|c|}` → `{lcc}`
   - `{|l|c|r|c|c|}` → `{lcrcc}`

3. If the original table has multi-level headers using `\hline`, convert to `\cmidrule`:
   - A `\hline` spanning only some columns after a `\multicolumn` row → `\cmidrule(lr){a-b}`

4. If a table is too wide for one column:
   - Convert `table` to `table*` with `[!t]`
   - Prefer shorter headings, `p{...}` columns, or reduced tabular content before using `\resizebox`
   - Keep table notes below the `tabular` in `\footnotesize` text

**Example conversion:**
```latex
% BEFORE (wrong)
\begin{tabular}{|l|c|c|c|}
\hline
Method & Col1 & Col2 & Col3 \\
\hline
data   & 1.0  & 2.0  & 3.0  \\
data   & 4.0  & 5.0  & 6.0  \\
\hline
\end{tabular}

% AFTER (correct)
\begin{tabular}{lccc}
\toprule
Method & Col1 & Col2 & Col3 \\
\midrule
data   & 1.0  & 2.0  & 3.0  \\
data   & 4.0  & 5.0  & 6.0  \\
\bottomrule
\end{tabular}
```

### 4.9 Equation Line-Breaking

For any equation that will overflow the two-column width (~3.3 in), wrap in `split` environment with `&` alignment at `=` signs. For truly wide equations, use `widetext`.

Equation cleanup rules:
- Replace `$$...$$` with `equation`, `equation*`, or another appropriate LaTeX equation environment.
- Replace `eqnarray` with `equation` + `split`, `align`, or `widetext`.
- Break long equations after `=` and before major `+`, `-`, or summation terms.
- If an equation triggers an overfull `\hbox`, treat it as a required formatting fix.
- Put `\label{...}` inside the numbered equation environment, after the line that establishes the number.
- Do not rewrite equations that are short enough to fit on one line.

### 4.10 End Matter

Ensure `\label{lastpage}` is present just before `\end{document}`.

Ensure acknowledgments use `\begin{acknowledgments}...\end{acknowledgments}` (not `\section*{Acknowledgments}`).

---

## Step 5 — Fix References

Identify which situation applies and follow the corresponding workflow.

### Situation A — Has .bib File(s)

This is the preferred case. Use `cicc.bst` via BibTeX.

**Ensure the `.tex` ends with:**
```latex
\bibliographystyle{cicc}
\bibliography{filename}   % without .bib extension
\label{lastpage}
\end{document}
```

**Check the `.bib` entries for common problems:**

1. **Journal name** — journal names in final references must be abbreviated. If a `shortjournal` field exists, `cicc.bst` will prefer it over `journal`. The pipeline also normalizes common full journal names in the output `.bib` copy before BibTeX.

2. **Author name format in .bib** — BibTeX entry format should be `Surname, Firstname` or `Surname, F.` so that `cicc.bst`'s `{vv~}{ll} {f.}` pattern outputs `Surname F.` correctly:
   - ✓ `author = {Mo, Yirong and Shaik, Sason}`
   - ✗ `author = {Yirong Mo and Sason Shaik}` ← still works but less reliable for complex names

3. **DOI/URL/ISSN fields** — do not add missing DOI, URL, or ISSN fields for output formatting. Existing fields may remain in `.bib`, but `cicc.bst` suppresses them in the final `.bbl` and PDF.

4. **Compile and inspect `.bbl`** — after BibTeX run, open the generated `.bbl` file and spot-check 3–5 entries against the formatting rules. Fix `.bib` entries (not `.bbl`) if issues are found.

**Include in final zip:** `.tex`, `cicc.cls`, `cicc.bst`, `.bib` file(s), `figures/`

### Situation B — Inline thebibliography

The `.tex` contains `\begin{thebibliography}{N}...\end{thebibliography}`. Check and correct every `\bibitem` entry:

| Field | Rule | Example |
|---|---|---|
| Author names | Surname-first, no comma between surname and initials | `Mo Y.`, `Berger M.~J.` |
| Multiple authors | Comma-separated, last preceded by `and` | `Mo Y., Shaik S. and Hiberty P.` |
| Article title | Sentence case, plain text | `Is my chemical universe localized?` |
| Journal name | Italicized, abbreviated | `\textit{J. Chem. Phys.}` |
| Volume | Bold | `\textbf{31}` |
| Issue | In parentheses after volume | `\textbf{31}(2)` |
| Year | In parentheses after volume/issue | `\textbf{31} (2007)` |
| Pages | After comma, en-dash | `, 1981--2128.` |
| Book title | Italicized, Title Case | `\textit{The Nature of the Chemical Bond}` |
| Book editors | Surname-first, in parentheses | `(Eds.\ Frenking G. and Shaik S.)` |
| DOI/URL/ISSN | Not displayed | remove visible DOI, URL, and ISSN text from inline `thebibliography` output |

**Correct format examples:**

```latex
% Journal article
\bibitem{ref1}
Shaik S., Is my chemical universe localized or delocalized?,
\textit{New J. Chem.}, \textbf{31} (2007), 1981--2128.

% Book
\bibitem{ref2}
Pauling L., \textit{The Nature of the Chemical Bond},
Cornell University Press, Ithaca, 1960.

% Book chapter
\bibitem{ref3}
Mo Y., The block-localized wavefunction (BLW) perspective of chemical bonding,
In \textit{The Chemical Bond}, (Eds.\ Frenking G. and Shaik S.),
Wiley, 2014, pp.~199--232.
```

**Do NOT convert** inline `thebibliography` to `.bib` unless the user explicitly requests it.

### Situation C — Mixed (.bib + inline bibitem)

Consolidate everything into a single `.bib` file. Reconstruct any inline `\bibitem` entries as proper `.bib` entries. Then follow Situation A workflow.

---

## Step 6 — Package Output

```bash
cd /home/claude
zip -r MANUSCRIPT_ID.zip \
    MANUSCRIPT_ID.tex \
    cicc.cls \
    figures/
```

If Situation A (BibTeX): also include `cicc.bst` and the `.bib` file(s).

The zip must contain:
- `.tex` file
- `cicc.cls`
- `figures/` folder (PNG/JPEG/PDF only — no EMF)
- For BibTeX: `cicc.bst` + `.bib` file(s)

Copy to `/mnt/user-data/outputs/` and present to user.

---

## Reformatting Checklist

After producing the output `.tex`, verify every item:

**Preamble**
- [ ] `\documentclass{cicc}` (lowercase)
- [ ] No duplicate `\usepackage` for packages built into cicc.cls
- [ ] All metadata fields present with placeholders for any missing values
- [ ] Each author on separate `\author[N]{Name}` line
- [ ] All `\affil` use `\textit{...}`
- [ ] Last `\affil` before `\affil[*]` has `\protect\vspace{1em}`

**Document structure**
- [ ] `\twocolumn[{...}]` wraps maketitle + abstract + keywords
- [ ] `\keywords{...}` inside abstract environment
- [ ] `\thispagestyle{firstpage}` and `\label{firstpage}` present
- [ ] `\label{lastpage}` present before `\end{document}`

**Formatting rules**
- [ ] Title uses Title Case
- [ ] All section/subsection headings use sentence case
- [ ] Keywords: comma-separated, lowercase, ends with period
- [ ] All `\cite` before ALL punctuation (periods AND commas)
- [ ] No `Fig.` / `Tab.` — always `Figure` / `Table`
- [ ] Equation refs use `Eq.\ ` / `Eqs.\ `
- [ ] Wide equations use `split` or `widetext`
- [ ] No `$$...$$` and no `eqnarray`
- [ ] Equation overfull `\hbox` warnings have been fixed

**Floats**
- [ ] `figure*` / `scheme*` / `table*` use `[!t]`; never `[h]` or `[b]`
- [ ] `figure` / `scheme` / `table` (single-column) use `[h!]`
- [ ] Single-image wide floats: `width=0.9\textwidth`; multi-panel wide floats: per-panel widths such as `0.2--0.5\textwidth`; single-column: `width=1.0\linewidth`
- [ ] All floats have `\centering`
- [ ] Table `\caption` before `\begin{tabular}`
- [ ] Float `\label` appears immediately after `\caption`
- [ ] Figure/scheme: `\includegraphics` BEFORE `\caption` (image above caption — MANDATORY)
- [ ] Floats placed BEFORE the paragraph that first references them
- [ ] Wide floats use `figure*` / `scheme*` / `table*` (not `widefigure` / `widescheme` / `widetable`)
- [ ] All tables use three-line format: `\toprule` / `\midrule` / `\bottomrule` — no `\hline`
- [ ] Table column specs contain no vertical lines (`|`)
- [ ] Crowded tables use `table*`, shorter headings, or `p{...}` columns before whole-table scaling
- [ ] `booktabs` package loaded if not already in `cicc.cls`

**References**
- [ ] Situation identified (A / B / C) and correct workflow applied
- [ ] Author names Surname-first throughout
- [ ] Editor names Surname-first in book chapters
- [ ] Journal names italicized and abbreviated
- [ ] Volume numbers bold
- [ ] Page ranges use en-dash (`--`)
- [ ] Article titles in sentence case; book titles in Title Case

**Output**
- [ ] Final zip contains correct files for the situation
- [ ] No EMF files in zip
- [ ] No original source `.tex` renamed — output has clean manuscript ID filename
