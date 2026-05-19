---
name: cicc-latex
description: |
  Convert Word documents (.docx) to LaTeX format following the CiCC (Communications in Computational Chemistry) journal template. Use this skill whenever the user wants to: convert a paper/manuscript from Word to LaTeX for CiCC journal submission, format a scientific paper using the cicc.cls class file, prepare a .tex file following CiCC formatting rules, or fix formatting issues in an existing CiCC LaTeX manuscript. Trigger on mentions of "CiCC", "cicc.cls", "cicc.bst", "Communications in Computational Chemistry", or any request to convert a chemistry/computational chemistry paper to LaTeX using a specific journal template.
---

# CiCC Journal LaTeX Conversion Workflow

This skill converts scientific manuscripts from Word (.docx) to LaTeX format following the CiCC journal template exactly. The workflow ensures all formatting rules, metadata structure, and style conventions are preserved.

## Overview of Steps

1. **Read the template files** (`CiCC_template.tex`, `cicc.cls`, `cicc.bst`) to understand the exact format
2. **Extract content** from the Word document using pandoc
3. **Extract images** from the docx (PNG/JPEG directly usable; EMF needs conversion to PDF)
4. **Write the .tex file** following the template structure precisely
5. **Apply CiCC formatting rules** (capitalization, citations, abbreviations, etc.)
6. **Verify** the output

## Template Structure (Preamble)

The preamble must follow this exact order and format. Do NOT add extra `\usepackage` commands — most packages (natbib, graphicx, amsmath, hyperref, etc.) are already loaded by `cicc.cls`.

```latex
\documentclass{cicc}

\articletype{Feature Article}

\doi{doi: 10.4208/cicc.2026.xxx.xx}
\publishedyear{2026}
\volume{xx}
\issue{xx}
\pagenumbers{xx - xx}

\receiveddate{...}
\revisiondate{dd/mm/yyyy}
\accepteddate{...}
\onlinedate{dd/mm/yyyy}
\publisheddate{dd/mm/yyyy}

\title[Short Title For Running Head]
{Full Title Here}
\author[1]{First Author}
\author[2,*]{Corresponding Author}

\affil[1]{\textit{Department, University, City, Country}}
\affil[2]{\textit{Department, University, City, Country}
\protect\vspace{1em}}

\affil[*]{Corresponding author: email@example.com}
```

Key points about the preamble:
- The output file must start exactly with `\documentclass{cicc}`.
- From `\documentclass{cicc}` through the end of the opening `\twocolumn[{...}]` abstract block, follow the fixed opening frame embedded in the Converter prompt.
- `\documentclass{cicc}` — lowercase "cicc", matching the cls filename
- Each author gets a separate `\author[affil_numbers]{Name}` command
- Affiliations use `\affil[number]{\textit{...}}` with italic text
- The last affiliation before `\affil[*]` gets `\protect\vspace{1em}`
- All metadata fields (receiveddate, revisiondate, accepteddate, onlinedate, publisheddate) must be present
- `\title`, `\author`, and `\affil` must stay before `\begin{document}`.
- Do not copy an author's source preamble wholesale.
- Keep only author packages that the converted body truly needs.
- Do not reload packages already supplied by `cicc.cls`, including `geometry`, `fontenc`, `inputenc`, `newtxtext`, `newtxmath`, `microtype`, `graphicx`, `xcolor`, `etoolbox`, `amsmath`, `calc`, `xstring`, `authblk`, `cuted`, `abstract`, `fancyhdr`, `caption`, and `natbib`.
- Do not load `amsthm`; use basic `\newtheorem` if theorem-like environments are needed.
- When evaluator feedback reports a compile conflict from a package or command, remove or replace that conflicting package or command in the next attempt.

## Document Opening Block

The title, abstract, and keywords must be wrapped in a `\twocolumn[{...}]` block:

```latex
\begin{document}

\twocolumn[{
  \vspace*{0.5em}
  \maketitle
  \thispagestyle{firstpage}
  \label{firstpage}

\begin{abstract}
Abstract text here.

\keywords{keyword1; keyword2; keyword3.}
\end{abstract}

}] % End of twocolumn header block

\section{Introduction}
```

