"""Processamento de NFS-e por data ou número."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from googleapiclient.errors import HttpError

from ..integrations.google_sheets import get_sheets_service, _read_sheet_values, SCOPES
from ..utils.normalizers import _norm, _normalize_nf_number, _split_imposto_glosa
from ..utils.parsers import _as_date, _as_number
from ..utils.dataframe_helpers import _build_header_map, _extract_required_fields, _find_col_idx
from ..domain.csv_layouts import VALOR_RECURSADO_KEYS

def processar_nfse(
    spreadsheet_id: str,
    sheet_name: str,
    modo: str,                 # "data" ou "numero"
    valor: str,                # data ISO (YYYY-MM-DD) quando modo="data", ou número da NF quando modo="numero"
    client_secrets_path: str = "client_secret.json",
    token_path: str = "token.json",
) -> List[dict]:
    """Gera JSON de NFS-e por *data de emissão* (“Data envio NF - Convenio”)
    ou por *número da NF* (“Nº NF” / “NF recurso”). Marca linhas que casam em
    NF recurso para o front-end aplicar regras visuais."""
    from datetime import date

    try:
        service = get_sheets_service(client_secrets_path=client_secrets_path, token_path=token_path)
        _read_sheet_values.clear()  # Limpa cache para garantir que puxe NFs inseridas recém
        values = _read_sheet_values(service, spreadsheet_id, sheet_name, header_row=10)
    except HttpError as e:
        raise RuntimeError(f"Erro ao acessar Google Sheets: {e}") from e

    if not values:
        raise RuntimeError("Nenhum dado retornado. Verifique a aba e o ID da planilha.")

    headers, rows = values[0], values[1:]
    headers_map = _build_header_map(headers)

    # índices dos campos necessários
    idx_emissao = _find_col_idx(headers, ["data envio nf - convenio"], fallback_idx=None)

    idx_num_nf = _find_col_idx(
        headers,
        ["nº nf", "n nf", "no nf", "numero nf", "nfse", "nfs-e", "nfs e"],
        fallback_idx=None,
    )

    idx_nf_recurso = _find_col_idx(
        headers,
        ["nf recurso", "nf_rec", "nf rec", "nf de recurso", "nf recurso glosa"],
        fallback_idx=None,
    )

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

            cand_nf = (
                _normalize_nf_number(row[idx_num_nf])
                if idx_num_nf is not None and idx_num_nf < len(row)
                else ""
            )

            cand_nfrec = (
                _normalize_nf_number(row[idx_nf_recurso])
                if idx_nf_recurso is not None and idx_nf_recurso < len(row)
                else ""
            )
            
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

    return out_rows

