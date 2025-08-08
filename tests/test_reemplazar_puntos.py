import lib.demandas as dem


def test_reemplazar_puntos_basico():
    texto = "Yo, .................., presento en .................."
    valores = ["Juan Perez", "Quito"]
    resultado = dem.reemplazar_puntos(texto, valores)
    assert resultado == "Yo, Juan Perez, presento en Quito"


def test_reemplazar_puntos_guiones():
    texto = "Yo, _________, presento en _________"
    valores = ["Maria Lopez", "Cuenca"]
    resultado = dem.reemplazar_puntos(texto, valores)
    assert resultado == "Yo, Maria Lopez, presento en Cuenca"
