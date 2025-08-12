from typing import Iterable

import whisper
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def transcribir_audio(path: str, modelo: str = "small") -> str:
    """Transcribe *path* usando Whisper y devuelve el texto."""
    model = whisper.load_model(modelo)
    result = model.transcribe(path, language="es")
    return result.get("text", "").strip()


def cargar_documentos(rutas: Iterable[str], chunk_size: int = 1000, chunk_overlap: int = 200):
    """Carga archivos de *rutas* y los trocea en fragmentos."""
    documentos = []
    for ruta in rutas:
        loader = PyPDFLoader(ruta) if ruta.lower().endswith(".pdf") else TextLoader(ruta, encoding="utf-8")
        documentos.extend(loader.load())
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(documentos)
