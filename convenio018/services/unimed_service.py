"""Processamento do fluxo de identificação Unimed."""

from __future__ import annotations

import json
import os
from difflib import SequenceMatcher

import pandas as pd

from ..utils.normalizers import _drop_nan_only_columns, _drop_rows_without_inicio, _norm, _safe_strip_lower
from ..utils.parsers import _excel_col_idx

def processar_identificacao_unimed_para_json(
    xlsx_file,
    csv_file,
    output_dir: str = ".",
    threshold: float = 0.78,
) -> str:
    """
    Lê:
      - XLSX: cabeçalho em A5:F5 (header=4 no pandas), colunas incluem "Titular" e "Entidade"
      - CSV: colunas incluem "Nome" e "entidade"/"Entidade"

    Regra:
      - Para cada Titular (XLSX), encontra o Nome (CSV) mais similar.
      - Se score >= threshold, escreve o número da "entidade" do CSV em "Entidade" do XLSX.
      - Gera JSON estruturado com matches.
    """
    import os, json, re
    from difflib import SequenceMatcher
    import pandas as pd
    import numpy as np
    import datetime as dt

    os.makedirs(output_dir, exist_ok=True)

    # ---------- helpers ----------
    def _norm_name(s: object) -> str:
        s = _norm(s)
        s = re.sub(r"[^a-z0-9 ]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        # token sort p/ melhorar matching (ex: "JOAO DA SILVA" vs "SILVA JOAO")
        toks = [t for t in s.split(" ") if t]
        toks.sort()
        return " ".join(toks)

    def _ratio(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    def _find_col(df: pd.DataFrame, candidates: list[str], fallback_idx: int | None = None) -> str:
        cols = list(df.columns)
        norm_cols = [_norm(c) for c in cols]
        for cand in candidates:
            nc = _norm(cand)
            for i, c in enumerate(norm_cols):
                if c == nc:
                    return cols[i]
        if fallback_idx is not None and 0 <= fallback_idx < len(cols):
            return cols[fallback_idx]
        return cols[0] if cols else ""
    
    def _to_json_safe(v):
        # pandas / numpy nulos
        try:
            import pandas as pd
            if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
                return None
        except Exception:
            pass

        # Timestamp (pandas) e datetime/date -> string ISO
        try:
            import pandas as pd
            if isinstance(v, pd.Timestamp):
                # NaT
                if pd.isna(v):
                    return None
                return v.isoformat()
        except Exception:
            pass

        import datetime as dt
        if isinstance(v, (dt.datetime, dt.date)):
            return v.isoformat()

        # numpy scalars -> python scalars
        try:
            import numpy as np
            if isinstance(v, np.generic):
                return v.item()
        except Exception:
            pass

        # fallback
        return v


    # ---------- XLSX ----------
    # cabeçalho na linha 5 => header=4 (0-based)
    df_xlsx = pd.read_excel(xlsx_file, header=4, engine="openpyxl")
    df_xlsx = df_xlsx.dropna(how="all")

    col_titular = _find_col(df_xlsx, ["Titular"], fallback_idx=0)
    col_entidade_xlsx = _find_col(df_xlsx, ["Entidade"], fallback_idx=1)

    # ---------- CSV (tenta auto-sep; cai p/ ';') ----------
    try:
        df_csv = pd.read_csv(csv_file, sep=None, engine="python")
    except Exception:
        df_csv = pd.read_csv(csv_file, sep=";", engine="python")

    df_csv = df_csv.dropna(how="all")
    df_csv.columns = [str(c).replace("\ufeff", "").strip() for c in df_csv.columns]

    col_nome = _find_col(df_csv, ["Nome"], fallback_idx=0)
    col_entidade_csv = _find_col(df_csv, ["entidade", "Entidade"], fallback_idx=1)

    # prepara lista de nomes do CSV
    csv_rows = []
    for _, r in df_csv.iterrows():
        nome_raw = r.get(col_nome)
        ent = r.get(col_entidade_csv)
        nome_n = _norm_name(nome_raw)
        if nome_n:
            csv_rows.append((nome_n, str(ent).strip() if ent is not None else ""))

    # ---------- matching ----------
    out_items = []
    entidades_preenchidas = 0

    # garante coluna "Entidade" no df_xlsx
    if col_entidade_xlsx not in df_xlsx.columns:
        df_xlsx[col_entidade_xlsx] = ""

    for idx, row in df_xlsx.iterrows():
        titular_raw = row.get(col_titular)
        titular_n = _norm_name(titular_raw)

        best_score = 0.0
        best_ent = ""
        best_nome_norm = ""

        if titular_n and csv_rows:
            for nome_norm, ent in csv_rows:
                sc = _ratio(titular_n, nome_norm)
                if sc > best_score:
                    best_score = sc
                    best_ent = ent
                    best_nome_norm = nome_norm

        matched = (best_score >= float(threshold)) and (best_ent != "")
        if matched:
            df_xlsx.at[idx, col_entidade_xlsx] = best_ent
            entidades_preenchidas += 1

        out_items.append({
            "linha_xlsx": int(idx) + 6,  # aproximação visual (dados começam após header)
            "Titular": None if pd.isna(titular_raw) else str(titular_raw),
            "Entidade": str(best_ent) if matched else ("" if pd.isna(row.get(col_entidade_xlsx)) else str(row.get(col_entidade_xlsx))),
            "match": {
                "encontrou": bool(matched),
                "score": round(float(best_score), 4),
                "nome_csv_normalizado": best_nome_norm,
                "threshold": float(threshold),
            },
            "row_xlsx": {k: _to_json_safe(v) for k, v in row.to_dict().items()},
        })

    payload = {
        "meta": {
            "threshold": float(threshold),
            "total_linhas_xlsx": int(len(df_xlsx)),
            "total_linhas_csv": int(len(df_csv)),
            "entidades_preenchidas": int(entidades_preenchidas),
            "colunas": {
                "xlsx_titular": col_titular,
                "xlsx_entidade": col_entidade_xlsx,
                "csv_nome": col_nome,
                "csv_entidade": col_entidade_csv,
            },
        },
        "items": out_items,
    }

    fpath = os.path.join(output_dir, "saida_identificacao_unimed.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return fpath

