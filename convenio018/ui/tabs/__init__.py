"""Aba(s) do Streamlit.

Cada arquivo aqui contém apenas o layout e chamadas para o backend.
"""

from .tab_convenios import render as render_convenios
from .tab_remessas import render as render_remessas
from .tab_recursos import render as render_recursos
from .tab_nfse import render as render_nfse
from .tab_capa import render as render_capa
from .tab_unimed import render as render_unimed
from .tab_glosa_mantida import render as render_glosa_mantida

__all__ = [
    "render_convenios",
    "render_remessas",
    "render_recursos",
    "render_nfse",
    "render_capa",
    "render_unimed",
    "render_glosa_mantida",
]