Critical: `\keywords{...}` goes INSIDE the abstract environment, and the entire block is inside `\twocolumn[{...}]`.
Also critical: `\maketitle`, `\thispagestyle{firstpage}`, and `\label{firstpage}` go inside the same `\twocolumn[{...}]` block. The manuscript body begins after that block, normally at the first `\section{...}`.

## Formatting Rules

### 1. Title Capitalization
Capitalize all major words in the title, including words after hyphens. Keep minor words (in, and, of, the, a, an, for, to, with, on, at, by, from, etc.) lowercase unless they are the first word.

**Example:** "Block-Localized Wavefunction (BLW) Method and Its Applications in Intramolecular and Intermolecular Interactions"

### 2. Section Heading Capitalization (Sentence Case)
Only the first word is capitalized, plus proper nouns and established abbreviations.
Do not use Title Case or ALL CAPS for section, subsection, or subsubsection headings. The evaluator reports obvious violations as `section-heading-case`; fix every reported heading.

**Correct:**
- `\section{Theoretical method}`
- `\subsection{Energy decomposition (BLW-ED) scheme}`
- `\section{Results and discussion}`
- `\section{Computational methods}`

**Wrong:**
- `\section{Theoretical Method}`  ← "Method" should not be capitalized
- `\section{Results and Discussion}` ← "Discussion" should not be capitalized
- `\section{Computational Methods}` ← "Methods" should not be capitalized
- `\section{COMPUTATIONAL METHODS}` ← all caps is wrong

### 3. Keywords Formatting
Keywords use **commas** as separators and are entirely lowercase, except for proper nouns (e.g., Diels-Alder) and abbreviations (e.g., VB, BLW, DFT). The `\keywords{...}` command in cicc.cls automatically outputs "Key words:" with a colon.

**Correct:**
- `\keywords{valence bond (VB) theory, block-localized wavefunction (BLW), electron transfer, anomeric effect, noncovalent interaction.}`

**Wrong:**
- `\keywords{valence bond (VB) theory; block-localized wavefunction (BLW); electron transfer}` ← semicolons should be commas
- `\keywords{Valence bond (VB) theory, Block-localized wavefunction (BLW), Electron transfer}` ← first letters should not be capitalized
- `\keywords{Valence Bond (VB) Theory, Block-Localized Wavefunction (BLW), Electron Transfer}` ← Title Case is wrong for keywords

### 4. Citations Before ALL Punctuation (Periods AND Commas)
`\cite{...}` must always appear BEFORE any punctuation mark (period, comma, semicolon). The punctuation follows after the closing brace. This applies to both end-of-sentence periods AND mid-sentence commas.

**Correct (before period):**
- `...proposed by Lewis over 100 years ago\cite{ref1, ref2}.`
- `...in the resonance theory\cite{ref3, ref4}.`

**Correct (before comma):**
- `...bridge MO computation results with VB concepts\cite{ref7}, with the development...`
- `...localization schemes of canonical MOs\cite{ref8,ref9,ref10}, atoms in molecule...`
- `...symmetry-adapted perturbation theory (SAPT)\cite{ref38}, EDA-NOCV\cite{ref17, ref18}, and...`

**Wrong:**
- `...proposed by Lewis over 100 years ago.\cite{ref1, ref2}` ← period before cite
- `...VB concepts,\cite{ref7} with...` ← comma before cite

### 5. Figure/Table/Scheme References — Always Full Words
Never use abbreviations like "Fig." or "Tab." in any context (captions or body text). Always use the full word.

**Correct:**
- `Figure~\ref{fig1} shows the major results.`
- `Table~\ref{tab1} summarizes the computational results.`

**Wrong:**
- `Fig.~\ref{fig1}` ← must be "Figure"

### 6. Equation References — Use "Eq." and "Eqs."
In running text, refer to equations as `Eq.\ N` or `Eqs.\ N and M`.

**Correct:**
- `...the bond function (Eq.\ 2) is formally reduced to...`
- `...the hybrid usage of Eqs.\ 2 and 3 in $\Psi_{R}$...`

