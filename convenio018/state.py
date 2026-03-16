"""Chaves compartilhadas do session_state do Streamlit."""

from __future__ import annotations

from .config import DEFAULT_CLIENT_SECRET, DEFAULT_OUTPUT_DIR, DEFAULT_UNIDADE

SESSION_DEFAULTS = {
    "unidade": DEFAULT_UNIDADE,
    "selected_convenio": None,
    "selected_date": None,
    "remessas_df": None,
    "remessas_totais": None,
    "recursos_df": None,
    "recursos_totais": None,
    "json_path": None,
    "modelo_csv": None,
    "output_dir": DEFAULT_OUTPUT_DIR,
    "logo_data_uri": None,
    "logo_path": None,
    "csv_prefs": None,
    "csv_convenio_overrides": None,
    "client_secret_path": DEFAULT_CLIENT_SECRET,
}
