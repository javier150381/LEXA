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

Si ya habías instalado los requerimientos, vuelve a ejecutar `pip install -r requirements.txt` para instalar la nueva dependencia `pypdf`.

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

## Indexación de documentos

El módulo `lib/indexing.py` introduce la función `crear_indice`, que crea un
almacenamiento vectorial a partir de una lista de documentos. De forma
predeterminada se utiliza `FAISS`, pero puede activarse el backend de Pinecone
estableciendo el parámetro `usar_pinecone=True`.

Cuando se utiliza Pinecone es necesario proporcionar las credenciales de
autenticación mediante los parámetros `api_key`, `environment` e `index_name`,
los cuales corresponden a `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT` y
`PINECONE_INDEX_NAME` respectivamente.
