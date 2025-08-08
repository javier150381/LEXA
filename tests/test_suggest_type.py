import unittest

from src.classifier.suggest_type import suggest_type


class SuggestTypeTests(unittest.TestCase):
    def test_simple_match(self):
        self.assertEqual(suggest_type("me despidieron del trabajo"), ["Laboral"])

    def test_multiple_matches(self):
        res = suggest_type("divorcio y custodia de mis hijos", top_n=2)
        self.assertEqual(res, ["Familiar"])

    def test_ignore_accents(self):
        # Should match even if accents are omitted in the description
        self.assertEqual(suggest_type("necesito pension alimenticia"), ["Familiar"])

    def test_no_match(self):
        self.assertEqual(suggest_type("tema sin relacion"), [])


if __name__ == "__main__":
    unittest.main()
