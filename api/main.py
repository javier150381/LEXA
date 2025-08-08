import logging
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from lib import demandas as dem
from src.classifier.suggest_type import suggest_type
from src.validators.requirements import validate_requirements

logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO)

app = FastAPI()


class GenerarRequest(BaseModel):
    tipo: str
    caso: str = ""


@app.post("/generar")
async def generar(req: GenerarRequest) -> Dict[str, str]:
    """Genera una demanda del ``tipo`` indicado para el ``caso`` dado."""
    try:
        texto = dem.generar_demanda_de_tipo(req.tipo, req.caso)
        return {"resultado": texto}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error al generar la demanda")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ClasificarRequest(BaseModel):
    descripcion: str
    top_n: int = 3


@app.post("/clasificar")
async def clasificar(req: ClasificarRequest) -> Dict[str, List[str]]:
    """Clasifica una descripción de caso en posibles categorías."""
    try:
        tipos = suggest_type(req.descripcion, top_n=req.top_n)
        return {"tipos": tipos}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error al clasificar el caso")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ValidarRequest(BaseModel):
    tipo: str
    datos: Dict[str, str]


@app.post("/validar")
async def validar(req: ValidarRequest) -> Dict[str, List[str]]:
    """Valida los requisitos obligatorios para una demanda."""
    try:
        faltantes = validate_requirements(req.tipo, req.datos)
        return {"faltantes": faltantes}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error al validar la demanda")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
