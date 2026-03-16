"""Fluxo principal de leitura de convênios por data de pagamento."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Dict, List

from googleapiclient.discovery import build

from ..integrations.google_sheets import _get_credentials, _read_sheet_values, SCOPES
from ..utils.normalizers import _norm, _split_imposto_glosa
from ..utils.parsers import _as_date
from ..utils.dataframe_helpers import _build_header_map, _extract_required_fields, _find_col_idx
from ..domain.csv_layouts import REMESSA_DATE_KEYS, RECURSO_DATE_KEYS, VALOR_RECURSADO_KEYS

def processar_convenio_para_json(
    spreadsheet_id: str,
    sheet_name: str,
    data_pagamento: date,
    output_dir: str = ".",
    client_secrets_path: str = "client_secret.json",
    token_path: str = "token.json",
) -> str:
    """
    Lê a planilha e escreve um JSON só com as linhas cuja
    Data pgto remessa == data_pagamento OU Data pgto recurso == data_pagamento.
    Colunas são resolvidas por NOME DE CABEÇALHO (case/acentos-insensitive).
    """
    # garante pasta de saída
    os.makedirs(output_dir, exist_ok=True)

    creds = _get_credentials(client_secrets_path=client_secrets_path, token_path=token_path)
    service = build("sheets", "v4", credentials=creds)

    try:
        values = _read_sheet_values(service, spreadsheet_id, sheet_name, header_row=10)
        if not values:
            raise RuntimeError("Nenhum dado retornado. Verifique a aba e o ID da planilha.")

        headers, rows = values[0], values[1:]
        idx_remessa = _find_col_idx(headers, REMESSA_DATE_KEYS, fallback_idx=13)  # N = 13 (0-based)
        idx_recurso = _find_col_idx(headers, RECURSO_DATE_KEYS, fallback_idx=26)  # AA = 26 (0-based)
        idx_valor_recursado = _find_col_idx(headers, VALOR_RECURSADO_KEYS, fallback_idx=None)

        headers_map = _build_header_map(headers)
        out_rows: List[dict] = []

        for row in rows:
            if all(str(c).strip() == "" for c in row):
                continue

            # dict {header_original: valor}
            row_dict = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}

            d_remessa = _as_date(row[idx_remessa]) if (idx_remessa is not None and len(row) > idx_remessa) else None
            d_recurso = _as_date(row[idx_recurso]) if (idx_recurso is not None and len(row) > idx_recurso) else None

            if not ((d_remessa == data_pagamento) or (d_recurso == data_pagamento)):
                continue

            base_item = _extract_required_fields(row_dict, headers_map)

            # Valor recursado com prioridade para o cabeçalho exato
            valor_recursado = None
            if idx_valor_recursado is not None and len(row) > idx_valor_recursado:
                valor_recursado = row[idx_valor_recursado]
            if valor_recursado in (None, ""):
                for k in VALOR_RECURSADO_KEYS:
                    exact = next((h for h in headers if _norm(h) == _norm(k)), None)
                    if exact and (row_dict.get(exact) not in (None, "")):
                        valor_recursado = row_dict.get(exact)
                        break

            base_item["Valor recursado"] = valor_recursado

            base_item["Data Remessa"] = d_remessa.isoformat() if d_remessa else None
            base_item["Data Recurso"] = d_recurso.isoformat() if d_recurso else None
            base_item["_match_remessa"] = (d_remessa == data_pagamento)
            base_item["_match_recurso"] = (d_recurso == data_pagamento)

            out_rows.append(base_item)

        # grava JSON
        ymd = data_pagamento.strftime("%Y%m%d")
        safe_sheet = "".join(c for c in sheet_name if c.isalnum() or c in ("_", "-")).strip() or "aba"
        fpath = os.path.join(output_dir, f"saida_{safe_sheet}_{ymd}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(out_rows, f, ensure_ascii=False, indent=2)

        return fpath

    except HttpError as e:
        raise RuntimeError(f"Erro ao acessar Google Sheets: {e}") from e

