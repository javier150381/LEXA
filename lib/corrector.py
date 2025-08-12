"""Herramientas de corrección gramatical usando LanguageTool."""

try:
    import language_tool_python
except ImportError:  # pragma: no cover
    language_tool_python = None

_tool = None
if language_tool_python is not None:  # pragma: no cover - lazy init
    _tool = language_tool_python.LanguageTool("en-US")


def corregir(texto: str):
    """Devuelve sugerencias de corrección para ``texto``.

    Cada sugerencia incluye el fragmento con error, un mensaje de
    LanguageTool y las posibles sustituciones recomendadas.

    Parameters
    ----------
    texto: str
        Texto a evaluar.

    Returns
    -------
    list[dict]
        Lista de sugerencias con claves ``error``, ``mensaje`` y
        ``sugerencias``.
    """
    if _tool is None:  # pragma: no cover
        raise ImportError("language_tool_python no está instalado")

    matches = _tool.check(texto)
    resultados = []
    for match in matches:
        fragmento = texto[match.offset : match.offset + match.errorLength]
        resultados.append(
            {
                "error": fragmento,
                "mensaje": match.message,
                "sugerencias": match.replacements,
            }
        )
    return resultados
