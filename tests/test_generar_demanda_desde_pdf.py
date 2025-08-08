from unittest import mock

import lib.demandas as dem


def test_generar_demanda_desde_pdf_replaces_placeholders():
    plantilla = "Demanda presentada por [NOMBRE] contra [DEMANDADO]."
    ctx = dem.DemandasContext()
    with mock.patch.dict(ctx.demandas_textos, {"tpl.pdf": plantilla}, clear=True), \
         mock.patch.dict(ctx.datos_basicos_demandas, {}, clear=True), \
         mock.patch.dict(ctx.datos_basicos_casos, {"MiCaso": {"NOMBRE": "Ana", "DEMANDADO": "Luis"}}, clear=True), \
         mock.patch.dict(ctx.vectorstores_por_caso, {}, clear=True):
        resultado = dem.generar_demanda_desde_pdf("tpl.pdf", "MiCaso", ctx=ctx)

    assert resultado == "Demanda presentada por Ana contra Luis."
    assert "[NOMBRE]" not in resultado
    assert "[DEMANDADO]" not in resultado


def test_generar_demanda_desde_pdf_custom_folder():
    plantilla = "Documento para [NOMBRE]"
    ctx = dem.DemandasContext()
    with mock.patch.dict(ctx.datos_basicos_casos, {"Caso": {"NOMBRE": "Ana"}}, clear=True), \
         mock.patch("lib.demandas.parsear_plantilla_desde_pdf", return_value=(plantilla, [])) as m:
        resultado = dem.generar_demanda_desde_pdf(
            "ej.pdf",
            "Caso",
            ctx=ctx,
            carpeta="/tmp/area",
        )
        m.assert_called_once_with("ej.pdf", carpeta="/tmp/area")

    assert "Ana" in resultado


def test_generar_demanda_desde_pdf_reemplaza_lineas_punteadas():
    plantilla = "Yo, ________, demando a ________"
    ctx = dem.DemandasContext()
    with mock.patch.dict(ctx.demandas_textos, {"ej.pdf": plantilla}, clear=True):
        datos = {
            "ACTOR_NOMBRES_APELLIDOS": "Ana",
            "DEMANDADO_NOMBRES_APELLIDOS": "Luis",
        }
        resultado = dem.generar_demanda_desde_pdf("ej.pdf", "", datos=datos, ctx=ctx)

    assert "Ana" in resultado
    assert "Luis" in resultado
