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

def extrair_detalhado_consultas_ipe(pdf_file) -> pd.DataFrame:
    """
    Extrai dados do PDF detalhado de Consultas Autorizadas (Fase 2).
    Captura Nome (linhas compostas), Dia, Hora, Vlr IPE e N.Nota.
    Retorna Pandas DataFrame com colunas:
    N.Nota, Nome, Dia, Hora, Vlr IPE, Status_Cancelado
    """
    texto_completo = ""
    try:
        pdf_file.seek(0)
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
    except Exception as e:
        raise ValueError(f"Não foi possível processar o arquivo PDF detalhado: {str(e)}")

    # Ignora frase de segurança do PDF do IPE
    texto_completo = texto_completo.replace("Para segurança da informação o CPF pode ser confirmado aqui", "")
    
    linhas = texto_completo.split('\n')
    
    registros = []
    registro_atual = None
    
    for linha in linhas:
        linha_clean = linha.strip()
        if not linha_clean:
            continue
            
        m_data = re.search(r"(\d{2}/\d{2}/\d{4})", linha_clean)
        m_hora = re.search(r"(\d{2}:\d{2})", linha_clean)
        m_nota = re.search(r"\b(\d{2}\.?\d{3})\b", linha_clean)
        m_valor = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2}|(?i)CANCELADA)", linha_clean)
        
        # Se contêm os pilares de um registro, inicia nova extração
        if m_data and m_hora and m_nota:
            if registro_atual:
                registros.append(registro_atual)
                
            dia = m_data.group(1)
            hora = m_hora.group(1)
            nota = m_nota.group(1).replace('.', '').strip()
            valor_raw = m_valor.group(1) if m_valor else "0,00"
            status_cancelado = "CANCELADA" in valor_raw.upper()
            
            # Subtrai as partes já localizadas para sobrar apenas o Nome na string
            resto = linha_clean
            resto = resto.replace(dia, "", 1)
            resto = resto.replace(hora, "", 1)
            resto = resto.replace(m_nota.group(1), "", 1)
            if m_valor:
                resto = resto.replace(m_valor.group(1), "", 1)
                
            # Limpa resíduos (R$, Hífen, espaços sobrando)
            resto = re.sub(r"(?i)\bR\$\b", "", resto)
            resto = re.sub(r"^[-\s]+", "", resto)
            nome = re.sub(r"\s+", " ", resto).strip()
            
            registro_atual = {
                "N.Nota": nota,
                "Nome": nome,
                "Dia": dia,
                "Hora": hora,
                "Vlr IPE": valor_raw,
                "Status_Cancelado": status_cancelado
            }
        else:
            # Caso não seja o início de um novo registro, pode ser a continuação do "Nome" multilinha
            if registro_atual:
                # Ignora palavras comuns de cabeçalhos/rodapés nas páginas subsequentes
                if re.search(r"(?i)Total|Página|Consultas|IPE Saúde|Demonstrativo|Nº\s*Nota|Data|Hora|Valor|Beneficiário", linha_clean):
                    continue
                
                # Anexa o que sobrou ao nome da pessoa
                registro_atual["Nome"] += " " + linha_clean
                registro_atual["Nome"] = re.sub(r"\s+", " ", registro_atual["Nome"]).strip()
                
    # Adicionar o último acumulador ao fim do laço
    if registro_atual:
        registros.append(registro_atual)
        
    df = pd.DataFrame(registros)
    if df.empty:
        df = pd.DataFrame(columns=["N.Nota", "Nome", "Dia", "Hora", "Vlr IPE", "Status_Cancelado"])
    
    return df

