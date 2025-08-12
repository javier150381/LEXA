"""Ejemplo de expresión escrita nivel MCER B1."""

import gradio as gr


def render() -> None:
    """Renderiza el contenido de la pestaña de Writing."""
    gr.Markdown("### Writing - Nivel B1")
    gr.Markdown(
        "Escribe un correo a un amigo invitándolo a pasar un fin de semana en tu ciudad (80-100 palabras)."
    )
    gr.Textbox(lines=10, label="Tu correo")
