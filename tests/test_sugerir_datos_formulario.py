import unittest
from unittest import mock

import lib.demandas as dem

class SugerirDatosFormularioTests(unittest.TestCase):
    def test_vacio_si_no_caso(self):
        ctx = dem.DemandasContext()
        self.assertEqual(dem.sugerir_datos_para_formulario(None, ctx), {})

    def test_usa_obtener_dato(self):
        ctx = dem.DemandasContext()
        def fake(ph, caso, ctx=None):
            return f"VAL_{ph}"
        with mock.patch.object(dem, "obtener_dato_de_caso", side_effect=fake):
            datos = dem.sugerir_datos_para_formulario("X", ctx)

        expected_keys = (
            dem.CAMPOS_DATOS_ACTOR
            + dem.CAMPOS_DATOS_DEFENSOR
            + dem.CAMPOS_DATOS_DEMANDADO
            + [
                s
                for s in dem.SECCIONES_DEMANDA
                if s not in ("DATOS_ACTOR", "DATOS_DEFENSOR", "DATOS_DEMANDADO")
            ]
        )

        for sec in expected_keys:
            self.assertEqual(datos[sec], f"VAL_{sec}")

    def test_jurisprudencia_si_falta(self):
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = object()
        with mock.patch.object(dem, "obtener_dato_de_caso", return_value=None), \
             mock.patch.object(dem, "buscar_palabras_clave_fn", return_value="JURI") as mb:
            datos = dem.sugerir_datos_para_formulario("X", ctx)
        self.assertEqual(datos["FUNDAMENTOS_DERECHO"], "JURI")
        mb.assert_called()

    def test_resumen_si_faltan_hechos(self):
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = object()
        with mock.patch.object(dem, "obtener_dato_de_caso", return_value=None), \
             mock.patch.object(dem, "resumir_caso", return_value="SUM"), \
             mock.patch.object(dem, "buscar_palabras_clave_fn", return_value="X"):
            datos = dem.sugerir_datos_para_formulario("X", ctx)
        self.assertEqual(datos["HECHOS"], "SUM")

if __name__ == "__main__":
    unittest.main()
