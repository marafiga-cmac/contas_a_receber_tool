"""Serviço de extração das pendências atrasadas de NFS-e e Identificação."""

from __future__ import annotations

from datetime import datetime
import sqlite3

import pandas as pd

from ..integrations.google_sheets import get_sheets_service, _read_sheet_values, get_sheet_names
from ..config import SHEET_IDS
from ..utils.dataframe_helpers import _find_col_idx
from ..utils.parsers import _as_date
from ..database.db_manager import save_dataframe_to_sqlite, DB_PATH


def parse_header(headers, keys):
    return _find_col_idx(headers, keys, fallback_idx=None)


def _get_table_name(tipo_controle: str) -> str:
    if tipo_controle == "nfse":
        return "controle_pendencias"
    return "controle_identificacao"


def _remove_old_pendencias(unidade: str, tipo_controle: str):
    """Remove pendências da unidade atual na tabela via DELETE para sincronização."""
    table_name = _get_table_name(tipo_controle)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "unidade TEXT, convenio TEXT, tipo TEXT, "
            "ref TEXT, num_remessa TEXT, data_prevista TEXT, "
            "valor TEXT)"
        )
        conn.execute(f"DELETE FROM {table_name} WHERE unidade = ?", (unidade,))
        conn.commit()


def atualizar_pendencias(
    unidade: str,
    tipo_controle: str = "nfse",
    client_secrets_path: str = "client_secret.json",
    token_path: str = "token.json"
):
    """
    Varre as planilhas de 2025 e 2026 da unidade ativa.
    Identifica pendências dependendo do tipo_controle:
    
    - nfse:
        - Faturamento: Data Prevista NF < Hoje E Nº NF Vazia
        - Glosa: Data Prevista Recurso < Hoje E NF Recurso Vazia
    
    - identificacao:
        - Faturamento: Data Prevista Pgto. < Hoje E Data pgto Vazia
        - Glosa: Data prevista de pgto recurso < Hoje E Data pgto recurso Vazia
    
    Escreve na tabela correspondente.
    """
    service = get_sheets_service(client_secrets_path, token_path)
    sheets_dict = SHEET_IDS.get(unidade, {})
    
    hoje = datetime.now().date()
    rows_data = []

    for ano, spreadsheet_id in sheets_dict.items():
        try:
            tabs = get_sheet_names(service, spreadsheet_id)
        except Exception:
            continue
            
        for tab in tabs:
            if not tab:
                continue
            
            try:
                # Evita recachear tudo
                _read_sheet_values.clear() 
                values = _read_sheet_values(service, spreadsheet_id, tab, header_row=10)
                if not values or len(values) < 2:
                    continue
                
                headers = values[0]
                rows = values[1:]
                
                # Globais
                idx_ref = parse_header(headers, ["ref.", "ref", "referencia"])
                idx_num_remessa = parse_header(headers, ["nº remessa", "n remessa", "numero remessa", "n° da remessa"])
                
                # Faturamento
                if tipo_controle == "nfse":
                    idx_prevista_fat = parse_header(headers, ["data prevista nf - convenio", "previsao nf"])
                    idx_exclusao_fat = parse_header(headers, ["nº nf", "n nf", "no nf", "numero nf"])
                else: # identificacao
                    idx_prevista_fat = parse_header(headers, ["data prevista pgto.", "data prevista pgto", "prev pgto"])
                    idx_exclusao_fat = parse_header(headers, ["data pgto", "data de pagamento", "dt pgto"])
                
                # Novo: Valor NF conforme solicitado
                idx_vlr_remessa = parse_header(headers, ["valor nf", "vlr nf", "valor nota", "valor da nf"])
                
                # Glosa
                idx_prevista_glo = parse_header(headers, ["data prevista de pgto recurso", "previsao pgto recurso"])
                
                if tipo_controle == "nfse":
                    idx_exclusao_glo = parse_header(headers, ["nf recurso", "nf_rec", "nf rec", "nf recurso glosa"])
                else: # identificacao
                    idx_exclusao_glo = parse_header(headers, ["data pgto recurso", "data pagamento recurso", "dt pgto recurso"])
                
                # Novo: Valor NF RG conforme solicitado
                idx_vlr_recursado = parse_header(headers, ["valor nf rg", "vlr nf rg", "valor nota recurso", "nf rg"])
                
                for row in rows:
                    if all(str(c).strip() == "" for c in row):
                        continue
                        
                    def get_val(idx):
                        if idx is not None and idx < len(row):
                            return str(row[idx]).strip()
                        return ""
                    
                    ref_val = get_val(idx_ref)
                    num_remessa_val = get_val(idx_num_remessa)
                    
                    # Checagem Faturamento
                    previsao_fat_str = get_val(idx_prevista_fat)
                    exclusao_fat_val = get_val(idx_exclusao_fat)
                    d_prev_fat = _as_date(previsao_fat_str)
                    
                    if d_prev_fat and d_prev_fat <= hoje and (not exclusao_fat_val):
                        rows_data.append({
                            "unidade": unidade,
                            "convenio": tab,
                            "tipo": "Faturamento",
                            "ref": ref_val,
                            "num_remessa": num_remessa_val,
                            "data_prevista": d_prev_fat.isoformat(),
                            "valor": get_val(idx_vlr_remessa)
                        })
                        
                    # Checagem Glosa
                    previsao_glo_str = get_val(idx_prevista_glo)
                    exclusao_glo_val = get_val(idx_exclusao_glo)
                    d_prev_glo = _as_date(previsao_glo_str)
                    
                    if d_prev_glo and d_prev_glo <= hoje and (not exclusao_glo_val):
                         rows_data.append({
                            "unidade": unidade,
                            "convenio": tab,
                            "tipo": "Glosa",
                            "ref": ref_val,
                            "num_remessa": num_remessa_val,
                            "data_prevista": d_prev_glo.isoformat(),
                            "valor": get_val(idx_vlr_recursado)
                        })

            except Exception:
                continue

    _remove_old_pendencias(unidade, tipo_controle)

    if rows_data:
        df = pd.DataFrame(rows_data)
        save_dataframe_to_sqlite(df, _get_table_name(tipo_controle))
        
    return len(rows_data)


def get_pendencias_agrupadas(unidade: str, tipo_controle: str = "nfse") -> dict:
    """Busca as pendências do banco e agrupa por 'convenio' e depois por 'ref'."""
    table_name = _get_table_name(tipo_controle)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "unidade TEXT, convenio TEXT, tipo TEXT, "
                "ref TEXT, num_remessa TEXT, data_prevista TEXT, "
                "valor TEXT)"
            )
            df = pd.read_sql(f"SELECT * FROM {table_name} WHERE unidade = ?", conn, params=(unidade,))
            if df.empty:
                return {}
            
            res = {}
            for convenio, group_conv in df.groupby("convenio"):
                res[convenio] = {}
                for ref, group_ref in group_conv.groupby("ref"):
                    res[convenio][ref] = {
                        "faturamento": group_ref[group_ref["tipo"] == "Faturamento"].to_dict("records"),
                        "glosa": group_ref[group_ref["tipo"] == "Glosa"].to_dict("records")
                    }
            return res
    except Exception as e:
        print(f"Erro a buscar pendencias: {e}")
        return {}
