from lib import demandas


def test_llm_provider_switch(monkeypatch):
    monkeypatch.setattr(demandas.tokens, "init_db", lambda: None)
    monkeypatch.setattr(demandas.tokens, "get_credit", lambda: 1)
    monkeypatch.setattr(demandas, "get_deepseek_api_key", lambda: "deep")
    monkeypatch.setenv("OPENAI_API_KEY", "open")

    demandas._llm = None
    demandas._llm_provider = None
    ctx = demandas.default_context

    ctx.llm_provider = "deepseek"
    llm = demandas.get_llm()
    assert llm.model_name == "deepseek-chat"

    ctx.llm_provider = "openai"
    llm = demandas.get_llm()
    assert llm.model_name == "gpt-4o-mini"

    ctx.llm_provider = "deepseek"
    demandas._llm = None
    demandas._llm_provider = None

