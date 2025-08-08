import lib.demandas as dem


def test_generar_redaccion_demanda_basico():
    datos = {
        "DESIGNACION_JUZGADOR": "Juez de lo Civil",
        "ACTOR_NOMBRES_APELLIDOS": "Pedro Perez",
        "RUC": "",
        "DEMANDADO_NOMBRES_APELLIDOS": "Juan Lopez",
    }
    texto = dem.generar_redaccion_demanda(datos)
    assert "PRIMERO. - LA DESIGNACIÓN DEL JUEZ ANTE QUIEN SE PROPONE." in texto
    assert "SEGUNDO. - LOS NOMBRES Y APELLIDOS Y MÁS GENERALES DE LEY DEL ACTOR SON" in texto
    assert "TERCERO. - Mi número de RUC es VACIO." in texto
    assert "CUARTO. - Demando al señor Juan Lopez" in texto
