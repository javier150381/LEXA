import re

try:
    from pdf2image import convert_from_path
    import pytesseract
except Exception:  # noqa: BLE001 - optional OCR dependencies
    convert_from_path = None
    pytesseract = None

from langchain_community.document_loaders import PyPDFLoader


def _limpiar_texto(texto: str) -> str:
    """Normaliza espacios y saltos de línea."""
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    texto = re.sub(r"\n[ \t]+", "\n", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _ocr_pdf(path: str) -> str:
    """Return OCR text for *path* if OCR deps are available."""
    if convert_from_path is None or pytesseract is None:
        return ""
    try:
        images = convert_from_path(path)
    except Exception:
        return ""
    parts: list[str] = []
    for img in images:
        try:
            parts.append(pytesseract.image_to_string(img, lang="spa"))
        except Exception:
            continue
    return _limpiar_texto("\n".join(parts))


def read_pdf_text(path: str) -> str:
    """Extrae texto de *path*, usando OCR si el PDF está escaneado."""
    try:
        from pdfminer.high_level import extract_text
        texto = extract_text(path)
    except Exception:
        try:
            loader = PyPDFLoader(path, extract_images=False)
            docs = loader.load()
            texto = "\n".join(d.page_content for d in docs)
        except Exception:
            texto = ""
    texto = _limpiar_texto(texto or "")
    if texto:
        return texto
    return _ocr_pdf(path)
