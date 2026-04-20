"""Geração da capa consolidada de NFS-e emitidas."""

from __future__ import annotations

import json
import os
from datetime import datetime

from googleapiclient.discovery import build

from ..integrations.google_sheets import _get_credentials, _read_sheet_values, SCOPES
from ..utils.normalizers import _normalize_nf_number
from ..utils.parsers import _as_date, _as_number
from ..utils.dataframe_helpers import _find_col_idx
from ..domain.csv_layouts import VALOR_RECURSADO_KEYS, RECURSO_DATE_KEYS

def gerar_capa_nfse_por_data(
    spreadsheet_id: str,
    sheet_names: list[str],
    data_emissao: str,          # ISO YYYY-MM-DD
    client_secrets_path: str = "client_secret.json",
    token_path: str = "token.json",
) -> str:
    """Gera o JSON da aba **Capa**.

    Varre todas as abas/convênios em `sheet_names`, filtra pelo dia em
    “Data envio NF - Convenio” e consolida por (NFSe, Convênio).

    Regra do valor quando a NFSe aparece em mais de uma remessa:
      - `valor_nf_base` = MAIOR "Valor NF" encontrado para a mesma NFSe
      - `valor_recursado_total` = SOMA de "Valor recursado" (quando existir)
      - `valor_total` = valor_nf_base + valor_recursado_total

    Saída: lista de dicts: { "NFSe": str, "Convenio": str, "Valor": float }
    """
    import os, json, re
    from datetime import date
    import pandas as pd

    output_dir = "."
    os.makedirs(output_dir, exist_ok=True)

    target_date = date.fromisoformat(str(data_emissao))

    creds = _get_credentials(client_secrets_path=client_secrets_path, token_path=token_path)
    service = build("sheets", "v4", credentials=creds)

    def _money_to_float(v) -> float:
        if v is None or (isinstance(v, float) and pd.fsna(v)):
            return 0.0
        try:
            return float(v)
        except Exception:
            s = str(v).strip()
            if s == "":
                return 0.0
            s = s.replace("R$", "").replace(" ", "").replace("\u00A0", "")
            s = s.replace(".", "").replace(",", ".")
            try:
                return float(s)
            except Exception:
                return 0.0

    # acumuladores por (nfse, convenio): max(valor_nf) e soma(valor_recursado)
    acc: dict[tuple[str, str], dict[str, float]] = {}
    nfse_do_dia: set[tuple[str, str]] = set()  # (nfse, sheet_name)

    _read_sheet_values.clear()
    for sheet_name in (sheet_names or []):
        try:
            values = _read_sheet_values(service, spreadsheet_id, sheet_name, header_row=10)
        except Exception:
            # Se a aba não existir, apenas ignora e segue para as demais
            continue

        if not values:
            continue

        headers, rows = values[0], values[1:]

        idx_emissao = _find_col_idx(headers, ["data envio nf - convenio"], fallback_idx=None)
        if idx_emissao is None:
            continue

        idx_num_nf = _find_col_idx(
            headers,
            ["nº nf", "n nf", "no nf", "numero nf", "nfse", "nfs-e", "nfs e"],
            fallback_idx=None,
        )
        if idx_num_nf is None:
            continue

        idx_valor_nf = _find_col_idx(
            headers,
            ["valor nf", "valor nfse", "valor nfs-e", "valor da nf"],
            fallback_idx=None,
        )
        idx_valor_recursado = _find_col_idx(headers, VALOR_RECURSADO_KEYS, fallback_idx=None)

        idx_nf_recurso = _find_col_idx(
            headers,
            ["nf recurso", "nf_rec", "nf rec", "nf de recurso", "nf recurso glosa"],
            fallback_idx=None,
        )
        idx_data_pgto_recurso = _find_col_idx(headers, RECURSO_DATE_KEYS, fallback_idx=None)
        idx_data_emissao_nf = _find_col_idx(headers, ["data emissão nf.", "data emissao nf"], fallback_idx=None)

        # -------------------------
        # 1ª PASSAGEM: NFSe emitidas no dia (remessas "normais")
        # -------------------------
        for row in rows:
            if idx_emissao >= len(row) or idx_num_nf >= len(row):
                continue

            d = _as_date(row[idx_emissao])
            if not d or d != target_date:
                continue

            nfse = _normalize_nf_number(row[idx_num_nf])
            if not nfse:
                continue

            # marca que essa NFSe pertence ao dia (por convênio/aba)
            nfse_do_dia.add((str(nfse), str(sheet_name)))

        # -------------------------
        # 1B) Marca NF alvo por "Data pgto recurso" (NF recurso pago no dia)
        # -------------------------
        if idx_nf_recurso is not None and idx_data_pgto_recurso is not None:
            for row in rows:
                if idx_nf_recurso >= len(row) or idx_data_pgto_recurso >= len(row):
                    continue

                dpg = _as_date(row[idx_data_pgto_recurso])
                if not dpg or dpg != target_date:
                    continue

                nf_recurso = _normalize_nf_number(row[idx_nf_recurso])
                if not nf_recurso:
                    continue

                nfse_do_dia.add((str(nf_recurso), str(sheet_name)))
        
        # -------------------------
        # 1D) Marca NF alvo por "Data Emissão Nf." (NF gerada hoje)
        # -------------------------
        if idx_data_emissao_nf is not None:
            for row in rows:
                if idx_data_emissao_nf >= len(row):
                    continue
                
                dem = _as_date(row[idx_data_emissao_nf])
                if not dem or dem != target_date:
                    continue
                
                # Prioriza NF recurso se existir, senão usa a principal
                nf_alvo = None
                if idx_nf_recurso is not None and idx_nf_recurso < len(row):
                    nf_alvo = _normalize_nf_number(row[idx_nf_recurso])
                if not nf_alvo and idx_num_nf >= 0 and idx_num_nf < len(row):
                    nf_alvo = _normalize_nf_number(row[idx_num_nf])
                
                if nf_alvo:
                    nfse_do_dia.add((str(nf_alvo), str(sheet_name)))

        # -------------------------
        # 1C) Soma Valor NF de TODAS as linhas cuja Nº NF esteja no conjunto alvo
        #      (assim NF que entrou no set alvo também traz todas as remessas)
        # -------------------------
        for row in rows:
            if idx_num_nf >= len(row):
                continue

            nfse = _normalize_nf_number(row[idx_num_nf])
            if not nfse:
                continue

            key = (str(nfse), str(sheet_name))
            if key not in nfse_do_dia:
                continue

            valor_nf = 0.0
            if idx_valor_nf is not None and idx_valor_nf < len(row):
                valor_nf = _money_to_float(row[idx_valor_nf])

            valor_rec = 0.0
            if idx_valor_recursado is not None and idx_valor_recursado < len(row):
                valor_rec = _money_to_float(row[idx_valor_recursado])

            slot = acc.get(key)
            if slot is None:
                acc[key] = {"sum_valor_nf": float(valor_nf), "sum_valor_rec": float(valor_rec)}
            else:
                slot["sum_valor_nf"] += float(valor_nf)
                slot["sum_valor_rec"] += float(valor_rec)

                
        # -------------------------
        # 2ª PASSAGEM: Recurso de Glosa (NF recurso) SEM filtrar pela data de emissão
        # -------------------------
        if idx_nf_recurso is not None:
            for row in rows:
                if idx_nf_recurso >= len(row):
                    continue

                nf_recurso = _normalize_nf_number(row[idx_nf_recurso])
                if not nf_recurso:
                    continue

                # só soma se o NF recurso apontar para uma NFSe que foi emitida no dia
                key_rec = (str(nf_recurso), str(sheet_name))
                if key_rec not in nfse_do_dia:
                    continue

                valor_rec = 0.0
                if idx_valor_recursado is not None and idx_valor_recursado < len(row):
                    valor_rec = _money_to_float(row[idx_valor_recursado])

                slot2 = acc.get(key_rec)
                if slot2 is None:
                    acc[key_rec] = {"sum_valor_nf": 0.0, "sum_valor_rec": float(valor_rec)}
                else:
                    slot2["sum_valor_rec"] += float(valor_rec)

    out_rows = []
    def _nf_sort(n: str) -> int:
        return int(re.sub(r"\D", "", n) or "0")

    for (nfse, convenio), v in sorted(acc.items(), key=lambda x: (x[0][1], _nf_sort(x[0][0]))):
        total = float(v.get("sum_valor_nf", 0.0)) + float(v.get("sum_valor_rec", 0.0)) 
        out_rows.append({"NFSe": str(nfse), "Convenio": str(convenio), "Valor": round(total, 2)})

    fname = f"saida_capa_nfse_{target_date.strftime('%Y%m%d')}.json"
    fpath = os.path.join(output_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, ensure_ascii=False, indent=2)
    return fpath

