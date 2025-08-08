import lib.demandas as dem


def test_extrae_actor_y_demandado():
    texto = (
        "PRIMERO. - DESIGNACIÓN DEL JUZGADOR:\n"
        "SEGUNDO. - DATOS DEL ACTOR:\n"
        "JUAN PEREZ, de nacionalidad ecuatoriana con cédula 1234567890, de 30 años de edad.\n"
        "TERCERO. - DATOS DEL DEFENSOR:\n"
        "CUARTO. - RUC:\n"
        "QUINTO. - DATOS DEL DEMANDADO:\n"
        "ANA GOMEZ, con cédula 0987654321, de 25 años de edad.\n"
    )

    datos = dem.extraer_datos_de_texto(texto)
    assert datos["ACTOR_NOMBRES_APELLIDOS"] == "Juan Perez"
    assert datos["ACTOR_CEDULA"] == "1234567890"
    assert datos["DEMANDADO_NOMBRES_APELLIDOS"] == "Ana Gomez"
    assert datos["DEMANDADO_CEDULA"] == "0987654321"

