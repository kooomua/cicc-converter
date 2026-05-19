# CiCC Formatting Rules Reference

Shared reference for the Converter and Evaluator agents. All rules below reflect CiCC (Communications in Computational Chemistry) journal requirements.

---

## Document Class and Preamble

- The output file must start exactly with `\documentclass{cicc}`.
- From `\documentclass{cicc}` through the end of the opening `\twocolumn[{...}]` abstract block, follow the fixed opening frame embedded in the Converter prompt as the authoritative frame.
- `\title`, all `\author`, and all `\affil` commands must appear before `\begin{document}`.
- `\maketitle`, `\thispagestyle{firstpage}`, `\label{firstpage}`, `abstract`, and `\keywords{...}` must appear inside the opening `\twocolumn[{...}]` block.
- The manuscript body starts after the opening abstract block, normally with the first `\section{...}`.
- Do not copy the author's preamble wholesale.
- Keep only author packages that are actually required by the converted body.
- Do not add packages already loaded by `cicc.cls`; check the class file first.
- Do not reload common `cicc.cls` packages such as `geometry`, `fontenc`, `inputenc`, `newtxtext`, `newtxmath`, `microtype`, `graphicx`, `xcolor`, `etoolbox`, `amsmath`, `calc`, `xstring`, `authblk`, `cuted`, `abstract`, `fancyhdr`, `caption`, or `natbib`.
- Do not load `amsthm`; if theorem-like environments are needed, use basic `\newtheorem` definitions.
- If evaluator feedback reports a package or command conflict, the next conversion attempt must remove or replace the conflicting package or command.
- Bibliography style: `\bibliographystyle{cicc}`
- The preamble should be minimal; avoid redefining class internals

---

## Title and Headings

- **Paper title:** Title Case — capitalize all major words; lowercase articles, prepositions, and conjunctions unless first word
- **Section headings (`\section`):** Sentence case — capitalize first word and proper nouns only
- **Subsection headings (`\subsection`, `\subsubsection`):** Sentence case
- Do not use Title Case or ALL CAPS for section/subsection headings. The evaluator reports this as `section-heading-case`.
- Correct: `\section{Computational methods}`. Wrong: `\section{Computational Methods}`.

---

## Keywords

- All lowercase, except proper nouns and standard abbreviations (e.g., DFT, NMR)
- Comma-separated list
- **Must end with a period**
- Example: `density functional theory, basis set, reaction energy.`

---

## Citations

- Citations must appear **before** all punctuation — both periods and commas
- Correct: `...as shown in previous work\cite{Smith2020}.`
- Correct: `...as noted by Jones\cite{Jones2019}, the method...`
- Wrong: `...as shown in previous work.\cite{Smith2020}`
- Wrong: `...as noted by Jones,\cite{Jones2019} the method...`

---

## Cross-References: Figures, Tables, Equations

- Always **"Figure"**, never "Fig." or "fig."
- Always **"Table"**, never "Tab." or "table" (when used as a label reference)
- Equation references in running text: **"Eq."** (singular) and **"Eqs."** (plural)
- Example: `as given by Eq. (3)` / `combining Eqs. (4) and (5)`

---

## Figure Placement and Floats

- Default to full-width floats in the two-column layout when readability is uncertain.
- Full-width figures/schemes: `\begin{figure*}[!t]` / `\begin{scheme*}[!t]`
- Single-column figures/schemes only for compact images that remain readable at column width: `\begin{figure}[h!]` / `\begin{scheme}[h!]`
- Use `figure*` for multi-panel figures, figures with text labels, structural schemes, plots with axes/legends, and any image wider than it is tall.
- Do not use `widefigure`, `widescheme`, or `widetable`; use the starred environments directly.
- Figure/scheme body order is fixed: `\centering`, `\includegraphics`, `\caption`, `\label`.
- Inside every figure/scheme float: `\includegraphics` must come **before** `\caption` — no exceptions.
- Recommended graphics widths: `width=0.9\textwidth` for single-image `figure*`/`scheme*`; `width=1.0\linewidth` for single-image `figure`/`scheme`.
- For multi-panel `figure*`/`scheme*` blocks using multiple `\includegraphics`, `\subfloat`, or subfigure markup, use relative per-panel widths such as `0.2--0.5\textwidth` so the combined panels fit within the full text width. Do not force each subimage to `0.9\textwidth`.
- Place each figure/scheme environment in the source before the paragraph that first references it; do not collect all floats at the end.

---

## Table Format

- Full-width tables: `\begin{table*}[!t]`
- Single-column tables only for short, narrow tables: `\begin{table}[h!]`
- Use `table*` when a table has more than four numeric/text columns, long headings, multi-level headers, or any content likely to overflow a column.
- Use `booktabs` three-line style: `\toprule` / `\midrule` / `\bottomrule`
- **No vertical lines** in any table
- Do not use repeated interior horizontal rules; use `\cmidrule(lr){a-b}` only for grouped headers.
- Caption goes **above** the table: `\caption{...}` before `\begin{tabular}`
- Use `\label` immediately after `\caption`
- Avoid `\resizebox` as the first fix for a crowded table. Prefer `table*`, shorter headings, `p{...}` columns, or smaller tabular content before scaling the whole table.
- Table notes go below the `tabular` in `\footnotesize` text; they do not replace the caption.

---

## Equations

- Two-column layout requires aggressive line-breaking for wide equations
- Use LaTeX equation environments; do not use `$$...$$`.
- Do not use `eqnarray`; use `equation` + `split`, `align`, `aligned`, or `widetext`.
- Prefer the `split` environment inside `equation` for multi-line numbered equations:
  ```latex
  \begin{equation}
  \begin{split}
    E &= \alpha + \beta \\
      &\quad + \gamma
  \end{split}
  \end{equation}
  ```
- Break long equations after `=` and before major `+`, `-`, or summation terms. Keep each source line short enough to fit one column after typesetting.
- Use `\quad` or `\qquad` only for alignment/continuation indentation, not for manual page layout hacks.
- Use `widetext` only when a formula remains unreadable after aggressive splitting.
- `\label{...}` for an equation goes inside the numbered equation environment, after the line that establishes the number.
- Number all displayed equations unless they are purely definitional intermediates
- Treat any overfull `\hbox` warning from an equation as a formatting issue that should be fixed before approval.

---

## Bibliography

- Author format: **Surname I.** (last name first, initials only — no full first names)
- Multiple authors separated by commas; last two authors separated by "and"
- Journal article titles: **Sentence case** (capitalize first word and proper nouns only)
- Journal names must be abbreviated. Prefer `shortjournal` when present; otherwise normalize common full journal names in the output `.bib` copy before BibTeX.
- Final rendered references must not display DOI, URL, or ISSN. Source `.bib` files may retain `doi`, `url`, and `issn` fields, but `cicc.bst` suppresses them in `.bbl`/PDF output.
- Example entry:
  ```
  Smith A., Jones B. and Brown C., A study of reaction energetics, J. Comput. Chem. 42, 100–110 (2021).
  ```

---

## General Typography

- Use `--` (en dash) for number ranges, not `-`
- Use `\%` for literal percent signs in text
- Spell out numbers one through nine in running text; use numerals for 10 and above
- Chemical formulas: use `\ce{}` from the `mhchem` package when available
- Units: use a thin space `\,` between value and unit: `3.14\,eV`
