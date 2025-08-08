from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field, root_validator

from src.validators.requirements import DEFAULT_RULES, validate_requirements


class DemandRequest(BaseModel):
    """Datos necesarios para generar una demanda."""

    TIPO_DEMANDA: str = Field("default", description="Tipo de demanda")
    ACTOR_NOMBRES_APELLIDOS: str
    DEMANDADO_NOMBRES_APELLIDOS: str
    FUNDAMENTOS_DERECHO: str
    PRETENSION: str

    @root_validator
    def check_required_fields(cls, values: Dict[str, str]) -> Dict[str, str]:
        demand_type = values.get("TIPO_DEMANDA", "default")
        missing = validate_requirements(demand_type, values)
        if missing:
            raise ValueError(f"Faltan datos obligatorios: {', '.join(missing)}")
        return values

    class Config:
        extra = "allow"


class DemandResponse(BaseModel):
    """Respuesta con el texto generado de la demanda."""

    texto: str


# Verificar que los campos requeridos del modelo coincidan con las reglas por defecto
MODEL_REQUIRED_FIELDS = [
    name for name, field in DemandRequest.__fields__.items()
    if field.required and name != "TIPO_DEMANDA"
]
if set(MODEL_REQUIRED_FIELDS) != set(DEFAULT_RULES["default"]["required"]):
    raise AssertionError(
        "Los campos requeridos de DemandRequest no coinciden con validators.requirements.DEFAULT_RULES"
    )
