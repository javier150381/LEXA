import lib.demandas as dem


def test_generar_redaccion_demanda_llm_basic():
    datos = {
        "DESIGNACION_JUZGADOR": "Juez de lo Civil",
        "ACTOR_NOMBRES_APELLIDOS": "Pedro Perez",
        "DEMANDADO_NOMBRES_APELLIDOS": "Juan Lopez",
    }
    texto = dem.generar_redaccion_demanda_llm(datos)
    assert "PRIMERO." in texto
    assert "DÉCIMO SEGUNDO." in texto
    assert "Sugerido" in texto
