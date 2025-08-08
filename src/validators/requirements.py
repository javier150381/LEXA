"""Validación de requisitos para la generación de demandas."""
from __future__ import annotations

import os
from typing import Dict, List

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

# Reglas básicas por tipo de demanda
DEFAULT_RULES: Dict[str, Dict[str, List[str]]] = {
    "default": {
        "required": [
            "ACTOR_NOMBRES_APELLIDOS",
            "DEMANDADO_NOMBRES_APELLIDOS",
            "FUNDAMENTOS_DERECHO",
            "PRETENSION",
        ]
    }
}


def load_rules(path: str = "validators/config.yaml") -> Dict[str, Dict[str, List[str]]]:
    """Carga las reglas combinando las predeterminadas con las del archivo."""
    rules: Dict[str, Dict[str, List[str]]] = {
        k: {"required": list(v.get("required", []))} for k, v in DEFAULT_RULES.items()
    }
    if yaml is None or not os.path.exists(path):
        return rules
    with open(path, "r", encoding="utf8") as fh:
        try:
            data = yaml.safe_load(fh) or {}
        except Exception:
            data = {}
    for tipo, cfg in data.items():
        req = cfg.get("required", []) if isinstance(cfg, dict) else []
        if tipo in rules:
            rules[tipo]["required"] = list(dict.fromkeys(rules[tipo]["required"] + req))
        else:
            rules[tipo] = {"required": list(req)}
    return rules


def validate_requirements(
    demand_type: str, data: Dict[str, str], config_path: str = "validators/config.yaml"
) -> List[str]:
    """Devuelve una lista de campos faltantes según las reglas del tipo."""
    rules = load_rules(config_path)
    tipo_rules = rules.get(demand_type) or rules.get("default", {})
    required = tipo_rules.get("required", [])
    missing = [campo for campo in required if not data.get(campo)]
    return missing
