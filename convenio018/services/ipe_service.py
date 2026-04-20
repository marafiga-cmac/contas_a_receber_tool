"""Processamento de faturamento para convênio Ipê."""

from __future__ import annotations

from io import BytesIO
import pandas as pd

from ..utils.normalizers import _dedupe_headers, _drop_nan_only_columns, _drop_rows_without_inicio
from ..utils.parsers import _excel_col_idx


import re
import pdfplumber

def _converter_valor(valor_str: str) -> float:
    """Converte string de valor financeiro (BR) para float."""
    v = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(v)
    except ValueError:
        return 0.0

def extrair_dados_demonstrativo_ipe(pdf_file) -> dict:
    """
    Lê o PDF de Demonstrativo de Pagamentos do IPÊ.
    Extrai:
    - Data de crédito
    - Totais financeiros (Total no Processo, IRF Retido, Líquido a receber)
    - Tabela de documentos (Nro Doc e Valor Pago)
    Retorna um dicionário estruturado.
    """
    texto_completo = ""
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
    except Exception as e:
        raise ValueError(f"Não foi possível processar o arquivo PDF. Verifique se o formato está correto: {str(e)}")

    linhas = texto_completo.split('\n')
    
    data_credito = None
    total_processo = 0.0
    irf_retido = 0.0
    liquido_receber = 0.0
    
    documentos = []
    
    # Regex para capturar no início a guia/Nro Doc (ex: 50.002, 12345) 
    # e no final o Valor Pago formato financeiro (ex: 1.234,56 ou 50,00)
    doc_pattern = re.compile(r"^(?:0{0,3})?(\d{2,}[\.\d]*)\s+.*\s+(\d{1,3}(?:\.\d{3})*,\d{2})$")
    
    for linha in linhas:
        linha_clean = linha.strip()
        if not linha_clean:
            continue
            
        # 1. Data de Crédito
        if not data_credito:
            m_credito = re.search(r"Creditado em:\s*(\d{2}/\d{2}/\d{4})", linha_clean, re.IGNORECASE)
            if m_credito:
                data_credito = m_credito.group(1)
        
        # 2. Totais (lendo o número mais ao final da linha)
        if re.search(r"Total no Processo", linha_clean, re.IGNORECASE):
            m_tot = re.search(r"([\d\.,]+)$", linha_clean)
            if m_tot:
                total_processo = _converter_valor(m_tot.group(1))
                
        elif re.search(r"IRF Retido", linha_clean, re.IGNORECASE):
            m_irf = re.search(r"([\d\.,]+)$", linha_clean)
            if m_irf:
                irf_retido = _converter_valor(m_irf.group(1))
                
        elif re.search(r"L[íi]quido a receber", linha_clean, re.IGNORECASE):
            m_liq = re.search(r"([\d\.,]+)$", linha_clean)
            if m_liq:
                liquido_receber = _converter_valor(m_liq.group(1))
                
        # 3. Tabela de Documentos
        else:
            m_doc = doc_pattern.match(linha_clean)
            if m_doc:
                nro_doc = m_doc.group(1)
                valor_str = m_doc.group(2)
                valor_pago = _converter_valor(valor_str)
                documentos.append({"Nro Doc": nro_doc, "Valor Pago": valor_pago})

    if not data_credito:
        raise ValueError("Não foi possível encontrar a 'Data de Crédito' (padrão 'Creditado em: ...'). O PDF pode não ser um demonstrativo válido do Ipê.")

    df_docs = pd.DataFrame(documentos)
    if not df_docs.empty:
        # Garante a ordem e tipagem
        df_docs = df_docs[["Nro Doc", "Valor Pago"]]
        df_docs["Nro Doc"] = df_docs["Nro Doc"].astype(str)
        df_docs["Valor Pago"] = df_docs["Valor Pago"].astype(float)
    else:
        df_docs = pd.DataFrame(columns=["Nro Doc", "Valor Pago"])

    return {
        "data_credito": data_credito,
        "totais": {
            "total_processo": total_processo,
            "irf_retido": irf_retido,
            "liquido_receber": liquido_receber
        },
        "df_documentos": df_docs
    }
