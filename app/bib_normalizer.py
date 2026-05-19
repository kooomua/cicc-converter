from __future__ import annotations

import re
from pathlib import Path


FIELD_RE = re.compile(
    r"(?P<prefix>\b(?P<name>journal|shortjournal)\s*=\s*)"
    r"(?P<open>[{\"])"
    r"(?P<value>.*?)"
    r"(?P<close>[}\"])"
    r"(?P<suffix>\s*,?)",
    re.IGNORECASE | re.DOTALL,
)


JOURNAL_ABBREVIATIONS = {
    "chemical reviews": "Chem. Rev.",
    "chemical science": "Chem. Sci.",
    "chemistry of materials": "Chem. Mater.",
    "chemistry a european journal": "Chem. Eur. J.",
    "communications chemistry": "Commun. Chem.",
    "computational materials science": "Comput. Mater. Sci.",
    "current opinion in chemical engineering": "Curr. Opin. Chem. Eng.",
    "inorganic chemistry": "Inorg. Chem.",
    "international journal of quantum chemistry": "Int. J. Quantum Chem.",
    "journal of chemical information and modeling": "J. Chem. Inf. Model.",
    "journal of chemical physics": "J. Chem. Phys.",
    "the journal of chemical physics": "J. Chem. Phys.",
    "journal of chemical theory and computation": "J. Chem. Theory Comput.",
    "journal of computational chemistry": "J. Comput. Chem.",
    "journal of computational physics": "J. Comput. Phys.",
    "journal of materials chemistry a": "J. Mater. Chem. A",
    "journal of medicinal chemistry": "J. Med. Chem.",
    "journal of physical chemistry": "J. Phys. Chem.",
    "journal of physical chemistry a": "J. Phys. Chem. A",
    "journal of physical chemistry b": "J. Phys. Chem. B",
    "journal of physical chemistry c": "J. Phys. Chem. C",
    "journal of physical chemistry letters": "J. Phys. Chem. Lett.",
    "the journal of physical chemistry letters": "J. Phys. Chem. Lett.",
    "nature": "Nature",
    "nature chemistry": "Nat. Chem.",
    "nature communications": "Nat. Commun.",
    "nature computational science": "Nat. Comput. Sci.",
    "nature materials": "Nat. Mater.",
    "nature methods": "Nat. Methods",
    "nature nanotechnology": "Nat. Nanotechnol.",
    "physical chemistry chemical physics": "Phys. Chem. Chem. Phys.",
    "physical review a": "Phys. Rev. A",
    "physical review applied": "Phys. Rev. Appl.",
    "physical review b": "Phys. Rev. B",
    "physical review e": "Phys. Rev. E",
    "physical review letters": "Phys. Rev. Lett.",
    "physical review materials": "Phys. Rev. Mater.",
    "proceedings of the national academy of sciences": "Proc. Natl. Acad. Sci. U.S.A.",
    "science": "Science",
    "scientific reports": "Sci. Rep.",
}


WORD_ABBREVIATIONS = {
    "accounts": "Acc.",
    "advanced": "Adv.",
    "analytical": "Anal.",
    "applied": "Appl.",
    "biochemistry": "Biochem.",
    "bioengineering": "Bioeng.",
    "biology": "Biol.",
    "chemical": "Chem.",
    "chemistry": "Chem.",
    "computational": "Comput.",
    "computer": "Comput.",
    "communications": "Commun.",
    "current": "Curr.",
    "engineering": "Eng.",
    "environmental": "Environ.",
    "european": "Eur.",
    "experimental": "Exp.",
    "international": "Int.",
    "journal": "J.",
    "letters": "Lett.",
    "materials": "Mater.",
    "mathematical": "Math.",
    "medicinal": "Med.",
    "molecular": "Mol.",
    "nanotechnology": "Nanotechnol.",
    "national": "Natl.",
    "organic": "Org.",
    "physical": "Phys.",
    "physics": "Phys.",
    "proceedings": "Proc.",
    "reports": "Rep.",
    "research": "Res.",
    "review": "Rev.",
    "reviews": "Rev.",
    "science": "Sci.",
    "sciences": "Sci.",
    "scientific": "Sci.",
    "society": "Soc.",
    "theory": "Theory",
}

JOURNAL_STOPWORDS = {"and", "of", "the", "for", "in", "on"}


def journal_key(value: str) -> str:
    cleaned = re.sub(r"[{}\\]", "", value)
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", cleaned).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def already_abbreviated(value: str) -> bool:
    if "." in value:
        return True
    words = [word for word in re.findall(r"[A-Za-z]+", value) if word.lower() not in JOURNAL_STOPWORDS]
    return bool(words) and len(words) <= 2


def abbreviate_journal(value: str) -> str:
    stripped = " ".join(value.split())
    key = journal_key(stripped)
    if not key:
        return value
    if key in JOURNAL_ABBREVIATIONS:
        return JOURNAL_ABBREVIATIONS[key]
    if already_abbreviated(stripped):
        return stripped

    words = re.findall(r"[A-Za-z0-9+&-]+", stripped)
    abbreviated = []
    changed = False
    for word in words:
        lower = word.lower()
        if lower in JOURNAL_STOPWORDS:
            continue
        replacement = WORD_ABBREVIATIONS.get(lower)
        if replacement:
            abbreviated.append(replacement)
            changed = True
        else:
            abbreviated.append(word)

    return " ".join(abbreviated) if changed and abbreviated else stripped


def entry_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    start = 0
    while True:
        at = text.find("@", start)
        if at == -1:
            break
        brace = text.find("{", at)
        if brace == -1:
            break
        depth = 0
        end = brace
        for idx in range(brace, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        spans.append((at, end))
        start = end
    return spans


def field_values(entry: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in FIELD_RE.finditer(entry):
        values[match.group("name").lower()] = match.group("value").strip()
    return values


def replace_journal_field(entry: str) -> str:
    values = field_values(entry)
    replacement = values.get("shortjournal") or abbreviate_journal(values.get("journal", ""))
    if not replacement:
        return entry

    def repl(match: re.Match[str]) -> str:
        if match.group("name").lower() != "journal":
            return match.group(0)
        return f"{match.group('prefix')}{match.group('open')}{replacement}{match.group('close')}{match.group('suffix')}"

    return FIELD_RE.sub(repl, entry)


def normalize_bib_text(text: str) -> str:
    if "@" not in text:
        return text

    pieces = []
    cursor = 0
    for start, end in entry_spans(text):
        pieces.append(text[cursor:start])
        pieces.append(replace_journal_field(text[start:end]))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def normalize_bib_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_bib_text(original)
    if normalized != original:
        path.write_text(normalized, encoding="utf-8")
        return True
    return False


def normalize_bib_files(output_dir: Path) -> list[str]:
    changed = []
    for bib in sorted(output_dir.glob("*.bib")):
        if normalize_bib_file(bib):
            changed.append(bib.name)
    return changed
