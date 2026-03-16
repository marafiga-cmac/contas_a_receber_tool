"""API de serviços (regras de negócio) usada pela UI.

Neste refactor, para minimizar risco, nós reaproveitamos a implementação
existente (código legado) e expomos uma interface estável.

Quando for evoluindo o projeto, o ideal é ir migrando funções do
`*_legacy.py` para módulos novos, mantendo esta API como "contrato".
"""

from __future__ import annotations

# Back-end (Sheets + parsing/geração de arquivos)
from .backend_legacy import (
    processar_convenio_para_json,
    processar_nfse_para_json,
    gerar_capa_nfse_por_data,
    make_remessas_df,
    make_recursos_df,
    compute_totals_remessas,
    compute_totals_recursos,
    processar_identificacao_unimed_para_json,
    gerar_csv_lancamentos_unimed_bytes,
    processar_cabergs_arquivos,
    processar_csv_analise,
    marcar_encontrados_csv,
    gerar_csv_glosa_mantida_bytes,
)

# Front-end "helpers" (HTML/CSV/relatórios)
from .frontend_legacy import (
    render_form,
    render_relatorio_remessas,
    render_relatorio_recursos,
    get_convenios_por_unidade,
    render_relatorio_nfse_para_impressao,
    render_relatorio_capa,
)

__all__ = [
    # backend
    "processar_convenio_para_json",
    "processar_nfse_para_json",
    "gerar_capa_nfse_por_data",
    "make_remessas_df",
    "make_recursos_df",
    "compute_totals_remessas",
    "compute_totals_recursos",
    "processar_identificacao_unimed_para_json",
    "gerar_csv_lancamentos_unimed_bytes",
    "processar_cabergs_arquivos",
    "processar_csv_analise",
    "marcar_encontrados_csv",
    "gerar_csv_glosa_mantida_bytes",
    # frontend
    "render_form",
    "render_relatorio_remessas",
    "render_relatorio_recursos",
    "get_convenios_por_unidade",
    "render_relatorio_nfse_para_impressao",
    "render_relatorio_capa",
]
