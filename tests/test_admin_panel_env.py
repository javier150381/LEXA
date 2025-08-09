import types
import importlib
import sys
from pathlib import Path


def _load_app(monkeypatch):
    # Provide a dummy tkcalendar module if missing
    if "tkcalendar" not in sys.modules:
        dummy = types.SimpleNamespace(DateEntry=object)
        monkeypatch.setitem(sys.modules, "tkcalendar", dummy)
    root_path = str(Path(__file__).resolve().parents[1])
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    return importlib.reload(importlib.import_module("ui.app"))


def _setup_common(monkeypatch):
    app_module = _load_app(monkeypatch)

    # Patch token and threading dependencies
    monkeypatch.setattr(app_module.tokens, "init_db", lambda *a, **k: None)
    monkeypatch.setattr(app_module.tokens, "get_tokens", lambda *a, **k: 0)
    monkeypatch.setattr(app_module.tokens, "get_credit", lambda *a, **k: 0)
    monkeypatch.setattr(app_module.threading, "Thread", lambda *a, **k: types.SimpleNamespace(start=lambda: None))
    monkeypatch.setattr(app_module.AbogadoVirtualApp, "show_progress_dialog", lambda self: None)
    monkeypatch.setattr(app_module.AbogadoVirtualApp, "ensure_license_email", lambda self: None)
    monkeypatch.setattr(app_module.ttk, "Style", lambda *a, **k: types.SimpleNamespace(configure=lambda *a, **k: None))

    # Dummy Tk elements
    class DummyVar:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value
        def get(self):
            return self.value
    monkeypatch.setattr(app_module.tk, "StringVar", DummyVar)
    monkeypatch.setattr(app_module.tk, "DoubleVar", DummyVar)

    class DummyWidget:
        def __init__(self, *a, **k):
            pass
        def pack(self, *a, **k):
            pass
        def grid(self, *a, **k):
            pass
        def columnconfigure(self, *a, **k):
            pass
        def rowconfigure(self, *a, **k):
            pass
        def bind(self, *a, **k):
            pass
        def config(self, *a, **k):
            pass
        def winfo_manager(self):
            return False
    for name in ["LabelFrame", "Frame", "Label", "Entry", "Button"]:
        monkeypatch.setattr(app_module.tk, name, DummyWidget)

    # Minimal root
    fake_root = types.SimpleNamespace(
        title=lambda *a, **k: None,
        geometry=lambda *a, **k: None,
        configure=lambda *a, **k: None,
        option_add=lambda *a, **k: None,
        bind=lambda *a, **k: None,
        protocol=lambda *a, **k: None,
    )

    # Use real build_pestaña_id_clave within simplified build_interface
    original_build = app_module.AbogadoVirtualApp.build_pestaña_id_clave
    def fake_build_interface(self):
        parent = DummyWidget()
        original_build(self, parent)
    monkeypatch.setattr(app_module.AbogadoVirtualApp, "build_interface", fake_build_interface)

    return app_module, fake_root


def test_admin_panel_hidden_without_env(monkeypatch):
    monkeypatch.delenv("LEXA_SHOW_ADMIN", raising=False)
    app_module, root = _setup_common(monkeypatch)
    app = app_module.AbogadoVirtualApp(root)
    assert not hasattr(app, "frame_admin")


def test_admin_panel_visible_with_env(monkeypatch):
    monkeypatch.setenv("LEXA_SHOW_ADMIN", "1")
    app_module, root = _setup_common(monkeypatch)
    app = app_module.AbogadoVirtualApp(root)
    assert hasattr(app, "frame_admin")


def test_load_email_refresh(monkeypatch):
    monkeypatch.delenv("LEXA_SHOW_ADMIN", raising=False)
    app_module, root = _setup_common(monkeypatch)
    original = app_module.default_context.config_global.get("license_email")
    try:
        app_module.default_context.config_global["license_email"] = "a@example.com"
        app = app_module.AbogadoVirtualApp(root)
        assert app.var_id_email.get() == "a@example.com"
        app_module.default_context.config_global["license_email"] = "b@example.com"
        app.on_load_id_email()
        assert app.var_id_email.get() == "b@example.com"
    finally:
        if original is None:
            app_module.default_context.config_global.pop("license_email", None)
        else:
            app_module.default_context.config_global["license_email"] = original
