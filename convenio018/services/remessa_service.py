"""Transformação e totais do relatório de remessas."""

from __future__ import annotations

import pandas as pd

from ..domain.csv_layouts import REMESSAS_COLUMNS

def make_remessas_df(items: List[Dict[str, Any]], selected_date: date) -> pd.DataFrame:
    sel_iso = selected_date.isoformat() if selected_date else None
    base = []
    for x in items:
        d_rem = x.get("Data Remessa"); vpgto = _as_number(x.get("Valor pgto"))
        if d_rem == sel_iso and vpgto is not None and vpgto != 0: base.append(x)
    df = pd.DataFrame(base)
    for col in REMESSAS_COLUMNS:
        if col not in df.columns: df[col] = None
    df = df[REMESSAS_COLUMNS]
    for c in ["Valor envio XML - Remessa","Valor pgto","Valor glosado","Imposto","Glosa mantida"]:
        df[c] = df[c].apply(_as_number)
    return df

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