### 7. Long Equation Line-Breaking
Since the document uses two-column layout (~3.3 inches per column), equations must be broken aggressively and early to fit within a single column. **Err on the side of breaking sooner** — prefer more line breaks over fewer. Use `split` inside `equation` for multi-line equations with `&` alignment at `=` signs:

**Strategy:** Break after each `=` sign, and limit each line to 2-3 terms maximum. For sums of many terms, put only 2 terms per line.

Hard equation rules:
- Do not use `$$...$$` display math.
- Do not use `eqnarray`; replace it with `equation` + `split`, `align`, or `widetext`.
- If an equation creates an overfull `\hbox`, rewrite the equation before approval.
- Place `\label{...}` inside the numbered equation environment, after the line that establishes the equation number.
- Use `widetext` only after aggressive line breaking still cannot produce a readable one-column equation.

```latex
\begin{equation}
\begin{split}
F_{b} &= \frac{d\Delta E_{b}}{dR} \\
&= \frac{d\Delta E_{\text{def}}}{dR} + \frac{d\Delta E_{F}}{dR} \\
&\quad + \frac{d\Delta E_{\text{pol}}}{dR} + \frac{d\Delta E_{\text{CT}}}{dR} \\
&\quad + \frac{d\Delta E_{\text{disp}}}{dR} \\
&= F_{\text{def}} + F_{F} + F_{\text{pol}} \\
&\quad + F_{\text{CT}} + F_{\text{disp}}
\end{split}
\end{equation}
```

For equations that cannot fit in a single column even with aggressive line breaks, use the `widetext` environment (defined in `cicc.cls` using the `cuted` package) to span both columns:

```latex
\begin{widetext}
\begin{equation}
... very long equation ...
\end{equation}
\end{widetext}
```

Alternatively, `align` can be used for multi-line aligned equations without the `equation` wrapper.

### 8. Figure and Scheme Environment Format

**Default choice: use `figure*` (two-column spanning) for most figures.** The CiCC two-column layout is narrow (~3.3 in per column), so most figures — including any multi-panel figure, any figure with text labels, any figure wider than it is tall, and any figure containing structural formulas or data plots — should span both columns. Only use single-column `figure` for genuinely small, simple images (e.g., a single compact molecular structure, a small icon, or a figure explicitly narrow enough to read at column width).

**Placement specifiers:**
- `figure*` / `scheme*`: use `[!t]` (top of page, `!` relaxes restrictions). `figure*` does **not** support `[h]` or `[b]`.
- `figure` / `scheme`: use `[h!]` (here, relaxed). Fall back to `[!htbp]` only if `[h!]` causes layout problems.
- Do not use `widefigure` or `widescheme`; use `figure*` or `scheme*` directly.

**MANDATORY ORDER inside every figure/scheme float — NO EXCEPTIONS:**
```
\centering
\includegraphics  ← ALWAYS FIRST (image above caption)
\caption          ← ALWAYS SECOND (caption below image)
\label
```
`\caption` must NEVER appear before `\includegraphics` in a figure or scheme environment. This order is fixed and non-negotiable.

**Wide figure (default for most single-image figures):**
```latex
\begin{figure*}[!t]
  \centering
  \includegraphics[width=0.9\textwidth]{figurefile}
  \caption{Caption text here.}
  \label{fig1}
\end{figure*}
```

**Wide multi-panel figure:**
Use `figure*`, but size each panel so the combined width fits within the full text width. Typical per-panel widths are `0.2--0.5\textwidth`; do not force every subimage to `0.9\textwidth`.

```latex
\begin{figure*}[!t]
  \centering
  \subfloat[]{\includegraphics[width=0.48\textwidth]{panel-a}}\hfill
  \subfloat[]{\includegraphics[width=0.48\textwidth]{panel-b}}
  \caption{Caption text here.}
  \label{fig:multi}
\end{figure*}
```

**Single-column figure (only for small/compact images):**
```latex
\begin{figure}[h!]
  \centering
  \includegraphics[width=1.0\linewidth]{figurefile}
  \caption{Caption text here.}
  \label{fig2}
\end{figure}
```

**Wide scheme (default for most schemes):**
```latex
\begin{scheme*}[!t]
  \centering
  \includegraphics[width=0.9\textwidth]{schemefile}
  \caption{Scheme caption here.}
  \label{scheme1}
\end{scheme*}
```

