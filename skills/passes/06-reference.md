Purpose: validate and repair references independently from the main converter.

Scope:
- citation keys in body
- `ref.bib`
- `thebibliography`
- `\bibliographystyle`
- `\bibliography`

Rules:
- Do not edit body prose except citation syntax if required.
- If TeX uses `\bibliography{ref}`, a usable `ref.bib` or generated `.bbl` must exist.
- For docx inputs with a numbered References section, convert each numbered reference into `\bibitem{refN}` when no `.bib` exists.
- The final PDF should not visibly include DOI, URL, or ISSN fields.
- Journal names should be abbreviated when reliable, but preserving a visible reference list is more important than perfect abbreviation.
- Undefined citations are not acceptable when source references are available.

Output:
- PASS when citations resolve to bibliography entries.
- WARNING when source references cannot be found.
- FAIL when citations exist but no bibliography data exists.
