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

    # 2. Tabela de Documentos
    documentos = []
    # Novo padrão sugerido: captura Grupo 1 (Doc) e Grupo 2 (Valor no final $)
    # O padrão (\d{2}\.?\d{3}) captura formatos como 50.002 ou 50002
    doc_pattern = re.compile(r"(\d{2}\.?\d{3})\s+.*?([\d\.]*,\d{2})$")
    
    for linha in texto_completo.split('\n'):
        linha_clean = linha.strip()
        if not linha_clean:
            continue
            
        m_doc = doc_pattern.search(linha_clean)
        if m_doc:
            # Grupo 1: Nro Doc (limpa o ponto)
            nro_doc = m_doc.group(1).replace('.', '')
            # Grupo 2: Valor Pago (converte para float para manter o DF tipado)
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
def extrair_detalhado_consultas_ipe(pdf_file):
    text = ""
    # Evita problemas de leitura caso o ponteiro não esteja no início
    pdf_file.seek(0)
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            extr = page.extract_text()
            if extr:
                text += extr + " "
    
    # Troca quebras de linha por espaços e remove espaços duplos
    text_limpo = re.sub(r'\s+', ' ', text.replace('\n', ' '))

    # Fatia o texto a cada CPF encontrado (o CPF marca o fim exato de um registro)
    parts = re.split(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', text_limpo)
    
    documentos = []
    
    # Itera de 2 em 2 (bloco de texto + CPF correspondente)
    for i in range(0, len(parts) - 1, 2):
        bloco = parts[i]
        
        # Pega a Matrícula (13 dígitos) que é o "meio" do registro
        match_mat = re.search(r'\b(\d{13})\b', bloco)
        if not match_mat:
            continue
        
        matricula = match_mat.group(1)
        before_mat, after_mat = bloco.split(matricula, 1)
        
        # EXTRAIR NOME (pega as palavras em maiúsculo logo antes da matrícula)
        nome = "NÃO IDENTIFICADO"
        match_nome = re.search(r'(?:^|\s)\d{2,3}\s+([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s]+)$', before_mat)
        if match_nome:
            nome = match_nome.group(1).strip()
        else:
            match_nome_fallback = re.search(r'([A-ZÀ-Ÿ\s]{5,})$', before_mat)
            if match_nome_fallback:
                nome = match_nome_fallback.group(1).strip()
        
        # EXTRAIR STATUS, VLR IPE E N.NOTA
        status_cancelado = False
        if "CANCELADA" in after_mat.upper():
            status_cancelado = True
            vlr_ipe = "CANCELADA"
            n_nota = "-"
        else:
            # Pega Valor IPE e N.Nota que ficam antes do Ref e PINPAD no fim do bloco
            match_valores = re.search(r'(\d+,\d{2})\s+(\d{4,8})\s+\d+\s+[A-Za-z]\s*$', after_mat)
            if match_valores:
                vlr_ipe = match_valores.group(1)
                n_nota = match_valores.group(2)
            else:
                vlr_ipe = "0,00"
                n_nota = "-"
                
        # EXTRAIR HORA E DIA
        hora, dia = "", ""
        match_hora = re.search(r'(\d{2}:\d{2}:\d{2}:\d{1,2})', after_mat)
        if match_hora:
            hora = match_hora.group(1)
            
        after_mat_no_hour = after_mat.replace(hora, '') if hora else after_mat
        match_dia = re.search(r'(?:^|\s)(\d{2})(?=\s)', after_mat_no_hour)
        if match_dia:
            dia = match_dia.group(1)

        documentos.append({
            "N.Nota": str(n_nota).replace('.', '').strip(),
            "Nome": nome,
            "Dia": dia,
            "Hora": hora,
            "Vlr IPE": vlr_ipe,
            "Status_Cancelado": status_cancelado
        })
        
    return pd.DataFrame(documentos)
