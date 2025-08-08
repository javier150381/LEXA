import unittest
import lib.demandas as dem

class ArmarReemplazosTests(unittest.TestCase):
    def test_enum_hechos_y_placeholder(self):
        datos = {
            "HECHOS": "Uno\nDos",
            "DESIGNACION_JUZGADOR": "Juez"
        }
        plantilla = "[DESIGNACION_JUZGADOR]\n[HECHO1]\n[HECHO2]\n[OTRO]"
        reempl = dem.armar_reemplazos(datos, plantilla)
        self.assertEqual(reempl["HECHO1"], "Uno")
        self.assertEqual(reempl["HECHO2"], "Dos")
        # Placeholders missing in datos should get underscores
        self.assertEqual(reempl["OTRO"], "___")
        # Existing keys keep their value
        self.assertEqual(reempl["DESIGNACION_JUZGADOR"], "Juez")

if __name__ == "__main__":
    unittest.main()
