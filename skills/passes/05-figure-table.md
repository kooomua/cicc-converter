Purpose: validate and repair figures and tables.

Scope:
- `figure`, `figure*`, `scheme`, `table`, and `table*`
- captions and labels
- graphics paths
- table packages required by local table syntax

Rules:
- Do not edit reference entries or body prose except figure/table callouts.
- Figure files referenced by `\includegraphics` must exist in output.
- Table captions go above tables.
- Figure captions go below graphics.
- If `\toprule`, `\midrule`, `\bottomrule`, `\cmidrule`, or `\addlinespace` are used, `booktabs` support must exist.
- If `\multirow` is used, `multirow` support must exist.

Output:
- PASS when figure/table source and packages are usable.
- WARNING for possible width/layout risks.
- FAIL for missing graphics or broken table syntax.
