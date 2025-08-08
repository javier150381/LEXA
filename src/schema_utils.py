from __future__ import annotations

import json
import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, List

from pdfminer.high_level import extract_text

# Directory where schema files live
SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "forms" / "schemas"
INDEX_FILE = SCHEMAS_DIR / "index.json"

# Directory for caching form data
FORM_DATA_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "form_cache"
# Directory for caching placeholder maps
PLACEHOLDER_CACHE_DIR = (
    Path(__file__).resolve().parents[1] / "data" / "placeholder_cache"
)


ESSENTIAL_PLACEHOLDERS = {"HECHOS", "FUNDAMENTOS_DERECHO", "PRETENSION", "REFERENCIAS"}


def _slugify(text: str) -> str:
    """Return a filesystem-safe slug for *text*."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _normalize_placeholder(name: str) -> str:
    """Return a cleaned, uppercased placeholder name."""
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"[\._-]+$", "", name)
    return name.upper()


def available_schema_types() -> List[str]:
    """List available demand types based on existing schema files."""
    tipos: List[str] = []
    for path in SCHEMAS_DIR.glob("demanda_*.json"):
        tipos.append(path.stem[len("demanda_"):])
    return sorted(tipos)


def load_schema(tipo: str) -> Dict[str, Any]:
    """Load schema for *tipo* from disk."""
    path = SCHEMAS_DIR / f"demanda_{tipo}.json"
    with open(path, "r", encoding="utf8") as fh:
        return json.load(fh)


def list_placeholders(template_path: str) -> List[str]:
    """Return placeholders found in ``template_path``.

    The function supports plain text files and PDFs. Placeholders are
    substrings enclosed in square brackets (e.g. ``[NOMBRE]``). The
    detected placeholder names are printed and returned as an ordered
    list.
    """
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe {template_path}")

    text = ""
    if path.suffix.lower() == ".pdf":
        try:
            text = extract_text(str(path)) or ""
        except Exception:
            text = ""
        if not text:
            from lib.pdf_utils import read_pdf_text

            text = read_pdf_text(str(path))
    else:
        with open(path, "r", encoding="utf8", errors="ignore") as fh:
            text = fh.read()

    # Preserve the order of appearance while deduplicating
    seen: set[str] = set()
    placeholders: List[str] = []
    for match in re.findall(r"\[([^\]]+)\]", text):
        name = match.upper()
        if name not in seen:
            seen.add(name)
            placeholders.append(name)

    for name in placeholders:
        print(name)
    return placeholders


def placeholders_from_text(text: str) -> List[str]:
    """Return placeholders found directly in ``text``.

    Placeholders are substrings enclosed in square brackets. The
    returned list contains unique placeholder names in uppercase,
    preserving the order in which they first appear.
    """

    seen: set[str] = set()
    placeholders: List[str] = []
    for match in re.findall(r"\[([^\]]+)\]", text):
        name = match.upper()
        if name not in seen:
            seen.add(name)
            placeholders.append(name)

    return placeholders


def form_from_text(text: str, title: str = "Formulario") -> Dict[str, Any]:
    """Generate a form schema from placeholders in ``text``."""

    placeholders = placeholders_from_text(text)
    fields: List[Dict[str, Any]] = []
    for name in placeholders:
        field: Dict[str, Any] = {
            "name": _slugify(name).upper(),
            "label": name.replace("_", " ").title(),
            "required": False,
        }
        fields.append(field)
    return {"title": title, "fields": fields}


def fill_placeholders(text: str, data: Dict[str, str]) -> str:
    """Replace placeholders in ``text`` using the provided ``data``.

    The keys in ``data`` can match the placeholder as it appears in the
    template, its uppercase form or its slugified name (uppercase).
    Unmatched placeholders are left intact.
    """

    def _replace(match: re.Match[str]) -> str:
        raw = match.group(1)
        slug = _slugify(raw).upper()
        return (
            data.get(raw)
            or data.get(raw.upper())
            or data.get(slug)
            or f"[{raw}]"
        )

    return re.sub(r"\[([^\]]+)\]", _replace, text)


def generate_schema_from_pdf(pdf_path: str, llm_model=None) -> tuple[Dict[str, Any], Dict[str, str]]:
    """Generate a schema and extract original data from ``pdf_path``.

    The PDF is converted to text. If it already contains placeholders
    (tokens enclosed in square brackets, e.g. ``[NOMBRE]``), those are used to
    build the schema. Otherwise an LLM is used to detect personal data,
    returning a template with placeholders and a mapping with the original
    values. The function returns a tuple ``(schema, datos)`` where ``datos``
    contains the values detected in the original document.
    """
    base = Path(pdf_path).stem.replace("_", " ")
    title = base.title()

    try:
        text = extract_text(pdf_path) or ""
    except Exception:
        text = ""
    if not text:
        from lib.pdf_utils import read_pdf_text

        text = read_pdf_text(pdf_path)

    datos: Dict[str, str] = {}
    seen: set[str] = set()
    placeholders: List[str] = []
    for match in re.findall(r"\[([^\]]+)\]", text):
        name = _normalize_placeholder(match)
        if name and name not in seen:
            seen.add(name)
            placeholders.append(name)

    fields: List[Dict[str, Any]] = []
    if placeholders:
        for name in placeholders:
            field: Dict[str, Any] = {
                "name": _slugify(name).upper(),
                "label": name.replace("_", " ").title(),
                "required": False,
            }
            if name in {"HECHOS", "FUNDAMENTOS_DERECHO", "PRETENSION"}:
                field["type"] = "text"
            fields.append(field)

        missing = ESSENTIAL_PLACEHOLDERS - set(placeholders)
        if missing:
            from lib.plantillas import generar_plantilla_por_llm

            plantilla, campos = generar_plantilla_por_llm(text, llm_model)
            datos.update({k.upper(): str(v) for k, v in campos.items()})
            seen_llm = set(placeholders)
            for match in re.findall(r"\{\{([^}]+)\}\}", plantilla):
                name = _normalize_placeholder(match)
                if name and name not in seen_llm:
                    seen_llm.add(name)
                    field = {
                        "name": _slugify(name).upper(),
                        "label": name.replace("_", " ").title(),
                        "required": False,
                    }
                    if name in {"HECHOS", "FUNDAMENTOS_DERECHO", "PRETENSION"}:
                        field["type"] = "text"
                    fields.append(field)
    else:
        from lib.plantillas import generar_plantilla_por_llm

        plantilla, campos = generar_plantilla_por_llm(text, llm_model)
        datos.update({k.upper(): str(v) for k, v in campos.items()})
        seen_llm: set[str] = set()
        placeholders = []
        for match in re.findall(r"\{\{([^}]+)\}\}", plantilla):
            name = _normalize_placeholder(match)
            if name and name not in seen_llm:
                seen_llm.add(name)
                placeholders.append(name)
        for name in placeholders:
            field: Dict[str, Any] = {
                "name": _slugify(name).upper(),
                "label": name.replace("_", " ").title(),
                "required": False,
            }
            if name in {"HECHOS", "FUNDAMENTOS_DERECHO", "PRETENSION"}:
                field["type"] = "text"
            fields.append(field)
        if not fields:
            fields = [
                {"name": "NOMBRE", "label": "Nombre", "required": False},
                {"name": "DETALLE", "label": "Detalle", "type": "text"},
            ]

    return {"title": title, "fields": fields}, datos


def load_or_generate_schema(tipo: str) -> Dict[str, Any]:
    """Load schema for *tipo* or generate a default one if missing."""
    path = SCHEMAS_DIR / f"demanda_{tipo}.json"
    if path.exists():
        with open(path, "r", encoding="utf8") as fh:
            return json.load(fh)

    schema = {
        "title": f"Demanda {tipo}",
        "fields": [
            {"name": "NOMBRE", "label": "Nombre", "required": False},
            {"name": "DETALLE", "label": "Detalle", "type": "text"},
        ],
    }
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf8") as fh:
        json.dump(schema, fh, indent=2, ensure_ascii=False)
    return schema


def update_schema_index(tipo: str, pdf_hash: str) -> None:
    """Update schema index with the hash for *tipo*."""
    index: Dict[str, str] = {}
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf8") as fh:
            index = json.load(fh)
    index[tipo] = pdf_hash
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)


def hash_for_pdf(path: str) -> str:
    """Return SHA256 hash of the PDF at *path*."""
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def index_hash(tipo: str) -> str | None:
    """Return stored hash for *tipo* if present."""
    if not INDEX_FILE.exists():
        return None
    with open(INDEX_FILE, "r", encoding="utf8") as fh:
        index = json.load(fh)
    return index.get(tipo)


def cache_form_data(tipo: str, data: Dict[str, str]) -> None:
    """Cache ``data`` for form type ``tipo``.

    The data is stored as JSON under ``FORM_DATA_CACHE_DIR``.
    """
    FORM_DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = FORM_DATA_CACHE_DIR / f"{tipo}.json"
    with open(path, "w", encoding="utf8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_form_data(tipo: str) -> Dict[str, str]:
    """Load cached data for form type ``tipo`` if available."""
    path = FORM_DATA_CACHE_DIR / f"{tipo}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf8") as fh:
        return json.load(fh)


def cache_placeholder_mapping(tipo: str, data: Dict[str, str]) -> None:
    """Cache placeholder mapping for form type ``tipo``."""
    PLACEHOLDER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = PLACEHOLDER_CACHE_DIR / f"{tipo}.json"
    with open(path, "w", encoding="utf8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

