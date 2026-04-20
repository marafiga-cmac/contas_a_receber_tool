"""Camada de compatibilidade para imports antigos de backend."""

from __future__ import annotations

from ..domain.csv_layouts import *  # noqa: F401,F403
from ..integrations.google_sheets import SCOPES
from ..services.cabergs_service import (
    gerar_tabela_conciliacao,
    marcar_encontrados_csv,
    processar_cabergs_arquivos,
    processar_csv_analise,
)
from ..services.capa_service import gerar_capa_nfse_por_data
from ..services.convenio_service import processar_convenio
from ..services.exports_service import (
    gerar_csv_glosa_mantida_bytes,
    gerar_csv_lancamentos_bytes,
    gerar_csv_lancamentos_unimed_bytes,
    gerar_csv_nfse_lancamentos_bytes,
    gerar_csv_recursos_bytes,
)
from ..services.nfse_service import processar_nfse
from ..services.recurso_service import compute_totals_recursos, make_recursos_df
from ..services.remessa_service import compute_totals_remessas, make_remessas_df, sum_col
from ..services.unimed_service import processar_identificacao_unimed
from ..utils.dataframe_helpers import *  # noqa: F401,F403
from ..utils.formatting import *  # noqa: F401,F403
from ..utils.formatting import (
    _ensure_len,
    _fmt_amount_csv,
    _fmt_ref_mmYYYY,
    _slugify,
)
from ..utils.normalizers import *  # noqa: F401,F403
from ..utils.normalizers import (
    _norm,
    _normalize_nf_number,
    _only_digits,
    _safe_strip_lower,
)
from ..utils.parsers import *  # noqa: F401,F403
from ..utils.parsers import (
    _as_date,
    _as_number,
    _read_csv_robusto,
)


__all__ = [name for name in globals() if not name.startswith("__")]
