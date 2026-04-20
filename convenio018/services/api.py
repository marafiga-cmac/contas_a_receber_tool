"""API de serviços (regras de negócio) usada pela UI."""

from __future__ import annotations

from ..domain.convenio_rules import get_convenios_por_unidade
from ..ui.forms.convenio_form import render_form
from ..ui.reports.capa_report import render_relatorio_capa
from ..ui.reports.nfse_report import render_relatorio_nfse_para_impressao
from ..ui.reports.recursos_report import render_relatorio_recursos
from ..ui.reports.remessas_report import render_relatorio_remessas
from .cabergs_service import (
    gerar_tabela_conciliacao,
    marcar_encontrados_csv,
    processar_cabergs_arquivos,
    processar_csv_analise,
)
from .capa_service import gerar_capa_nfse_por_data
from .convenio_service import processar_convenio
from .exports_service import gerar_csv_glosa_mantida_bytes, gerar_csv_lancamentos_unimed_bytes
from .nfse_service import processar_nfse
from .recurso_service import compute_totals_recursos, make_recursos_df
from .remessa_service import compute_totals_remessas, make_remessas_df
from .unimed_service import processar_identificacao_unimed
from .ipe_service import extrair_dados_demonstrativo_ipe
from ..database.db_manager import save_dataframe_to_sqlite

__all__ = [
    "compute_totals_recursos",
    "compute_totals_remessas",
    "gerar_capa_nfse_por_data",
    "gerar_csv_glosa_mantida_bytes",
    "gerar_csv_lancamentos_unimed_bytes",
    "gerar_tabela_conciliacao",
    "get_convenios_por_unidade",
    "make_recursos_df",
    "make_remessas_df",
    "marcar_encontrados_csv",
    "processar_cabergs_arquivos",
    "processar_convenio",
    "processar_csv_analise",
    "processar_identificacao_unimed",
    "extrair_dados_demonstrativo_ipe",
    "processar_nfse",
    "render_form",
    "render_relatorio_capa",
    "render_relatorio_nfse_para_impressao",
    "render_relatorio_recursos",
    "render_relatorio_remessas",
    "save_dataframe_to_sqlite",
]
