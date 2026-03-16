"""Normalização de texto, cabeçalhos e chaves de conciliação."""

from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

def _drop_nan_only_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove colunas onde todos os valores são vazios/NaN/'nan'."""
    if df is None or df.empty:
        return df

    def _is_empty_cell(x) -> bool:
        if x is None:
            return True
        try:
            if pd.isna(x):
                return True
        except Exception:
            pass
        s = str(x).strip()
        return s == "" or s.lower() == "nan"

    keep = []
    for col in df.columns:
        vals = df[col].tolist()
        keep.append(not all(_is_empty_cell(v) for v in vals))
    return df.loc[:, keep]


def _drop_rows_without_inicio(df: pd.DataFrame, col_name: str = "Início") -> pd.DataFrame:
    """Remove linhas onde a coluna 'Início' está vazia/NaN/'nan'."""
    if df is None or df.empty:
        return df
    # encontra coluna por igualdade case-insensitive
    real_col = None
    tgt = (col_name or "").strip().lower()
    for c in df.columns:
        if str(c).strip().lower() == tgt:
            real_col = c
            break
    if real_col is None:
        return df

    def _has_value(x) -> bool:
        if x is None:
            return False
        try:
            if pd.isna(x):
                return False
        except Exception:
            pass
        s = str(x).strip()
        return not (s == "" or s.lower() == "nan")

    mask = df[real_col].apply(_has_value)
    return df.loc[mask].reset_index(drop=True)


def _dedupe_headers(cols) -> list[str]:
    """Garante nomes únicos de colunas, tratando None/''/'nan' como vazios."""
    used: dict[str, int] = {}
    out: list[str] = []
    for i, c in enumerate(list(cols or [])):
        base = "" if c is None else str(c).strip()
        if base == "" or base.lower() == "nan":
            base = f"COL_{i}"
        n = used.get(base, 0)
        name = f"{base}_{n}" if n > 0 else base
        used[base] = n + 1
        out.append(name)
    return out


def _norm(s: Any) -> str:
    import unicodedata
    if s is None: return ""
    s = str(s)
    s2 = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s2 = re.sub(r"\s+", " ", s2)
    return s2.strip().lower()


def _split_imposto_glosa(cell: Any) -> (Optional[float], Optional[float]):
    if cell is None or str(cell).strip() == "": return None, None
    s = str(cell)
    imp = glo = None
    m_imp = re.search(r"imposto[^0-9\-]*(-?\d[\d\.,]*)", s, flags=re.I)
    m_glo = re.search(r"glosa\s*mantida[^0-9\-]*(-?\d[\d\.,]*)", s, flags=re.I)
    if m_imp: imp = _as_number(m_imp.group(1))
    if m_glo: glo = _as_number(m_glo.group(1))
    if imp is None or glo is None:
        nums = re.findall(r"-?\d[\d\.,]*", s)
        if len(nums) >= 2:
            if imp is None: imp = _as_number(nums[0])
            if glo is None: glo = _as_number(nums[1])
    return imp, glo


def _normalize_nf_number(x):
    s = "" if x is None else str(x)
    return "".join(ch for ch in s if ch.isdigit())


def _safe_strip_lower(x) -> str:
    return str(x or "").strip().lower()


def _only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def _norm_guia_tiss_tabela1(v) -> str:
    """Tabela 1 (XLS): se começar com 0, desconsidera zeros à esquerda."""
    s = "" if v is None else str(v).strip()
    s = _only_digits(s)
    # remove zeros à esquerda (regra)
    s = s.lstrip("0")
    return s

def _norm_guia_tiss_tabela2(v) -> str:
    """Tabela 2 (CSV): remove 3 primeiros caracteres e o último, depois mantém só dígitos."""
    s = "" if v is None else str(v).strip()
    if len(s) >= 5:
        s = s[3:-1]
    else:
        s = ""
    s = _only_digits(s)
    return s

def _find_col_case_insensitive(df: pd.DataFrame, target: str) -> str | None:
    if df is None or df.empty:
        return None
    tgt = (target or "").strip().lower()
    for c in df.columns:
        if str(c).strip().lower() == tgt:
            return c
    return None

