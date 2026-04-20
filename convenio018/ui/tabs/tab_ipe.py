"""Aba: Identificação Ipê."""

from __future__ import annotations

import streamlit as st

from ...services.api import extrair_dados_demonstrativo_ipe

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

    st.markdown("---")
