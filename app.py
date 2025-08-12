"""Interfaz de práctica con pestañas para distintas habilidades MCER B1."""

import gradio as gr

from skills import grammar, listening, reading, speaking, vocabulary, writing

MODULES = [
    ("Listening", listening.render),
    ("Speaking", speaking.render),
    ("Reading", reading.render),
    ("Writing", writing.render),
    ("Grammar", grammar.render),
    ("Vocabulary", vocabulary.render),
]


def build_demo() -> gr.Blocks:
    """Crea la aplicación de Gradio con una pestaña por habilidad."""
    with gr.Blocks() as demo:
        gr.Markdown("# Práctica de inglés - Nivel B1")
        for title, render in MODULES:
            with gr.Tab(title):
                render()
    return demo


demo = build_demo()

if __name__ == "__main__":
    demo.launch()
