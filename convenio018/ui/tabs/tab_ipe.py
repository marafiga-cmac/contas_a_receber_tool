"""Aba: Identificação Ipê."""

from __future__ import annotations

import streamlit as st

from ...services.api import processar_ipe_arquivos, save_dataframe_to_sqlite


def render() -> None:
    st.subheader("Identificação Ipê")

    st.markdown(
        "Faça o upload das tabelas e arquivos enviados pela Ipê (`.xls` ou `.xlsx`). "
        "As colunas e cabeçalhos serão normalizados (similar a metodologia local), "
        "para posterior análise em grade e extração para SQLite."
    )

    uploaded_files = st.file_uploader(
        "Enviar arquivos (XLS/XLSX)",
        type=["xls", "xlsx"],
        accept_multiple_files=True,
        key="ipe_uploader",
    )

    # Botão de processamento local da RAM
    col1, col2 = st.columns([1, 4])
    with col1:
        btn_processar = st.button("Executar Leitura", type="primary", key="btn_ipe_processar")

    if btn_processar:
        if not uploaded_files:
            st.warning("⚠️ Insira ao menos um arquivo de trabalho.")
        else:
            with st.spinner("Puxando estruturas pelo Pandas..."):
                try:
                    df = processar_ipe_arquivos(uploaded_files)
                    if df is not None and not df.empty:
                        st.session_state["ipe_df"] = df
                        st.success(f"✅ Leitura em memória bem sucedida: {len(df)} linhas formatadas.")
                    else:
                        st.warning("A planilha submetida não retornou dados de tabela TISS após filtros iniciais.")
                        st.session_state.pop("ipe_df", None)
                except Exception as ex:
                    st.error(f"Erro fatal interpretando Excel da Ipê: {ex}")

    st.markdown("---")

    df_view = st.session_state.get("ipe_df")
    
    # Grade Interativa
    if df_view is not None and not df_view.empty:
        st.write("### Auditoria e Validação")
        st.caption("Investigue as colunas convertidas. Estando 100% aderente clique em Salvar no BD Local.")
        
        # Cria uma visualização responsiva de ponta-a-ponta
        st.dataframe(df_view, use_container_width=True, hide_index=True)

        if st.button("💾 Validado: Salvar no Banco de Dados", type="primary", key="btn_ipe_salvar"):
            with st.spinner("Inserindo Batched Records num SQLite..."):
                try:
                    inseridos = save_dataframe_to_sqlite(df_view, "ipe_identificacao")
                    st.success(f"🎉 Insert executado. Registrou-se {inseridos} entidades em `ipe_identificacao`.")
                    st.session_state.pop("ipe_df", None) # Refresh da sessão
                    
                except Exception as db_ex:
                    st.error(f"I/O SQL Exception: {db_ex}")
