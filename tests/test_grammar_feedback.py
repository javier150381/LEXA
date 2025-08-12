from src.feedback import get_feedback
from src.speaking import evaluate as speak_eval
from src.writing import evaluate as write_eval


def test_past_simple_rule():
    msgs = get_feedback("I didn't went to school")
    assert any("didn't" in m for m in msgs)


def test_preposition_rule():
    msgs = write_eval("I will go in Monday")
    assert any("days of the week" in m for m in msgs)


def test_third_person_rule_via_speaking():
    msgs = speak_eval("He go to work")
    assert any("third person" in m for m in msgs)