**Single-column scheme (compact only):**
```latex
\begin{scheme}[h!]
  \centering
  \includegraphics[width=1.0\linewidth]{schemefile}
  \caption{Scheme caption here.}
  \label{scheme2}
\end{scheme}
```

Note: `widescheme` / `widefigure` are aliases in `cicc.cls` for `scheme*` / `figure*`. Prefer the starred forms directly.

**Figure/Scheme Placement Rule:** Place the float environment in the LaTeX source BEFORE the paragraph that first references it. Do NOT pile all figures at the end.

### 9. Table Environment Format

**CiCC tables must be three-line tables (三线表).** Use the `booktabs` package. If `booktabs` is not already loaded by `cicc.cls`, add `\usepackage{booktabs}` to the preamble.

**Three-line table rules:**
- Use `\toprule` / `\midrule` / `\bottomrule` — **never `\hline`**
- Column format must contain **no vertical lines** (`|`) — only `l`, `c`, `r`, `p{...}`
- No extra horizontal rules between data rows; use `\cmidrule{a-b}` only for multi-level headers
- `\caption` comes **before** `\begin{tabular}`
- `\centering` comes before `\caption`
- `\label` comes immediately after `\caption`
- Do not use `widetable`; use `table*` directly.
- Use `table*` for tables with more than four numeric/text columns, long headings, multi-level headers, or any content likely to overflow a single column.
- Avoid `\resizebox` as the first solution for crowded tables. Prefer `table*`, shorter headings, `p{...}` columns, or reduced tabular content before scaling the whole table.
- Table notes go below the `tabular` in `\footnotesize` text.

**Placement specifiers** follow the same rules as figure/scheme:
- `table*` (two-column wide): use `[!t]`
- `table` (single-column): use `[h!]`

**Single-column table (default for most tables):**
```latex
\begin{table}[h!]
\centering
\caption{Caption text here.}
\label{tab1}
\begin{tabular}{lcccc}
\toprule
Header1 & Header2 & Header3 & Header4 & Header5 \\
\midrule
data    & data    & data    & data    & data    \\
data    & data    & data    & data    & data    \\
\bottomrule
\end{tabular}
\end{table}
```

**Wide (two-column) table — use `table*` (NOT `widetable`):**
```latex
\begin{table*}[!t]
\centering
\caption{Caption text here.}
\label{tab2}
\begin{tabular}{llcccccc}
\toprule
Header1 & Header2 & Header3 & Header4 & Header5 & Header6 & Header7 & Header8 \\
\midrule
data    & data    & data    & data    & data    & data    & data    & data    \\
data    & data    & data    & data    & data    & data    & data    & data    \\
\bottomrule
\end{tabular}
\end{table*}
```

**Multi-level header (use `\cmidrule` instead of `\hline`):**
```latex
\begin{tabular}{lcccc}
\toprule
 & \multicolumn{2}{c}{Group A} & \multicolumn{2}{c}{Group B} \\
\cmidrule(lr){2-3} \cmidrule(lr){4-5}
Method & Col1 & Col2 & Col3 & Col4 \\
\midrule
data   & data & data & data & data \\
\bottomrule
\end{tabular}
```

Note: `widetable` is an alias in `cicc.cls` for `table*`. Use `table*` directly for clarity and portability.

### 10. Acknowledgments and End Matter

```latex
\begin{acknowledgments}
Acknowledgment text here.
\end{acknowledgments}

\begin{Supporting_Information}
...
\end{Supporting_Information}

\begin{Notes}
The authors declare no competing financial interest.
\end{Notes}

\bibliographystyle{cicc}
\bibliography{ref}
\label{lastpage}
\end{document}
```

If using `thebibliography` instead of BibTeX, replace the `\bibliographystyle`/`\bibliography` lines with the `\begin{thebibliography}{N}...\end{thebibliography}` block.

## Missing Information — Placeholders Only

**Never invent or guess missing content.** When any required field is absent from the Word source, output a clearly visible placeholder and do nothing else. This applies to:

