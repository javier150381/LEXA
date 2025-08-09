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

## Interfaz web con Gradio

Para interactuar con una versión simplificada de LEXA mediante una interfaz
gráfica, ejecuta:

```bash
PYTHONPATH=. python ui/gradio_app.py
```

Esto iniciará un servidor local de Gradio accesible en
`http://127.0.0.1:7860` donde podrás clasificar casos y validar requisitos.

Por defecto, la interfaz se lanza con `share=True`, lo que genera un enlace
público de Gradio. En entornos donde se requiera evitar la exposición externa,
puedes desactivar esta opción estableciendo la variable de entorno
`DISABLE_GRADIO_SHARE=1` antes de ejecutar el comando anterior.
