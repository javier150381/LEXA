import pytest

# Skip tests if FastAPI or API app is not available
fastapi = pytest.importorskip("fastapi")
try:
    from src.api import app
except Exception:
    pytest.skip("FastAPI app not available", allow_module_level=True)

from fastapi.testclient import TestClient

client = TestClient(app)


def test_generar_endpoint():
    response = client.post("/generar", json={"prompt": "hola"})
    assert response.status_code == 200
    data = response.json()
    assert "resultado" in data or "result" in data


def test_clasificar_endpoint():
    response = client.post("/clasificar", json={"texto": "documento"})
    assert response.status_code == 200
    data = response.json()
    assert "categoria" in data or "classification" in data
