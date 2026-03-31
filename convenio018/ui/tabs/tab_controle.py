"""Aba: Controle (NFS-e e Identificação)."""

from __future__ import annotations

import streamlit as st

from ...services.controle_service import atualizar_pendencias, get_pendencias_agrupadas

def render_content(agrupado: dict, tipo_controle: str):
    """Renderiza os cards e expanders para um conjunto de dados agrupados."""
    if not agrupado:
        st.info("Nenhuma pendência atrasada encontrada ou a base de dados ainda não foi atualizada. Clique em 'Atualizar' para sincronizar os dados.")
        return

    for convenio_nome, refs in sorted(agrupado.items()):
        with st.container(border=True):
            st.subheader(f"Convênio: {convenio_nome}")
            
            for ref_nome, data in sorted(refs.items()):
                faturamento_list = data.get("faturamento", [])
                glosa_list = data.get("glosa", [])
                
                # Nomes dos expanders dependem do tipo
                fat_label = "Fat (Remessas de Faturamento)"
                glo_label = "Recurso (Remessas de Recurso de Glosa)"
                
                if faturamento_list:
                    with st.expander(f"{ref_nome} - {fat_label}"):
                        for item in faturamento_list:
                            num = item.get("num_remessa", "") or "S/N"
                            dt = item.get("data_prevista", "")
                            vlr = item.get("valor", "")
                            if dt and len(dt) >= 10 and "-" in dt:
                                partes = dt.split("T")[0].split("-")
                                if len(partes) == 3:
                                    dt = f"{partes[2]}/{partes[1]}/{partes[0]}"
                            st.info(f"**{num}** - {vlr} ({dt})")
                
                if glosa_list:
                    with st.expander(f"{ref_nome} - {glo_label}"):
                        for item in glosa_list:
                            num = item.get("num_remessa", "") or "S/N"
                            dt = item.get("data_prevista", "")
                            vlr = item.get("valor", "")
                            if dt and len(dt) >= 10 and "-" in dt:
                                partes = dt.split("T")[0].split("-")
                                if len(partes) == 3:
                                    dt = f"{partes[2]}/{partes[1]}/{partes[0]}"
                            st.warning(f"**{num}** - {vlr} ({dt})")

def render() -> None:
    st.header("Controle de Pendências")

    unidade = st.session_state.get("unidade") or "CMAP"
    client_secret_path = st.session_state.get("client_secret_path") or "client_secret.json"

    tab_nfse, tab_identificacao = st.tabs(["NFS-e", "Identificação"])

    with tab_nfse:
        col_btn, _ = st.columns([1, 4])
        if col_btn.button("Atualizar NFS-e", type="primary", use_container_width=True, key="btn_upd_nfse"):
            with st.spinner(f"Sincronizando NFS-e ({unidade})..."):
                try:
                    total = atualizar_pendencias(unidade, tipo_controle="nfse", client_secrets_path=client_secret_path)
                    st.success(f"Atualização concluída! {total} pendências encontradas.")
                except Exception as e:
                    st.error(f"Erro: {e}")
        
        st.markdown("---")
        agrupado_nfse = get_pendencias_agrupadas(unidade, tipo_controle="nfse")
        render_content(agrupado_nfse, "nfse")

    with tab_identificacao:
        col_btn, _ = st.columns([1, 4])
        if col_btn.button("Atualizar Identificação", type="primary", use_container_width=True, key="btn_upd_ident"):
            with st.spinner(f"Sincronizando Identificação ({unidade})..."):
                try:
                    total = atualizar_pendencias(unidade, tipo_controle="identificacao", client_secrets_path=client_secret_path)
                    st.success(f"Atualização concluída! {total} pendências encontradas.")
                except Exception as e:
                    st.error(f"Erro: {e}")
        
        st.markdown("---")
        agrupado_ident = get_pendencias_agrupadas(unidade, tipo_controle="identificacao")
        render_content(agrupado_ident, "identificacao")
