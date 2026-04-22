"""Transformação e totais do relatório de recursos."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import pandas as pd

from ..domain.csv_layouts import RECURSOS_COLUMNS
from ..utils.parsers import _as_number

def make_recursos_df(items: List[Dict[str, Any]], data_pagamento: date) -> pd.DataFrame:
    registros = []
    alvo_iso = data_pagamento.isoformat()

    for it in items:
        if it.get("Data Recurso") != alvo_iso:
            continue

        registros.append({
            "Nº Remessa": it.get("Nº Remessa"),
            "Ref.": it.get("Ref."),
            "Nº NF": it.get("NF recurso") or it.get("Nº NF"),  # exibe sempre uma NF
            "Valor recursado": it.get("Valor recursado"),
            "Valor pago": it.get("Valor pago"),
            "Imposto": it.get("Imposto"),
            "Glosa mantida": it.get("Glosa mantida"),
        })

    if not registros:
        return pd.DataFrame(columns=[
            "Nº Remessa","Ref.","Nº NF",
            "Valor recursado","Valor pago",
            "Imposto","Glosa mantida",
        ])

    df = pd.DataFrame(registros)

    for col in ["Valor recursado","Valor pago","Imposto","Glosa mantida"]:
        if col in df.columns:
            df[col] = df[col].apply(_as_number)

    return df

def sum_col(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns: return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())

def compute_totals_remessas(df: pd.DataFrame) -> Dict[str, float]:
    return {
        "total_envio_xml": sum_col(df,"Valor envio XML - Remessa"),
        "total_pgto": sum_col(df,"Valor pgto"),
        "total_glosado": sum_col(df,"Valor glosado"),
        "total_imposto": sum_col(df,"Imposto"),
        "total_glosa_mantida": sum_col(df,"Glosa mantida"),
        "total_pago": sum_col(df,"Valor pgto"),
    }

def compute_totals_recursos(df: pd.DataFrame) -> Dict[str, float]:
    return {
        "total_recursado": sum_col(df,"Valor recursado") if "Valor recursado" in df.columns else 0.0,
        "total_imposto": sum_col(df,"Imposto"),
        "total_glosa_mantida": sum_col(df,"Glosa mantida"),
        "total_pago": sum_col(df,"Valor pago") if "Valor pago" in df.columns else sum_col(df,"Valor pgto"),
    }

