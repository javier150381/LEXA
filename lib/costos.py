"""Herramientas para calcular y mostrar costos por caso."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import json
import sys


@dataclass
class CasoCostos:
    demandas: int = 0
    costo_demanda: float = 0.0
    consultas_casos: int = 0
    costo_consulta_caso: float = 0.0
    consultas_jurisprudencia: int = 0
    costo_consulta_juris: float = 0.0

    def total_demandas(self) -> float:
        return self.demandas * self.costo_demanda

    def total_consultas_casos(self) -> float:
        return self.consultas_casos * self.costo_consulta_caso

    def total_consultas_juris(self) -> float:
        return self.consultas_jurisprudencia * self.costo_consulta_juris

    def total(self) -> float:
        return (
            self.total_demandas()
            + self.total_consultas_casos()
            + self.total_consultas_juris()
        )


def calcular_costos(casos: Dict[str, CasoCostos]) -> Dict[str, Dict[str, float]]:
    """Calcula subtotales y totales para cada caso.

    Parameters
    ----------
    casos: Dict[str, CasoCostos]
        Diccionario donde la clave es el nombre del caso y el valor un
        ``CasoCostos`` con las cantidades y costos unitarios.

    Returns
    -------
    Dict[str, Dict[str, float]]
        Datos de costos por caso y un campo ``"Total general"`` con la suma
        de todos los casos.
    """
    resultados: Dict[str, Dict[str, float]] = {}
    total_general = 0.0
    for nombre, info in casos.items():
        tot_dem = info.total_demandas()
        tot_casos = info.total_consultas_casos()
        tot_juris = info.total_consultas_juris()
        tot = info.total()
        resultados[nombre] = {
            "N.º Demandas": info.demandas,
            "Costo por demanda": info.costo_demanda,
            "Total demandas": tot_dem,
            "N.º Consultas de casos": info.consultas_casos,
            "Costo por consulta de caso": info.costo_consulta_caso,
            "Total consultas de casos": tot_casos,
            "N.º Consultas de jurisprudencia": info.consultas_jurisprudencia,
            "Costo por consulta de jurisprudencia": info.costo_consulta_juris,
            "Total consultas de jurisprudencia": tot_juris,
            "Total por caso": tot,
        }
        total_general += tot
    resultados["Total general"] = total_general
    return resultados


def formatear_tabla_costos(resultados: Dict[str, Dict[str, float]]) -> str:
    """Devuelve una tabla en texto plano con los costos calculados."""
    headers = [
        "Caso/Categoría",
        "N.º Demandas",
        "Costo por demanda",
        "Total demandas",
        "N.º Consultas de casos",
        "Costo por consulta de caso",
        "Total consultas de casos",
        "N.º Consultas de jurisprudencia",
        "Costo por consulta de jurisprudencia",
        "Total consultas de jurisprudencia",
        "Total por caso",
    ]

    filas = []
    # Mapeo de cada encabezado numérico para calcular totales verticales
    numeric_headers = [
        "N.º Demandas",
        "Costo por demanda",
        "Total demandas",
        "N.º Consultas de casos",
        "Costo por consulta de caso",
        "Total consultas de casos",
        "N.º Consultas de jurisprudencia",
        "Costo por consulta de jurisprudencia",
        "Total consultas de jurisprudencia",
        "Total por caso",
    ]
    suma_cols = {h: 0 for h in numeric_headers}

    for nombre, datos in resultados.items():
        if nombre == "Total general":
            continue
        fila = [
            nombre,
            datos["N.º Demandas"],
            f"{datos['Costo por demanda']:.2f}",
            f"{datos['Total demandas']:.2f}",
            datos["N.º Consultas de casos"],
            f"{datos['Costo por consulta de caso']:.2f}",
            f"{datos['Total consultas de casos']:.2f}",
            datos["N.º Consultas de jurisprudencia"],
            f"{datos['Costo por consulta de jurisprudencia']:.2f}",
            f"{datos['Total consultas de jurisprudencia']:.2f}",
            f"{datos['Total por caso']:.2f}",
        ]
        filas.append(fila)

        # Acumular totales verticales usando los valores originales
        suma_cols["N.º Demandas"] += datos["N.º Demandas"]
        suma_cols["Costo por demanda"] += datos["Costo por demanda"]
        suma_cols["Total demandas"] += datos["Total demandas"]
        suma_cols["N.º Consultas de casos"] += datos["N.º Consultas de casos"]
        suma_cols["Costo por consulta de caso"] += datos["Costo por consulta de caso"]
        suma_cols["Total consultas de casos"] += datos["Total consultas de casos"]
        suma_cols["N.º Consultas de jurisprudencia"] += datos["N.º Consultas de jurisprudencia"]
        suma_cols["Costo por consulta de jurisprudencia"] += datos[
            "Costo por consulta de jurisprudencia"
        ]
        suma_cols["Total consultas de jurisprudencia"] += datos[
            "Total consultas de jurisprudencia"
        ]
        suma_cols["Total por caso"] += datos["Total por caso"]

    # Construir la fila de totales verticales
    totales = ["Total general"]
    for h in numeric_headers:
        val = suma_cols[h]
        if h.startswith("N.º"):
            totales.append(str(int(val)))
        else:
            totales.append(f"{val:.2f}")

    # Calcular anchos de columna
    anchos = [len(h) for h in headers]
    for fila in filas + [totales]:
        for i, col in enumerate(fila):
            anchos[i] = max(anchos[i], len(str(col)))

    def _format_row(row):
        return "| " + " | ".join(str(col).ljust(anchos[i]) for i, col in enumerate(row)) + " |"

    linea = "|" + "|".join("-" * (a + 2) for a in anchos) + "|"

    salida = [_format_row(headers), linea]
    for fila in filas:
        salida.append(_format_row(fila))
    salida.append(linea)
    salida.append(_format_row(totales))
    return "\n".join(salida)


def _cargar_json(path: str) -> Dict[str, CasoCostos]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    casos = {}
    for nombre, datos in raw.items():
        casos[nombre] = CasoCostos(
            demandas=datos.get("demandas", 0),
            costo_demanda=datos.get("costo_demanda", 0.0),
            consultas_casos=datos.get("consultas_casos", 0),
            costo_consulta_caso=datos.get("costo_consulta_caso", 0.0),
            consultas_jurisprudencia=datos.get("consultas_jurisprudencia", 0),
            costo_consulta_juris=datos.get("costo_consulta_juris", 0.0),
        )
    return casos


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Uso: python -m lib.costos <archivo.json>")
        sys.exit(1)
    casos = _cargar_json(argv[0])
    resultados = calcular_costos(casos)
    print(formatear_tabla_costos(resultados))


if __name__ == "__main__":  # pragma: no cover
    main()
