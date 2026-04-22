"""Renderização do relatório de NFS-e."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ...services.exports_service import gerar_csv_nfse_lancamentos_bytes
from .print_templates import LOGO_PATH, _build_print_html, _path_to_data_uri

def _to_float_any(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return 0.0
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def _fmt_money(v):
    try:
        x = _to_float_any(v)
        return "R$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def render_relatorio_nfse_para_impressao(items: list[dict]):
    modo_nfse = (st.session_state.get("nfse_modo") or "").lower()

    # Colunas base (sempre incluir Nº NF para consistência)
    if modo_nfse == "data":
        cols = [
            "Nº Remessa",
            "Ref.",
            "Valor envio XML - Remessa",
            "Nº NF",
            "Valor NF",
            "Valor glosado",
            "Imposto",
            "Glosa mantida",
        ]
    else:
        cols = [
            "Nº Remessa",
            "Ref.",
            "Nº NF",
            "Valor NF",
            "Valor glosado",
            "Imposto",
            "Glosa mantida",
        ]

    df = pd.DataFrame(items or [])
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].copy()

    # Determina máscaras de recurso e remessa
    aux = pd.DataFrame(items or [])
    mask_recurso = pd.Series(False, index=df.index)
    if "_nfse_match_kind" in aux.columns:
        mask_recurso = aux["_nfse_match_kind"].isin(["recurso", "nf_recurso", "rg"])
    
    # Se houver Ref. começando com RG, também é recurso
    if "Ref." in df.columns:
        mask_recurso = mask_recurso | df["Ref."].astype(str).str.upper().str.startswith("RG -")
    
    mask_remessa = ~mask_recurso

    # 1. Substituição de valores: troca "Valor envio XML - Remessa" por "Valor glosado" (original) nas linhas recurso
    if "Valor envio XML - Remessa" in df.columns and "Valor glosado" in aux.columns:
        df.loc[mask_recurso, "Valor envio XML - Remessa"] = aux.loc[mask_recurso, "Valor glosado"].values

    # 2. Cabeçalho Dinâmico
    nome_col_xml = "Valor envio XML - Remessa"
    if mask_recurso.any() and mask_remessa.any():
        nome_col_xml = "Valor Glosa / Valor XML"
    elif mask_recurso.any():
        nome_col_xml = "Valor de Glosa do Recurso"

    if nome_col_xml != "Valor envio XML - Remessa":
        df.rename(columns={"Valor envio XML - Remessa": nome_col_xml}, inplace=True)

    # 3. Ajustes especiais (prefixo RG, Valor NF)
    if mask_recurso.any():
        # prefixo "RG - " em Ref.
        if "Ref." in df.columns:
            df.loc[mask_recurso, "Ref."] = df.loc[mask_recurso, "Ref."].apply(
                lambda s: f"RG - {s}"
                if (str(s or "").strip()[:4].upper() != "RG -")
                else s
            )

        # "Valor NF" vira "Valor NF RG" (ou Valor recursado) nas linhas recurso
        if "Valor NF" in df.columns:
            val_rg_key = "Valor NF RG"
            val_rec_key = "Valor recursado"
            
            # Tenta pegar de Valor NF RG primeiro, se não tiver, tenta Valor recursado
            if val_rg_key in aux.columns:
                df.loc[mask_recurso, "Valor NF"] = aux.loc[mask_recurso, val_rg_key].apply(_to_float_any).values
            elif val_rec_key in df.columns:
                df.loc[mask_recurso, "Valor NF"] = df.loc[mask_recurso, val_rec_key].apply(_to_float_any)
            elif val_rec_key in aux.columns:
                df.loc[mask_recurso, "Valor NF"] = aux.loc[mask_recurso, val_rec_key].apply(_to_float_any).values

        # Zera o Valor glosado apenas nas linhas de recurso
        if "Valor glosado" in df.columns:
            df.loc[mask_recurso, "Valor glosado"] = 0.0

    # --- totais ---
    total_envio_xml = float(
        df[nome_col_xml].apply(_to_float_any).sum()
    ) if nome_col_xml in df.columns else 0.0
    total_valor_nf = float(
        df["Valor NF"].apply(_to_float_any).sum()
    ) if "Valor NF" in df.columns else 0.0
    total_glosado = float(
        df["Valor glosado"].apply(_to_float_any).sum()
    ) if "Valor glosado" in df.columns else 0.0
    total_imposto = float(
        df["Imposto"].apply(_to_float_any).sum()
    ) if "Imposto" in df.columns else 0.0
    total_glosa_mnt = float(
        df["Glosa mantida"].apply(_to_float_any).sum()
    ) if "Glosa mantida" in df.columns else 0.0

    # =========================
    # NOVO BLOCO – CSV de lançamentos NFS-e
    # =========================
    st.markdown("---")
    st.markdown("### Exportar lançamentos contábeis (NFS-e)")

    convenio = (
        st.session_state.get("nfse_ctx_convenio")
        or st.session_state.get("selected_convenio")
        or ""
    )
    referencia = st.session_state.get("nfse_context") or ""

    # ✅ DF para CSV (baseado no df processado acima)
    df_csv = df.copy()
    aux_all = pd.DataFrame(items or [])
    
    # Adiciona colunas extras do aux_all que não estão no df base, de forma segura
    for extra_col in ["NF recurso", "Valor NF RG", "Valor recursado", "_nfse_match_kind"]:
        if extra_col in aux_all.columns:
            df_csv[extra_col] = aux_all[extra_col].values

    # ✅ fallback: se Nº NF estiver vazio, usa NF recurso (se disponível)
    if "Nº NF" in df_csv.columns:
        df_csv["Nº NF"] = df_csv["Nº NF"].astype(str).replace({"None": "", "nan": ""})
        
    if "NF recurso" in df_csv.columns:
        mask_vazio_nf = df_csv["Nº NF"].str.strip().eq("")
        mask_tem_rec = df_csv["NF recurso"].astype(str).str.strip().ne("") & df_csv["NF recurso"].notna()
        df_csv.loc[mask_vazio_nf & mask_tem_rec, "Nº NF"] = df_csv.loc[mask_vazio_nf & mask_tem_rec, "NF recurso"]

    # Se for RG, garante que a coluna Nº NF (para descrição) tenha o número de "NF recurso"
    mask_rg = df_csv.get("_nfse_match_kind", "").astype(str).str.lower().isin(["recurso","rg"])
    if "Ref." in df_csv.columns:
        mask_rg = mask_rg | df_csv["Ref."].astype(str).str.lower().str.startswith("rg")
    
    if "NF recurso" in df_csv.columns:
        mask_has_rec = df_csv["NF recurso"].notna() & (df_csv["NF recurso"].astype(str).str.strip() != "")
        df_csv.loc[mask_rg & mask_has_rec, "Nº NF"] = df_csv.loc[mask_rg & mask_has_rec, "NF recurso"]

    fname_nfse, csv_bytes_nfse = gerar_csv_nfse_lancamentos_bytes(
        df_nfse=df_csv,
        selected_convenio=convenio,
        referencia_str=referencia,
    )

    st.download_button(
        f"⬇️ Baixar CSV NFS-e ({convenio})",
        data=csv_bytes_nfse,
        file_name=fname_nfse,
        mime="text/csv",
        use_container_width=True,
        key="dl_csv_nfse",
    )

    # --- DataFrame formatado para a grade do Streamlit ---
    df_fmt = df.copy()
    for c in [nome_col_xml, "Valor NF", "Valor recursado", "Valor glosado", "Imposto", "Glosa mantida"]:
        if c in df_fmt.columns:
            df_fmt[c] = df_fmt[c].apply(_fmt_money)

    st.markdown("#### Pré-visualização do Relatório NFS-e")
    st.dataframe(df_fmt, use_container_width=True)

    # --- tabela HTML para impressão ---
    table_html = df_fmt.to_html(index=False, border=0, escape=False)

    # --- cards de totais ---
    total_pairs = [
        ("Valor total envio XML", _fmt_money(total_envio_xml)),
        ("Valor total NFS-e", _fmt_money(total_valor_nf)),
        ("Valor total glosado", _fmt_money(total_glosado)),
        ("Valor total imposto", _fmt_money(total_imposto)),
        ("Valor total glosa mantida", _fmt_money(total_glosa_mnt)),
        ("Número de linhas", f"{len(df)}"),
    ]

    titulo = "Relatório — NFS-e"
    convenio_hdr = convenio
    data_str = referencia or (
        st.session_state.get("selected_date").strftime("%d/%m/%Y")
        if st.session_state.get("selected_date")
        else "-"
    )

    if not st.session_state.get("logo_data_uri"):
        st.session_state["logo_data_uri"] = _path_to_data_uri(
            st.session_state.get("logo_path") or LOGO_PATH
        )

    html = _build_print_html(
        titulo=titulo,
        convenio=convenio_hdr,
        data_str=data_str,          # aqui é a data escolhida
        table_html=table_html,
        total_pairs=total_pairs,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=850, scrolling=True)

