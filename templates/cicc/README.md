# CiCC Journal Template Files

This folder contains the official CiCC (Communications in Computational Chemistry) journal template files:

- **`cicc.cls`** — LaTeX document class
- **`cicc.bst`** — BibTeX bibliography style

## Usage by the Converter Agent

These are the authoritative versions used by the Converter agent. When preparing output, the Converter must copy `cicc.cls` and `cicc.bst` from this folder into `output/MANUSCRIPT_ID/` — they override any `.cls` or `.bst` files supplied by the authors in their submission package.

If an author's input folder contains their own copies of these files, ignore them for output purposes. Always use the versions here.

## Updating the Template

If the journal issues a new version of `cicc.cls` or `cicc.bst`, replace the files in this folder. Do not modify them to accommodate individual manuscripts — formatting fixes belong in the manuscript `.tex` file.
