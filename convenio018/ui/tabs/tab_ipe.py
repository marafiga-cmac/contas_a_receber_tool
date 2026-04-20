"""Aba: Identificação Ipê."""

from __future__ import annotations

import streamlit as st

from ...services.api import extrair_dados_demonstrativo_ipe, extrair_detalhado_consultas_ipe

def render() -> None:
    st.subheader("Identificação Ipê")

    st.markdown(
        "Faça o upload do **Demonstrativo de Pagamentos** (`.pdf`) enviado pelo IPE Saúde. "
        "O sistema extrairá automaticamente a data de crédito, totais financeiros e a relação de documentos pagos."
    )

    uploaded_file = st.file_uploader(
        "Enviar Demonstrativo PDF",
        type=["pdf"],
        accept_multiple_files=False,
        key="ipe_uploader",
    )

    if uploaded_file is not None:
        if st.button("Executar Leitura", type="primary", key="btn_ipe_processar"):
            # Limpa estado da Fase 2 ao rodar um novo arquivo da Fase 1
            st.session_state.pop("ipe_fase2_df", None)
            
            with st.spinner("Processando Demonstrativo..."):
                try:
                    resultado = extrair_dados_demonstrativo_ipe(uploaded_file)
                    
                    st.success("✅ Extrator finalizado com sucesso!")
                    
                    st.subheader(f"Depósito - {resultado['data_credito']}")
                    
                    # Métricas
                    col1, col2, col3 = st.columns(3)
                    totais = resultado["totais"]
                    
                    def brl_format(val):
                        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        
                    col1.metric("Total no Processo", brl_format(totais["total_processo"]))
                    col2.metric("IRF Retido", brl_format(totais["irf_retido"]))
                    col3.metric("Líquido a Receber", brl_format(totais["liquido_receber"]))
                    
                    df_view = resultado["df_documentos"]
                    
                    st.markdown("### Documentos de Pagamento")
                    
                    if not df_view.empty:
                        # Exibir dataframe conforme regras do projeto
                        st.dataframe(df_view, use_container_width=True, hide_index=True)
                        # Salvar base conforme requerido para a Fase 2
                        st.session_state['ipe_deposito_df'] = df_view
                    else:
                        st.warning("⚠️ O demonstrativo não continha linhas de documento no padrão esperado.")
                        st.session_state.pop("ipe_deposito_df", None)
                        
                except ValueError as ve:
                    st.error(f"Erro de Validação: {ve}")
                    # Log técnico para diagnóstico
                    try:
                        import pdfplumber
                        uploaded_file.seek(0)
                        with pdfplumber.open(uploaded_file) as pdf:
                            preview = pdf.pages[0].extract_text()[:500] if pdf.pages else "PDF Vazio ou sem texto extraível"
                            with st.expander("🔍 Ver log técnico (Conteúdo Lido)"):
                                st.code(preview)
                    except:
                        pass
                except Exception as ex:
                    st.error(f"Erro fatal interpretando o PDF: {ex}")

    st.divider()

    # ==========================================
    # FASE 2: Cruzamento
    # ==========================================
    if "ipe_deposito_df" in st.session_state:
        df_fase1 = st.session_state["ipe_deposito_df"]
        
        st.subheader("Fase 2: Cruzamento de Consultas Autorizadas")
        st.markdown(
            "Faça o upload do PDF com as Consultas Autorizadas (Detalhamento). "
            "O sistema fará o cruzamento com o Demonstrativo lido acima, verificando as notas."
        )
        
        up_fase2 = st.file_uploader(
            "Enviar Consultas Autorizadas PDF",
            type=["pdf"],
            accept_multiple_files=False,
            key="ipe_fase2_uploader"
        )
        
        if up_fase2 is not None:
            if st.button("Cruzar Dados", type="primary", key="btn_ipe_fase2"):
                with st.spinner("Lendo detalhamento paciente por paciente. Isso pode demorar alguns segundos..."):
                    try:
                        df_fase2 = extrair_detalhado_consultas_ipe(up_fase2)
                        st.session_state["ipe_fase2_df"] = df_fase2
                        st.success("✅ Extrato detalhado lido com sucesso!")
                    except Exception as ex:
                        st.error(f"Erro fatal extraindo Consultas Autorizadas: {ex}")
                        
        if "ipe_fase2_df" in st.session_state:
            df_fase2 = st.session_state["ipe_fase2_df"]
            
            # Lista de Documentos validados da Fase 1 (Garante formatação segura de String)
            notas_fase1 = [str(x).strip() for x in df_fase1["Nro Doc"].tolist()]
            
            # Filtros e Cruzamento
            df_fase2["N.Nota_Join"] = df_fase2["N.Nota"].astype(str).str.strip()
            
            mask_validado = df_fase2["N.Nota_Join"].isin(notas_fase1) & (~df_fase2["Status_Cancelado"])
            df_validados = df_fase2[mask_validado].copy()
            df_n_encontrados = df_fase2[~mask_validado].copy()
            
            # Colunas exigidas
            cols_exibicao = ["N.Nota", "Nome", "Dia", "Hora", "Vlr IPE"]
            
            # View Status
            st.markdown("#### Resultados do Cruzamento:")
            opcao_visao = st.radio(
                "Selecione a visão de dados:",
                ["✅ Atendimentos Validados", "⚠️ Tabela Suspeitos"],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            if opcao_visao.startswith("✅"):
                st.caption(f"Exibindo **{len(df_validados)}** consultas com N.Nota validadas contra o Demonstrativo e não canceladas.")
                st.dataframe(df_validados[cols_exibicao], use_container_width=True, hide_index=True)
            else:
                st.caption(f"Exibindo **{len(df_n_encontrados)}** consultas suspeitas: sem correspondência no Demonstrativo ou marcadas como CANCELADA.")
                st.dataframe(df_n_encontrados[cols_exibicao], use_container_width=True, hide_index=True)
