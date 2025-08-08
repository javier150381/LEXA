import os
import json
import tempfile
from lib.demandas import comparar_json_files


def test_comparar_json_files_diff():
    d1 = {"a": 1, "b": {"c": 2}}
    d2 = {"a": 1, "b": {"c": 3, "d": 4}, "e": 5}
    with tempfile.TemporaryDirectory() as tmp:
        f1 = os.path.join(tmp, "1.json")
        f2 = os.path.join(tmp, "2.json")
        with open(f1, "w", encoding="utf-8") as fh:
            json.dump(d1, fh)
        with open(f2, "w", encoding="utf-8") as fh:
            json.dump(d2, fh)
        diffs = comparar_json_files(f1, f2)

    joined = "\n".join(diffs)
    assert "+ e" in joined
    assert "~ b.c" in joined
    assert "+ b.d" in joined
