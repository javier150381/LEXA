"""Ejemplo de producción oral nivel MCER B1."""

import gradio as gr


def render() -> None:
    """Renderiza el contenido de la pestaña de Speaking."""
    gr.Markdown("### Speaking - Nivel B1")
    gr.Markdown(
        "Describe tu ciudad favorita durante uno o dos minutos. Usa el micrófono para grabar tu respuesta."
    )
    gr.Audio(label="Graba tu respuesta", sources=["microphone"])
