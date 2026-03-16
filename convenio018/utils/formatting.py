"""Formatação de referência, CSV e nomes de arquivo."""

from __future__ import annotations

import re
from datetime import date, datetime

from ..domain.csv_layouts import CSV_COLS

def _ensure_len(row, n=CSV_COLS):
    row = list(row)
    if len(row) < n: row += [""] * (n - len(row))
    elif len(row) > n: row = row[:n]
    return row

def _fmt_ref_mmYYYY(ref_raw):
    import unicodedata
    s_raw = str(ref_raw or "").strip()
    if not s_raw: return ""
    s = unicodedata.normalize("NFD", s_raw).lower()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace(".","").replace("_"," ").strip()
    m = re.search(r"(\d{1,2})[\/\-\s\.](\d{2,4})", s)
    if m:
        mm = int(m.group(1)); yy = m.group(2); yyyy = int(yy) + 2000 if len(yy)==2 else int(yy)
        if 1 <= mm <= 12: return f"{mm:02d}/{yyyy}"
    month_map = {"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12,
                 "feb":2,"apr":4,"may":5,"aug":8,"sep":9,"oct":10,"dec":12}
    m = re.search(r"([a-z]{3,4})[\/\-\s]+(\d{2,4})", s)
    if m:
        mon = m.group(1)[:3]; yy = m.group(2)
        if mon in month_map:
            mm = month_map[mon]; yyyy = int(yy) + 2000 if len(yy)==2 else int(yy)
            return f"{mm:02d}/{yyyy}"
    m = re.search(r"(\d{4})[\/\-\s\.](\d{1,2})", s)
    if m:
        yyyy = int(m.group(1)); mm = int(m.group(2))
        if 1 <= mm <= 12: return f"{mm:02d}/{yyyy}"
    return s_raw

def _fmt_amount_csv(v):
    if v is None: return "0"
    try: fv = float(v)
    except Exception:
        s = str(v).strip().replace("R$","").replace(" ","")
        if "," in s and "." in s: s = s.replace(".","").replace(",",".")
        elif "," in s: s = s.replace(",",".")
        try: fv = float(s)
        except Exception: return "0"
    cents = int(round(fv * 100))
    return str(cents)

def _slugify(s: str) -> str:
    import unicodedata as _ud, re as _re
    s = str(s or "")
    s = _ud.normalize("NFKD", s)
    s = "".join(c for c in s if not _ud.combining(c))
    s = s.lower().strip()
    s = _re.sub(r"[^a-z0-9]+","_",s)
    s = _re.sub(r"_+","_",s).strip("_")
    return s
