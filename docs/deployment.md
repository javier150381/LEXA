# Despliegue

Este proyecto incluye un contenedor Docker con Gunicorn y Uvicorn para servir la aplicación FastAPI.

## Construir y ejecutar localmente

```bash
docker-compose up --build
```

La API quedará disponible en `http://localhost:8000`.

## Render

1. Cree un nuevo servicio de "Web Service".
2. Conecte el repositorio y configure el despliegue automático.
3. Establezca el comando de inicio:
   ```
   gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
4. Configure la variable `PORT` en `8000` si es necesario.

## Railway

1. Importe el repositorio como nuevo proyecto.
2. En la pestaña de servicio, defina el puerto `8000` y el comando de inicio como en Render.
3. Railway construirá la imagen automáticamente con el `Dockerfile` incluido.

## Fly.io

1. Instale la CLI de Fly y ejecute `fly launch`.
2. Acepte el `Dockerfile` existente y configure el puerto `8080` interno apuntando a `8000`.
3. Despliegue con `fly deploy`.

## Servidor propio

1. Copie el repositorio al servidor.
2. Construya la imagen:
   ```bash
   docker build -t lexa-app .
   ```
3. Ejecute el contenedor:
   ```bash
   docker run -d -p 8000:8000 lexa-app
   ```
