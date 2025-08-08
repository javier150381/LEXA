import types
import ui.app as app_mod
from ui.app import AbogadoVirtualApp, messagebox

class DummyListbox:
    def __init__(self, items, selected):
        self.items = items
        self.selected = selected
    def curselection(self):
        return self.selected
    def get(self, index):
        return self.items[index]

class DummyVar:
    def __init__(self, value=""):
        self._value = value
    def get(self):
        return self._value

class DummyStatus:
    def __init__(self):
        self.value = ""
    def set(self, value):
        self.value = value


def test_on_eliminar_juris_pdf_multiple(monkeypatch):
    dummy = types.SimpleNamespace()
    dummy.list_juris = DummyListbox(["a.pdf", "b.pdf", "c.pdf"], (0, 2))
    dummy.status_text = DummyStatus()
    dummy.refresh_list_juris = lambda: setattr(dummy, "refreshed", True)
    dummy.update_info_label = lambda: None

    calls = []
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)
    def fake_eliminar(nombre):
        calls.append(nombre)
        return f"ok {nombre}"
    monkeypatch.setattr(
        app_mod, "eliminar_jurisprudencia_pdf", fake_eliminar
    )

    AbogadoVirtualApp.on_eliminar_juris_pdf(dummy)
    assert calls == ["a.pdf", "c.pdf"]
    assert dummy.status_text.value == "ok a.pdf\nok c.pdf"
    assert dummy.refreshed


def test_on_eliminar_pdf_caso_multiple(monkeypatch):
    dummy = types.SimpleNamespace()
    dummy.caso_seleccionado = DummyVar("CASO")
    dummy.list_pdfs_caso = DummyListbox(["a.pdf", "b.pdf", "c.pdf"], (1, 2))
    dummy.status_text = DummyStatus()
    dummy.refresh_list_pdfs_caso = lambda nombre: setattr(dummy, "refreshed_pdfs", nombre)
    dummy.refresh_list_casos = lambda: setattr(dummy, "refreshed_casos", True)

    calls = []
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)
    def fake_eliminar(doc, nombre):
        calls.append((doc, nombre))
        return f"ok {doc} {nombre}"
    monkeypatch.setattr(
        app_mod, "eliminar_pdf_de_caso", fake_eliminar
    )

    AbogadoVirtualApp.on_eliminar_pdf_caso(dummy)
    assert calls == [("b.pdf", "CASO"), ("c.pdf", "CASO")]
    assert dummy.status_text.value == "ok b.pdf CASO\nok c.pdf CASO"
    assert dummy.refreshed_pdfs == "CASO"
    assert dummy.refreshed_casos


def test_on_eliminar_pdf_area_multiple(monkeypatch):
    dummy = types.SimpleNamespace()
    dummy.var_area = DummyVar("AREA")
    dummy.list_area_pdfs = DummyListbox(["a.pdf", "b.pdf"], (0, 1))
    dummy.status_text = DummyStatus()
    dummy.refresh_list_areas = lambda: setattr(dummy, "refreshed", True)

    calls = []
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)
    def fake_eliminar(doc, nombre):
        calls.append((doc, nombre))
        return f"ok {doc} {nombre}"
    monkeypatch.setattr(
        app_mod, "eliminar_pdf_de_area", fake_eliminar
    )

    AbogadoVirtualApp.on_eliminar_pdf_area(dummy)
    assert calls == [("a.pdf", "AREA"), ("b.pdf", "AREA")]
    assert dummy.status_text.value == "ok a.pdf AREA\nok b.pdf AREA"
    assert dummy.refreshed
