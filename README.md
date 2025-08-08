# LEXA

## Instalación

Instala las dependencias necesarias:

```bash
pip install fastapi uvicorn
```

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
