import pandas as pd
import streamlit as st
from ...services.api import processar_cabergs_arquivos, processar_csv_analise, marcar_encontrados_csv

def render() -> None:
    st.subheader("Identificação CABERGS")
    st.markdown("Faça o upload dos relatórios XLS/XLSX do CABERGS e, em seguida, anexe o CSV para análise e marcação.")
    
    # 1. Upload dos arquivos do Convênio (antigo result.get("cabergs_xls_files"))
    cabergs_files = st.file_uploader(
        "Anexar relatórios CABERGS (XLS/XLSX)", 
        type=["xls", "xlsx"], 
        accept_multiple_files=True,
        key="cabergs_up_xls"
    )

    if cabergs_files:
        try:
            df_cabergs = processar_cabergs_arquivos(cabergs_files)
            st.subheader("Prévia do CABERGS (cabeçalho ajustado)")
            st.caption("Aplicado: B→C, AB→AF, AQ→AR | Extraído: G5 (Remessa) e X5 (Competência)")
            st.dataframe(df_cabergs, use_container_width=True)
            st.session_state["cabergs_df_xls"] = df_cabergs
        except Exception as e:
            st.error(f"Erro ao processar CABERGS: {e}")
            st.session_state["cabergs_df_xls"] = pd.DataFrame()
    else:
        st.info("Anexe o(s) arquivo(s) XLS/XLSX do CABERGS para exibir a tabela.")
        st.session_state.pop("cabergs_df_xls", None)

    st.markdown("---")
    st.subheader("Arquivo CSV para Análise (automático)")

    # 2. Upload do CSV
    csv_file = st.file_uploader("Envie o arquivo CSV", type=["csv"], key="cabergs_csv_upload")

    if csv_file is not None:
        try:
            df_csv = processar_csv_analise(csv_file)
            st.session_state["cabergs_df_csv"] = df_csv
        except Exception as e:
            st.error(f"Erro ao processar CSV: {e}")
            st.session_state["cabergs_df_csv"] = pd.DataFrame()
    
    # 3. Lógica de Execução e Marcação
    df_xls_ss = st.session_state.get("cabergs_df_xls")
    df_csv_ss = st.session_state.get("cabergs_df_csv")

    st.markdown("---")

    if st.button("Executar Marcação", type="primary", key="btn_exec_mark_csv"):
        if isinstance(df_xls_ss, pd.DataFrame) and not df_xls_ss.empty and isinstance(df_csv_ss, pd.DataFrame) and not df_csv_ss.empty:
            try:
                df_csv_marked = marcar_encontrados_csv(df_xls_ss, df_csv_ss, flag_col="Encontrado")
                st.session_state["cabergs_df_csv"] = df_csv_marked
            except Exception as e:
                st.error(f"Erro ao marcar encontrados no CSV: {e}")
        else:
            st.warning("Anexe e processe os dois arquivos (XLS/XLSX e CSV) antes de executar.")

    # 4. Preview do CSV Tratado
    df_csv_show = st.session_state.get("cabergs_df_csv")
    if isinstance(df_csv_show, pd.DataFrame) and not df_csv_show.empty:
        if "Encontrado" not in df_csv_show.columns:
            df_csv_show = df_csv_show.copy()
            df_csv_show.insert(0, "Encontrado", False)

        disabled_cols = [c for c in df_csv_show.columns if c not in ("Encontrado", "Remessa (G5)", "Valor MV")]

        st.subheader("Prévia do CSV tratado")
        st.data_editor(
            df_csv_show,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_cols,
            key="csv_preview_editor",
        )
        st.session_state["cabergs_df_csv"] = df_csv_show
