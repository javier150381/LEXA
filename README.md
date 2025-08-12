# LEXA

Aplicación de práctica para habilidades de inglés nivel MCER B1. Incluye ejercicios básicos de Listening, Speaking, Reading, Writing, Grammar y Vocabulary.

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

## Uso

Inicia la interfaz web con Gradio:

```bash
python app.py
```

La aplicación se abrirá en `http://127.0.0.1:7860`.

## Servicio de WhatsApp

Para enviar los resultados de los ejercicios por WhatsApp se utiliza la
API de Twilio.  Es necesario configurar las siguientes variables de
entorno:

- `TWILIO_ACCOUNT_SID`: identificador de la cuenta en Twilio.
- `TWILIO_AUTH_TOKEN`: token de autenticación de Twilio.
- `TWILIO_WHATSAPP_NUMBER`: número telefónico de Twilio habilitado para
  WhatsApp (por ejemplo, `whatsapp:+14155238886`).

Uso básico:

```python
from src.whatsapp_service import send_grammar

send_grammar("Buen trabajo", "+34999999999")
```

## Errores típicos nivel B1

Algunos errores frecuentes en aprendientes de nivel B1 de inglés son:

- `goed` → `went`
- `writed` → `wrote`
- `comed` → `came` / `ate`
