"""Parsers auxiliares do projeto."""

from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any, Optional

import pandas as pd

def _as_date(cell: Any) -> Optional[date]:
    if cell is None or str(cell).strip() == "": return None
    s = str(cell).strip()
    for fmt in ("%d/%m/%Y","%d-%m-%Y","%Y-%m-%d"):
        try: return datetime.strptime(s, fmt).date()
        except ValueError: pass
    try:
        n = float(s.replace(",", "."))
        base_ord = date(1899,12,30).toordinal()
        return date.fromordinal(base_ord + int(n))
    except Exception:
        return None

def _as_number(cell: Any) -> Optional[float]:
    if cell is None or str(cell).strip() == "": return None
    s = str(cell).strip()
    for sym in ["R$","$"]: s = s.replace(sym,"")
    s = s.replace(" ","")
    if "," in s and "." in s: s = s.replace(".","").replace(",",".")
    elif "," in s: s = s.replace(",",".")
    try: return float(s)
    except ValueError:
        m = re.search(r"-?\d[\d\.,]*", s)
        return _as_number(m.group(0)) if m else None


def _excel_col_idx(col_letters: str) -> int:
    """A=1, B=2 ..."""
    col_letters = col_letters.upper().strip()
    n = 0
    for ch in col_letters:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _read_csv_robusto(uploaded_file) -> pd.DataFrame:
    """Lê CSV com fallback de encoding e delimitador, sem depender de sep=None."""
    if uploaded_file is None:
        return pd.DataFrame()

    raw = uploaded_file.read()
    if not raw:
        return pd.DataFrame()

    # tenta decodificar
    text = None
    last_err = None
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            text = raw.decode(enc)
            break
        except Exception as e:
            last_err = e
    if text is None:
        raise RuntimeError(f"Falha ao decodificar CSV: {last_err}")

    sample = text[:20000]
    # tenta sniffer
    sniffer_delim = None
    try:
        sniffer_delim = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"]).delimiter
    except Exception:
        sniffer_delim = None

    counts = {
        ";": sample.count(";"),
        ",": sample.count(","),
        "\t": sample.count("\t"),
        "|": sample.count("|"),
    }
    best_by_count = max(counts, key=counts.get)

    seps_to_try = []
    if sniffer_delim:
        seps_to_try.append(sniffer_delim)
    seps_to_try.append(best_by_count)
    for s in [";", ",", "\t", "|"]:
        if s not in seps_to_try:
            seps_to_try.append(s)

    df = None
    last_read_err = None
    for sep in seps_to_try:
        try:
            df_try = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
            # se ficou 1 coluna só e o sep aparece bastante, tenta próximo
            if df_try.shape[1] == 1 and counts.get(sep, 0) > 0:
                df = df_try  # guarda, mas tenta outra
                continue
            df = df_try
            break
        except Exception as e:
            last_read_err = e
            df = None

    if df is None:
        raise RuntimeError(f"Falha ao ler CSV. Último erro: {last_read_err}")

    # remove colunas lixo comuns
    df = df.loc[:, [
        c for c in df.columns
        if not str(c).lower().startswith("unnamed")
        and not str(c).startswith("\ufeff")
    ]]

    return df

