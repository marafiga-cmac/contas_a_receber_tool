"""Camada de compatibilidade para imports antigos de frontend."""

from __future__ import annotations

from ..domain.convenio_rules import (
    CONVENIOS_CMAC,
    CONVENIOS_CMAP,
    CMAC_GLOSA_TO_3301,
    CMAC_GLOSA_TO_3303,
    CSV_HEADER_FIRST_ROW,
    DEPOSITO_SUBCONTA_BANCO,
    get_convenios_por_unidade,
)
from ..ui.forms.convenio_form import render_form
from ..ui.reports.capa_report import render_relatorio_capa
from ..ui.reports.nfse_report import render_relatorio_nfse_para_impressao
from ..ui.reports.recursos_report import render_relatorio_recursos
from ..ui.reports.remessas_report import render_relatorio_remessas
from ..ui.reports.print_templates import LOGO_PATH

__all__ = [
    "CONVENIOS_CMAC",
    "CONVENIOS_CMAP",
    "CMAC_GLOSA_TO_3301",
    "CMAC_GLOSA_TO_3303",
    "CSV_HEADER_FIRST_ROW",
    "DEPOSITO_SUBCONTA_BANCO",
    "LOGO_PATH",
    "get_convenios_por_unidade",
    "render_form",
    "render_relatorio_capa",
    "render_relatorio_nfse_para_impressao",
    "render_relatorio_recursos",
    "render_relatorio_remessas",
]
