import lib.costos as cos


def test_calcular_costos():
    casos = {
        "CASO1": cos.CasoCostos(
            demandas=2,
            costo_demanda=50.0,
            consultas_casos=3,
            costo_consulta_caso=10.0,
            consultas_jurisprudencia=1,
            costo_consulta_juris=5.0,
        )
    }
    resultados = cos.calcular_costos(casos)
    assert resultados["CASO1"]["Total demandas"] == 100.0
    assert resultados["CASO1"]["Total por caso"] == 135.0
    assert resultados["Total general"] == 135.0


def test_formatear_tabla_costos():
    casos = {"CASO1": cos.CasoCostos(demandas=1, costo_demanda=5.0)}
    tabla = cos.formatear_tabla_costos(cos.calcular_costos(casos))
    assert "CASO1" in tabla
    assert "5.00" in tabla

