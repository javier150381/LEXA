"""Ejemplo sencillo de comprensión auditiva nivel MCER B1."""

import gradio as gr


def render() -> None:
    """Renderiza el contenido de la pestaña de Listening."""
    gr.Markdown("### Listening - Nivel B1")
    gr.Markdown(
        "Escucha un breve diálogo sobre planes de viaje y responde la pregunta."
    )
    gr.Audio(label="Audio del ejercicio", type="filepath")
    gr.Textbox(label="¿A dónde van de vacaciones los hablantes?")
