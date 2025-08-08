# Variables de entorno

El módulo `api/config.py` carga variables desde un archivo `.env` en la raíz del
repositorio utilizando [python-dotenv](https://pypi.org/project/python-dotenv/).
Las variables más relevantes son:

- `OPENAI_API_KEY`: clave para la API de OpenAI.
- `DEEPSEEK_API_KEY`: clave para la API de DeepSeek (proveedor por defecto).
- `DEMANDAS_PATH`: ruta a la carpeta con PDFs de demandas de ejemplo
  (predeterminado `data/demandas_ejemplo`).
- `JURIS_PATH`: ruta a la carpeta de jurisprudencia en PDF
  (predeterminado `data/jurisprudencia`).
- `LEGAL_CORPUS_PATH`: ruta al corpus legal en PDF
  (predeterminado `data/legal_corpus`).
- `CASOS_PATH`: ruta a la carpeta con casos en PDF
  (predeterminado `data/casos`).
- `AV_SHEETS_CREDENTIALS`: ruta al archivo de credenciales para Google Sheets.
- `AV_SHEETS_ID`: identificador de la hoja de cálculo de Google.
- `AV_SHEETS_NAME`: nombre de la pestaña de la hoja (opcional).

Crea un archivo `.env` y define las variables necesarias antes de ejecutar la
aplicación.
