# LEXA

## Instalación

1. Crea un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # En Windows usa `venv\\Scripts\\activate`
```

2. Instala las dependencias necesarias:

```bash
pip install -r requirements.txt
```

El archivo `requirements.txt` contiene todas las dependencias necesarias para ejecutar la aplicación localmente.

## Ejecución del servidor

Inicia el servidor de desarrollo:

```bash
uvicorn api.main:app --reload
```

## Verificación

Después de iniciar el servidor, abre en tu navegador o consulta con `curl` la URL:

```
http://localhost:8000
```

Deberías recibir una respuesta del servicio.
