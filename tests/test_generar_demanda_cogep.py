import lib.demandas as dem


def test_generar_demanda_cogep_placeholders():
    ctx = dem.DemandasContext()
    texto = dem.generar_demanda_cogep(ctx)
    assert "[HECHOS]" in texto
    assert "DESIGNACION_JUZGADOR" in ctx.pending_placeholders
