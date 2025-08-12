"""Funciones de voz: transcripción con Whisper y respuesta con GPT-4.

Este módulo proporciona utilidades para transcribir archivos de audio
usando el modelo `whisper` de OpenAI y conversar con un LLM (por
defecto GPT-4) usando la transcripción como entrada. Las transcripciones
se guardan para análisis posterior.
"""

from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Directorio por defecto donde se almacenarán las transcripciones
TRANSCRIPCIONES_DIR = Path("data/transcripciones")


def transcribir_audio(audio_path: Union[str, Path], model_name: str = "small") -> str:
    """Transcribe el archivo de audio indicado usando `whisper`.

    Parameters
    ----------
    audio_path: Union[str, Path]
        Ruta al archivo de audio a transcribir.
    model_name: str
        Nombre del modelo de whisper a utilizar.

    Returns
    -------
    str
        Texto transcrito del audio.

    Raises
    ------
    ImportError
        Si la librería `whisper` no está instalada.
    """
    try:
        import whisper  # type: ignore
    except Exception as exc:  # pragma: no cover - error path
        raise ImportError("whisper no está instalado") from exc

    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_path))
    return result.get("text", "").strip()


def conversar(
    audio_path: Union[str, Path],
    *,
    model_name: str = "small",
    llm_model: str = "gpt-4o-mini",
    storage_dir: Union[str, Path] = TRANSCRIPCIONES_DIR,
) -> str:
    """Transcribe el audio y obtiene una respuesta usando GPT-4.

    La transcripción se guarda en ``storage_dir`` con un nombre que
    incluye marca de tiempo para facilitar su análisis posterior.

    Parameters
    ----------
    audio_path: Union[str, Path]
        Ruta del archivo de audio a procesar.
    model_name: str, optional
        Modelo de whisper a emplear.
    llm_model: str, optional
        Modelo de lenguaje a utilizar para la respuesta.
    storage_dir: Union[str, Path], optional
        Carpeta donde se guardarán las transcripciones.

    Returns
    -------
    str
        Respuesta generada por el modelo de lenguaje.
    """
    texto = transcribir_audio(audio_path, model_name)

    storage_path = Path(storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    transcript_file = storage_path / f"{Path(audio_path).stem}_{timestamp}.txt"
    transcript_file.write_text(texto, encoding="utf-8")

    llm = ChatOpenAI(model=llm_model, api_key=os.getenv("OPENAI_API_KEY"))
    respuesta = llm.invoke(texto)
    return getattr(respuesta, "content", str(respuesta))