| Missing item | Placeholder to use |
|---|---|
| Dates (received, accepted, etc.) | `dd/mm/yyyy` |
| DOI | `doi: 10.4208/cicc.2026.xxx.xx` |
| Volume / Issue / Pages | `xx` |
| Article type | `\articletype{PLACEHOLDER}` |
| Keywords not found | `\keywords{PLACEHOLDER}` |
| Abstract not found | `PLACEHOLDER` inside `\begin{abstract}` |
| Author affiliation unclear | `\affil[N]{\textit{PLACEHOLDER}}` |
| Figure caption missing | `\caption{PLACEHOLDER}` |
| Acknowledgments missing | omit the environment entirely |

Do NOT fabricate plausible-looking metadata, infer dates from context, or fill in partial citations. A placeholder is always preferable to invented content.

## Bibliography Formatting

Use `\bibliographystyle{cicc}` and `\bibliography{ref}` with BibTeX when possible. When using `\begin{thebibliography}` manually, follow these formats strictly:

**General rules:**
- Author format: **Surname first, then initials** (姓在前). No comma between surname and initials. Initials separated by periods, multiple initials tied with `~`. Example: `Berger M.~J.`, `Mo Y.`, `Smith A.~B.~C.`
- This matches `cicc.bst`'s `format.names` function pattern `{vv~}{ll} {f.}` — e.g. BibTeX entry `Mo, Yirong` outputs `Mo Y.`
- Multiple authors separated by commas; last author preceded by "and" (no Oxford comma for two authors).
- Fields separated by commas. Each entry ends with a period.

**Comma usage between fields:**
- The pattern is: Author(s), Title, *Journal/Book*, Volume/Edition info, (Year), Pages.
- The comma comes **after** the closing parenthesis of the year: `\textbf{31} (2007), 1981--2128`
- Page ranges for book chapters are prefixed with `pp.~` and preceded by a comma: `2014, pp.~199--232`
- The final field (pages or year) ends with a **period**, not a comma.

**Title capitalization rules:**

*Journal article titles* — **sentence case**: capitalize only the first word and proper nouns/established abbreviations; all other words are lowercase.
- ✓ `Is my chemical universe localized or delocalized?`
- ✓ `Local adaptive mesh refinement for shock hydrodynamics`
- ✗ `Local Adaptive Mesh Refinement for Shock Hydrodynamics` ← Title Case is wrong for article titles

*Book titles, thesis titles, program/manual titles* — **Title Case**: capitalize all words except minor words (in, and, of, the, a, an, for, to, with, on, at, by, from) unless they are the first word.
- ✓ `\textit{The Nature of the Chemical Bond}`
- ✓ `\textit{The Chemical Bond}`
- ✗ `\textit{The nature of the chemical bond}` ← sentence case is wrong for book titles

**Journal articles:** Authors, Title, \textit{Journal}, \textbf{Volume}(Issue) (Year), Pages.
- Title in plain text, sentence case. Journal name italicized and abbreviated. Volume bold. Issue in parentheses immediately after volume if present.
- Final rendered journal-article references must not display DOI, URL, or ISSN. Existing `doi`, `url`, and `issn` fields may remain in `.bib`, but `cicc.bst` suppresses them in `.bbl`/PDF output.
- Example: `Shaik S., Is my chemical universe localized or delocalized?, \textit{New J. Chem.}, \textbf{31} (2007), 1981--2128.`

**Standalone books:** Authors, \textit{Book Title}, Publisher, Address, Year.
- Book title italicized, Title Case. Publisher, address, year separated by commas.
- Example: `Pauling L., \textit{The Nature of the Chemical Bond}, Cornell University Press, Ithaca, 1960.`

**Book chapters:** Authors, Chapter title, In \textit{Book Title}, Vol.~\textbf{Volume}, (Eds.\ Editor Names), Publisher, Address, Year, pp.~Pages.
- Chapter title in plain text, sentence case. Book title preceded by "In", italicized, Title Case.
- Editors in parentheses: `(Eds.\ ...)` or `(Ed.\ ...)`. Editor names also follow Surname-first format.
- Example: `Mo Y., The block-localized wavefunction (BLW) perspective of chemical bonding, In \textit{The Chemical Bond}, (Eds.\ Frenking G. and Shaik S.), Wiley, 2014, pp.~199--232.`

