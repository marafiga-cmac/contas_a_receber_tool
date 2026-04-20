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
        # Garante que o buffer esteja no início caso tenha sido lido antes
        pdf_file.seek(0)
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
    except Exception as e:
        raise ValueError(f"Não foi possível processar o arquivo PDF: {str(e)}")

    # 1. Busca de Metadados (Texto Consolidado para evitar quebras de linha)
    texto_para_busca = texto_completo.replace('\n', ' ')
    
    # Data de Crédito
    m_credito = re.search(r"(?i)Creditado\s+em\s*[:\s]*(\d{2}/\d{2}/\d{4})", texto_para_busca)
    data_credito = m_credito.group(1) if m_credito else None
    
    if not data_credito:
        raise ValueError("Não foi possível encontrar a 'Data de Crédito'. O PDF pode não ser um demonstrativo válido do Ipê ou o padrão mudou.")

    # Totais Financeiros
    def buscar_total(label_regex):
        match = re.search(label_regex + r"\s*[:\s]*([\d\.,]+)", texto_para_busca, re.IGNORECASE)
        return _converter_valor(match.group(1)) if match else 0.0

    total_processo = buscar_total(r"Total\s+no\s+Processo")
    irf_retido = buscar_total(r"IRF\s+Retido")
    liquido_receber = buscar_total(r"L[íi]quido\s+a\s+receber")

    # 2. Tabela de Documentos (Linha a linha)
    documentos = []
    # Regex: Início opcional com 0s, captura números com pontos (limparemos depois), 
    # salta conteúdo vago ate encontrar o valor financeiro no final da linha.
    doc_pattern = re.compile(r"^(?:0{0,3})?(\d{2,}[\.\d]*)\s+.*\s+(\d{1,3}(?:\.\d{3})*,\d{2})$")
    
    for linha in texto_completo.split('\n'):
        linha_clean = linha.strip()
        m_doc = doc_pattern.match(linha_clean)
        if m_doc:
            # Limpeza do Nro Doc: remove pontos conforme requisitado
            nro_doc = m_doc.group(1).replace('.', '')
            valor_pago = _converter_valor(m_doc.group(2))
            documentos.append({"Nro Doc": nro_doc, "Valor Pago": valor_pago})

    df_docs = pd.DataFrame(documentos)
    if not df_docs.empty:
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
