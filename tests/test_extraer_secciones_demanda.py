import unittest
import lib.demandas as dem

class ExtraerSeccionesTests(unittest.TestCase):
    def test_extrae_secciones_basico(self):
        texto = (
            "PRIMERO. - DESIGNACIÓN DEL JUZGADOR:\nA\n\n"
            "DÉCIMO SEGUNDO. - FIRMAS DEL ACTOR Y ABOGADO:\nFirma"
        )
        secs = dem.extraer_secciones_demanda(texto)
        self.assertEqual(secs["DESIGNACION_JUZGADOR"], "A")
        self.assertEqual(secs["FIRMAS"], "Firma")

if __name__ == '__main__':
    unittest.main()