**Preprints/Misc:** Authors, Title (sentence case), Year. Do not display DOI or URL in the final reference list.

**Programs/Manuals:** Authors, \textit{Program Title} (Title Case), Organization, Address, Year.

**Theses:** Authors, \textit{Thesis Title} (Title Case), School, Address, Year.

## Image Handling

Image mapping must be done in **two phases**: a code phase to establish order, then an LLM visual proof phase to confirm correctness. Never assign `\includegraphics` filenames based on filename number alone.

### Phase 1 — Code: Establish Document Order

Parse `document.xml` to get the exact sequence in which images appear in the document body. Each image reference in Word XML looks like `<a:blip r:embed="rIdXX"/>`, and the relationship file (`word/_rels/document.xml.rels`) maps each `rId` to an actual media filename.

Run this to produce an ordered mapping:

```python
import zipfile, xml.etree.ElementTree as ET

docx_path = "manuscript.docx"
with zipfile.ZipFile(docx_path) as z:
    rels_xml = z.read("word/_rels/document.xml.rels")
    doc_xml  = z.read("word/document.xml")

# Build rId → filename map
rels_root = ET.fromstring(rels_xml)
rid_to_file = {}
for r in rels_root:
    rid  = r.attrib.get("Id", "")
    tgt  = r.attrib.get("Target", "")
    if "media/" in tgt:
        rid_to_file[rid] = tgt.split("media/")[-1]

# Walk document body in order
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
doc_root = ET.fromstring(doc_xml)
order = []
for blip in doc_root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
    rid = blip.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed", "")
    if rid in rid_to_file:
        fname = rid_to_file[rid]
        if fname not in order:   # deduplicate repeated embeds of same image
            order.append(fname)

for i, f in enumerate(order, 1):
    print(f"Position {i}: {f}")
```

This gives a reliable list like:
```
Position 1: image1.png   ← Scheme 1 (flowchart)
Position 2: image2.png   ← Figure 1a
Position 3: image3.png   ← Figure 1b
Position 4: image4.png   ← Figure 2
...
```

Cross-reference this list against the figure/scheme/table captions extracted from the plain text to produce a **draft mapping table** before writing any LaTeX.

### Phase 2 — LLM Visual Proof: Confirm by Content

After Phase 1 produces the draft mapping, visually inspect each image using the `view` tool and compare what you see against the caption assigned to it.

For each image:
1. View the image file
2. Describe what it shows (e.g., "a branching decision tree with 4 levels")
3. Compare against the caption (e.g., "Figure 4: Tiebreaking tree for stereocenters")
4. Mark as **✓ confirmed** or **✗ mismatch**

If Phase 1 and Phase 2 agree → proceed confidently.
If they disagree → flag the conflict explicitly in a comment in the `.tex` file and do NOT guess:

```latex
%% WARNING: image5.png assigned to Figure 3 by document order, but visually
%% appears to show a timing chart (expected: stereochemistry diagram).
%% Please verify manually before compiling.
```

### EMF Conversion

EMF files cannot be compiled in LaTeX and **must be converted to PDF** before use. LibreOffice is available in the environment — use it to convert all EMF files automatically:

```bash
# Convert all EMF files in the figures/ folder to PDF
for emf in figures/*.emf; do
    base="${emf%.emf}"
    libreoffice --headless --convert-to pdf "$emf" --outdir figures/ 2>/dev/null
    echo "Converted: $emf → ${base}.pdf"
done
```

After conversion, use the `.pdf` filename in `\includegraphics`. Do NOT leave EMF placeholders in the final `.tex` — always convert.

### Images Inside Tables

When images appear inside table cells in the Word document, the Phase 1 XML scan will still find them in document order — they are not skipped. However, they require special handling in LaTeX:

- These are typically **inline structure images** (e.g., chemical structure drawings in a data column)
- Do NOT wrap them in a `figure` or `scheme` float — they belong inside the `tabular` cell directly
- Use `\includegraphics[width=...]` inline within the table cell:

```latex
\begin{tabular}{cc}
\hline
Case & Structure \\
\hline
(g) & \includegraphics[width=2.5cm]{figures/image13.png} \\
(h) & \includegraphics[width=2.5cm]{figures/image14.png} \\
\hline
\end{tabular}
```

