import lib.demandas as dem
from unittest import mock


def test_sugerir_juzgados_default():
    res = dem.sugerir_juzgados()
    assert "Unidad Judicial" in res[0]


def test_determinar_procedimiento():
    assert dem.determinar_procedimiento(5000, "") == "Sumario"
    assert dem.determinar_procedimiento(20000, "") == "Ordinario"


def test_sugerir_fundamentos_default():
    res = dem.sugerir_fundamentos_derecho()
    assert "Art." in res[0]


def test_elaborar_fundamentos_usa_helpers():
    ctx = dem.DemandasContext()
    with mock.patch.object(dem, "buscar_palabras_clave_fn", return_value="TXT") as mb, \
         mock.patch.object(dem, "mejorar_fundamentos_llm", return_value="MEJ") as mm:
        texto = dem.elaborar_fundamentos_derecho("caso1", ctx)
    mb.assert_called()
    mm.assert_called_with("TXT", ctx)
    assert texto == "MEJ"
