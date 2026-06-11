Purpose: inspect the uploaded source and the current converted TeX draft before any focused conversion pass changes it.

Checks:
- Identify source type: docx or tex.
- Count source figures, tables, citations, and references when possible.
- For docx inputs, check whether Pandoc Markdown contains a numbered References section.
- Check whether the converted TeX already has bibliography data: `.bib`, `.bbl`, or `thebibliography`.
- Record risks that later passes must resolve.

Output:
- PASS when the source can be inspected and no blocking condition is found.
- WARNING when important source material exists but is missing from the draft.
- FAIL only when the source or draft cannot be read.
