"""Processamento de NFS-e por data ou número."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from googleapiclient.discovery import build

from ..integrations.google_sheets import _get_credentials, _read_sheet_values, SCOPES
from ..utils.normalizers import _norm, _normalize_nf_number, _split_imposto_glosa
from ..utils.parsers import _as_date, _as_number
from ..utils.dataframe_helpers import _build_header_map, _extract_required_fields, _find_col_idx
from ..domain.csv_layouts import VALOR_RECURSADO_KEYS

def processar_nfse_para_json(
    spreadsheet_id: str,
    sheet_name: str,
    modo: str,                 # "data" ou "numero"
    valor: str,                # data ISO (YYYY-MM-DD) quando modo="data", ou número da NF quando modo="numero"
    output_dir: str = ".",
    client_secrets_path: str = "client_secret.json",
    token_path: str = "token.json",
) -> str:
    """Gera JSON de NFS-e por *data de emissão* (“Data envio NF - Convenio”)
    ou por *número da NF* (“Nº NF” / “NF recurso”). Marca linhas que casam em
    NF recurso para o front-end aplicar regras visuais."""
    import os, json
    from datetime import date
    os.makedirs(output_dir, exist_ok=True)

    creds = _get_credentials(client_secrets_path=client_secrets_path, token_path=token_path)
    service = build("sheets", "v4", credentials=creds)

    values = _read_sheet_values(service, spreadsheet_id, sheet_name, header_row=10)
    if not values:
        raise RuntimeError("Nenhum dado retornado. Verifique a aba e o ID da planilha.")

    headers, rows = values[0], values[1:]
    headers_map = _build_header_map(headers)

    # índices dos campos necessários
    idx_emissao = _find_col_idx(headers, ["data envio nf - convenio"], fallback_idx=None)

    header_num_nf = next((h for h in headers if _norm(h) in ("nº nf","n nf","no nf","numero nf","nfse")), None)
    header_nf_recurso = next((h for h in headers if _norm(h) in ("nf recurso","nf de recurso")), None)

    # onde procurar "Valor recursado"
    idx_valor_recursado = _find_col_idx(headers, VALOR_RECURSADO_KEYS, fallback_idx=None)

    out_rows = []
    if modo == "data":
        target_date = date.fromisoformat(str(valor))

    def _get_valor_recursado(row_dict, row):
        """Resolve 'Valor recursado' com prioridade para cabeçalhos equivalentes."""
        # 1) se tem índice direto
        if idx_valor_recursado is not None and len(row) > idx_valor_recursado:
            v = row[idx_valor_recursado]
            if str(v).strip() != "":
                return v
        # 2) varrer candidatos por nome normalizado
        for k in VALOR_RECURSADO_KEYS:
            exact = next((h for h in headers if _norm(h) == _norm(k)), None)
            if exact and (row_dict.get(exact) not in (None, "")):
                return row_dict.get(exact)
        return None

    for row in rows:
        if all(str(c).strip() == "" for c in row):
            continue

        row_dict = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
        base_item = _extract_required_fields(row_dict, headers_map)

        # captura data de emissão da NF
        d_emissao = _as_date(row[idx_emissao]) if idx_emissao is not None and len(row) > idx_emissao else None

        # por padrão (preenchidos embaixo)
        base_item["_nfse_modo"] = modo
        base_item["_nfse_match_kind"] = None

        match_emissao = match_nf = False

        if modo == "data":
            match_emissao = (d_emissao == target_date)
            if not match_emissao:
                continue
        else:
            # normaliza números p/ comparação
            target_nf = _normalize_nf_number(valor)
            cand_nf = _normalize_nf_number(row_dict.get(header_num_nf)) if header_num_nf else ""
            cand_nfrec = _normalize_nf_number(row_dict.get(header_nf_recurso)) if header_nf_recurso else ""
            if not (target_nf and (target_nf == cand_nf or target_nf == cand_nfrec)):
                continue
            match_nf = True
            # classifica o tipo de match
            if target_nf == cand_nfrec and cand_nfrec != "":
                base_item["_nfse_match_kind"] = "recurso"
            else:
                base_item["_nfse_match_kind"] = "nf"

        # adiciona valor recursado ao JSON (útil para a troca no front)
        base_item["Valor recursado"] = _get_valor_recursado(row_dict, row)

        base_item["Data Emissao NF"] = d_emissao.isoformat() if d_emissao else None
        base_item["_match_emissao"] = match_emissao
        base_item["_match_nf"] = match_nf

        out_rows.append(base_item)

    safe_sheet = "".join(c for c in sheet_name if c.isalnum() or c in ("_", "-")).strip() or "aba"
    suffix = f"data_{target_date.strftime('%Y%m%d')}" if modo == "data" else f"nf_{_normalize_nf_number(valor) or 'sem_numero'}"
    fname = f"saida_nfse_{safe_sheet}_{suffix}.json"
    fpath = os.path.join(output_dir, fname)

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, ensure_ascii=False, indent=2)
    return fpath

