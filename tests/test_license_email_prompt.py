import types

import ui.app as app_module


def test_tabs_disabled_until_email_saved(monkeypatch, tmp_path):
    # Use temporary locations for the tokens database
    monkeypatch.setattr(app_module.tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(app_module.tokens, "TOKENS_DB", tmp_path / "tokens.db")

    # Minimal fake root
    fake_root = types.SimpleNamespace(
        title=lambda *a, **k: None,
        geometry=lambda *a, **k: None,
        configure=lambda *a, **k: None,
        option_add=lambda *a, **k: None,
        bind=lambda *a, **k: None,
        protocol=lambda *a, **k: None,
    )

    # Avoid building full UI elements
    monkeypatch.setattr(
        app_module.ttk,
        "Style",
        lambda *a, **k: types.SimpleNamespace(configure=lambda *a, **k: None),
    )
    monkeypatch.setattr(
        app_module.threading,
        "Thread",
        lambda *a, **k: types.SimpleNamespace(start=lambda: None),
    )
    monkeypatch.setattr(app_module.AbogadoVirtualApp, "show_progress_dialog", lambda self: None)

    # Dummy variable classes
    class DummyVar:
        def __init__(self, value=None):
            self._value = value

        def set(self, value):
            self._value = value

        def get(self):
            return self._value

    monkeypatch.setattr(app_module.tk, "StringVar", DummyVar)
    monkeypatch.setattr(app_module.tk, "DoubleVar", DummyVar)

    # Fake notebook to track tab states
    class DummyNotebook:
        def __init__(self):
            self.states = {}
            self.selected = None

        def index(self, arg):
            return 3 if arg == "end" else 0

        def tab(self, idx, state=None):
            if state is not None:
                self.states[idx] = state
            return {"state": self.states.get(idx, "normal")}

        def select(self, idx):
            self.selected = idx

    def fake_build_interface(self):
        self.notebook = DummyNotebook()
        self.var_license_email = DummyVar("")
        self.lbl_license_status = types.SimpleNamespace(config=lambda *a, **k: None)
        self.entry_license_email = types.SimpleNamespace(config=lambda *a, **k: None)

    monkeypatch.setattr(app_module.AbogadoVirtualApp, "build_interface", fake_build_interface)

    warnings = []
    monkeypatch.setattr(app_module.messagebox, "showwarning", lambda *a, **k: warnings.append(1))
    monkeypatch.setattr(app_module.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(app_module.messagebox, "showerror", lambda *a, **k: None)

    saved_config = {}
    monkeypatch.setattr(app_module.demandas, "guardar_config", lambda cfg: saved_config.update(cfg))

    original_config = app_module.default_context.config_global.copy()
    app_module.default_context.config_global.pop("license_email", None)

    try:
        app = app_module.AbogadoVirtualApp(fake_root)
        # Warning shown and other tabs disabled
        assert warnings
        assert app.notebook.states.get(1) == "disabled"
        assert app.notebook.states.get(2) == "disabled"
        assert app.notebook.selected == 0

        # User enters email and saves
        app.var_license_email.set("user@example.com")
        app.on_save_license_email()
        assert saved_config["license_email"] == "user@example.com"
        for idx in range(app.notebook.index("end")):
            assert app.notebook.tab(idx)["state"] == "normal"
    finally:
        app_module.default_context.config_global = original_config

