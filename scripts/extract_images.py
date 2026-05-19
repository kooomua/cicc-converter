#!/usr/bin/env python3
"""Extract embedded images from a .docx file, converting EMF files to PDF via LibreOffice."""

import sys
import os
import shutil
import subprocess
import zipfile
from pathlib import Path


def extract_images(docx_path: Path, figures_dir: Path) -> list[dict]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    results = []

    with zipfile.ZipFile(docx_path, "r") as z:
        media_files = [f for f in z.namelist() if f.startswith("word/media/")]
        if not media_files:
            print("No embedded media found in document.")
            return results

        for member in media_files:
            filename = Path(member).name
            dest = figures_dir / filename
            with z.open(member) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            results.append({"filename": filename, "path": str(dest), "status": "extracted", "converted": None})

    return results


def convert_emf_files(results: list[dict], figures_dir: Path) -> None:
    emf_entries = [r for r in results if r["filename"].lower().endswith(".emf")]
    if not emf_entries:
        return

    if not shutil.which("soffice"):
        for r in emf_entries:
            r["converted"] = "skipped — LibreOffice not found"
        return

    for entry in emf_entries:
        src = Path(entry["path"])
        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(figures_dir),
                    str(src),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            pdf_path = figures_dir / (src.stem + ".pdf")
            if result.returncode == 0 and pdf_path.exists():
                entry["converted"] = f"ok → {pdf_path.name}"
            else:
                entry["converted"] = f"failed: {result.stderr.strip()[:120]}"
        except subprocess.TimeoutExpired:
            entry["converted"] = "failed: LibreOffice timed out"
        except Exception as exc:
            entry["converted"] = f"failed: {exc}"


def print_summary(results: list[dict]) -> bool:
    col_w = [36, 14, 30]
    header = f"{'Filename':<{col_w[0]}}  {'Status':<{col_w[1]}}  {'EMF Conversion'}"
    print()
    print(header)
    print("-" * (sum(col_w) + 4))

    any_error = False
    for r in results:
        conv = r["converted"] or "-"
        print(f"{r['filename']:<{col_w[0]}}  {r['status']:<{col_w[1]}}  {conv}")
        if r["converted"] and r["converted"].startswith("failed"):
            any_error = True

    print()
    total = len(results)
    emf_total = sum(1 for r in results if r["converted"] is not None)
    emf_ok = sum(1 for r in results if r["converted"] and r["converted"].startswith("ok"))
    print(f"Extracted: {total} file(s)  |  EMF conversions: {emf_ok}/{emf_total} succeeded")
    print()
    return any_error


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path/to/manuscript.docx>")
        return 1

    docx_path = Path(sys.argv[1]).resolve()
    if not docx_path.exists():
        print(f"Error: file not found: {docx_path}")
        return 1
    if docx_path.suffix.lower() != ".docx":
        print(f"Error: expected a .docx file, got: {docx_path.name}")
        return 1

    figures_dir = docx_path.parent / "figures"
    print(f"Source:  {docx_path}")
    print(f"Output:  {figures_dir}")

    try:
        results = extract_images(docx_path, figures_dir)
    except zipfile.BadZipFile:
        print("Error: file is not a valid .docx (bad zip).")
        return 1
    except Exception as exc:
        print(f"Error during extraction: {exc}")
        return 1

    if not results:
        return 0

    convert_emf_files(results, figures_dir)
    had_errors = print_summary(results)
    return 1 if had_errors else 0


if __name__ == "__main__":
    sys.exit(main())