- During Phase 2 visual inspection, identify which images are table-cell images vs standalone figures — they are usually small, show a single molecule/structure, and appear in a numbered sequence corresponding to table rows
- The table caption goes above the tabular (`\caption` before `\begin{tabular}`) as per CiCC style

### Other image rules

- PNG files can be used directly in LaTeX
- JPEG files can be used directly
- PDF files (converted from EMF) can be used directly
- Save all extracted images to a `figures/` subfolder
- Always use the filename confirmed by Phase 2 in `\includegraphics{figures/filename}`

## Final Output: Packaging

After the `.tex` file is complete and verified, package all required files into a single zip for the author:

```bash
cd /mnt/user-data/outputs
zip -r MANUSCRIPT_ID.zip \
    MANUSCRIPT_ID.tex \
    cicc.cls \
    figures/
```

The zip must contain:
- The `.tex` file
- `cicc.cls` (the class file)
- `figures/` folder with all images (PNG/JPEG/PDF — no EMF)

Do NOT include: `cicc.bst` unless the paper uses BibTeX `.bib` file (in which case include the `.bib` too). Do NOT include the original `.docx`.

## Conversion Checklist

After writing the .tex file, verify:
- [ ] `\documentclass{cicc}` (lowercase)
- [ ] All metadata fields present (articletype, doi, publishedyear, volume, issue, pagenumbers/dates)
- [ ] `\twocolumn[{...}]` block wraps maketitle + abstract + keywords
- [ ] `\keywords{...}` inside abstract environment
- [ ] `\thispagestyle{firstpage}` inside twocolumn block
- [ ] Title uses Title Case (all major words capitalized)
- [ ] Section headings use sentence case
- [ ] Keywords are all lowercase (except proper nouns/abbreviations), comma-separated
- [ ] All `\cite` placed before ALL punctuation (periods AND commas)
- [ ] No "Fig." — always "Figure"; no "Tab." — always "Table"
- [ ] Equation refs use "Eq." / "Eqs."
- [ ] Long equations use `split` or `widetext` for two-column layout
- [ ] No `$$...$$` and no `eqnarray`; equation overfull warnings have been fixed
- [ ] Most figures use `figure*[!t]` (default); single-column `figure[h!]` only for small/compact images
- [ ] `figure*` / `scheme*` use `[!t]` (never `[h]` or `[b]`); `figure` / `scheme` use `[h!]`
- [ ] Single-image wide figures use `width=0.9\textwidth`; multi-panel wide figures use per-panel relative widths such as `0.2--0.5\textwidth`; single-column figures use `width=1.0\linewidth`
- [ ] No missing metadata — all absent fields have visible placeholders (never invented values)
- [ ] Tables use `\centering` before `\caption`
- [ ] Table `\label` appears immediately after `\caption`
- [ ] All tables use three-line format: `\toprule` / `\midrule` / `\bottomrule` — no `\hline`
- [ ] Table column specs contain no vertical lines (`|`)
- [ ] `table` uses `[h!]`; `table*` uses `[!t]` — not `[!htbp]` or `[h]`
- [ ] Wide floats use `figure*` / `table*` (not `widefigure` / `widetable`)
- [ ] `booktabs` package loaded if not already in `cicc.cls`
- [ ] Figures/Schemes placed in source BEFORE the paragraph that first references them
- [ ] Image mapping: Phase 1 (XML document order) completed before assigning any filenames
- [ ] Image mapping: Phase 2 (LLM visual inspection) confirmed each image matches its caption
- [ ] Any unresolved image conflicts flagged with `%% WARNING:` comments in the .tex
- [ ] All EMF files converted to PDF using LibreOffice (no EMF in final zip)
- [ ] Images inside table cells placed inline in `tabular` (not wrapped in `figure` float)
- [ ] All bibliography entries present and correctly formatted
- [ ] `\label{firstpage}` and `\label{lastpage}` present
- [ ] Final zip contains: `.tex`, `cicc.cls`, `figures/` (PNG/JPEG/PDF only)
- [ ] In every figure/scheme: `\includegraphics` comes BEFORE `\caption` (image above caption)
