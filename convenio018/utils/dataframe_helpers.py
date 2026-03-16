"""Helpers para construção e leitura de DataFrames."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..domain.csv_layouts import REQUIRED_FIELDS
from .normalizers import _norm
from .parsers import _as_number

def _find_col_idx(headers: List[str], candidates: List[str], fallback_idx: Optional[int] = None) -> Optional[int]:
    """Retorna índice da coluna cujo cabeçalho (normalizado) bate com candidates; senão fallback_idx."""
    norm_headers = [_norm(h) for h in headers]
    norm_to_idx = {nh: i for i, nh in enumerate(norm_headers)}
    for cand in candidates:
        nh = _norm(cand)
        if nh in norm_to_idx:
            return norm_to_idx[nh]
    return fallback_idx


def _build_header_map(headers: List[str]) -> Dict[str, str]:
    return {_norm(h): h for h in headers}

def _is_value_field(out_name: str) -> bool:
    n = _norm(out_name)
    return n.startswith("valor") or "imposto" in n or "glosa mantida" in n

def _extract_required_fields(row_dict: Dict[str, Any], headers_map: Dict[str, str]) -> Dict[str, Any]:
    out_names = {
        "Nº Remessa","Ref.","Nº NF","NF recurso",
        "Valor envio XML - Remessa","Valor pgto","Valor glosado","Imposto","Glosa mantida","Valor pago"
    }
    out: Dict[str, Any] = {k: None for k in out_names}
    for norm_key, out_name in REQUIRED_FIELDS.items():
        if norm_key in headers_map:
            original_header = headers_map[norm_key]
            val = row_dict.get(original_header)
            out[out_name] = _as_number(val) if _is_value_field(out_name) else (val if val != "" else None)

    need_imp = out["Imposto"] is None
    need_glo = out["Glosa mantida"] is None
    if need_imp or need_glo:
        for combined_key in COMBINED_IMPOSTO_GLOSA_KEYS:
            if combined_key in headers_map:
                cel = row_dict.get(headers_map[combined_key])
                imp, glo = _split_imposto_glosa(cel)
                if need_imp and imp is not None: out["Imposto"] = imp; need_imp = False
                if need_glo and glo is not None: out["Glosa mantida"] = glo; need_glo = False
                break
    return out

