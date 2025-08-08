import unittest
from unittest import mock

import lib.demandas as dem

class GenerarResumenDemandaTests(unittest.TestCase):
    def test_llama_sugerir_datos(self):
        ctx = dem.DemandasContext()
        datos = {
            "DESIGNACION_JUZGADOR": "J1",
            "ACTOR_NOMBRES_APELLIDOS": "A",
            "ACTOR_CEDULA": "1",
            "ACTOR_PROVINCIA": "APROV",
            "ACTOR_CANTON": "ACANT",
            "ACTOR_CALLE_PRIMARIA": "AC1",
            "ACTOR_CALLE_SECUNDARIA": "AC2",
            "ACTOR_NUMERO_CASA": "ANUM",
            "DEFENSOR_NOMBRE": "D",
            "RUC": "R",
            "DEMANDADO_NOMBRES_APELLIDOS": "DN",
            "DEMANDADO_CEDULA": "DC",
            "DEMANDADO_NACIONALIDAD": "DNAC",
            "DEMANDADO_PROFESION": "DP",
            "DEMANDADO_EDAD": "DE",
            "DEMANDADO_PROVINCIA": "DPROV",
            "DEMANDADO_CANTON": "DCANT",
            "DEMANDADO_CALLE_PRIMARIA": "DC1",
            "DEMANDADO_CALLE_SECUNDARIA": "DC2",
            "DEMANDADO_NUMERO_CASA": "DNUM",
            "DEMANDADO_DESCRIPCION_VIVIENDA": "DESC",
            "DEMANDADO_DIR_ELECTRONICA": "DDE",
            "HECHOS": "H",
            "FUNDAMENTOS_DERECHO": "FD",
            "ACCESO_PRUEBAS": "AP",
            "PRETENSION": "P",
            "CUANTIA": "C",
            "PROCEDIMIENTO": "PR",
            "FIRMAS": "F",
            "OTROS": "O",
        }
        with mock.patch.object(dem, "sugerir_datos_para_formulario", return_value=datos) as ms:
            texto = dem.generar_resumen_demanda("X", ctx)
        ms.assert_called_with("X", ctx)
        self.assertIn("PRIMERO. - DESIGNACIÓN DEL JUZGADOR", texto)
        self.assertIn("DÉCIMO SEGUNDO. - FIRMAS", texto)

    def test_vacio_si_faltan(self):
        ctx = dem.DemandasContext()
        datos = {}
        with mock.patch.object(dem, "sugerir_datos_para_formulario", return_value=datos):
            texto = dem.generar_resumen_demanda("X", ctx)
        self.assertIn("VACIO", texto)
        self.assertIn("DÉCIMO SEGUNDO. - FIRMAS", texto)

if __name__ == "__main__":
    unittest.main()
