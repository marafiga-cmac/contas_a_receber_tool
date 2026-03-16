"""Aba: Lançamentos Glosa Mantida.

Objetivo:
  - Montar lançamentos contábeis manualmente a partir de:
      Convênio, Competência, Remessa, (opcional) Nº NFSe, Valor
  - Acompanhar uma lista acumulada (pré-visualização por descrição)
  - Exportar tudo em um único CSV (padrão do template já usado no projeto)

Regras de histórico (descrição):
  - Para convênios cujo histórico inclui NFSe (Copel, Sul America, Bradesco):
      "Glosa Mantida - Glosa S/Rem. (Remessa) - NFSe (Num. NFSe) - Fat. (Competencia)"
  - Para convênios que vão para a regra 1133003 (sem NFSe):
      "Glosa Mantida S/Glosa S/Rem. (Remessa) - Faturamento Plano de Saúde  - (Competencia)"

Estrutura do lançamento (CSV):
  - Débito:  3149021 / restrição "2"  / valor positivo
  - Crédito: 1133004 / restrição "0A" / valor negativo
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from ...services.api import get_convenios_por_unidade, gerar_csv_glosa_mantida_bytes

import io

import pandas as pd


CONVENIOS_COM_NFSE_NO_HISTORICO = {"Copel", "Sul America", "Bradesco", "Conab", 
                                   "Global Araucária", "Global Paranaguá", "MedSul",
                                     "Notredame", "Postal Saúde", "Prevent Senior", 
                                     "Sul America", "Life",}


def _fmt_competencia(raw: str) -> str:
    """Normaliza competência para MM/YYYY (tolerante)."""
    # Reaproveita a função do legado sem importar tudo no topo
    from ...services import backend_legacy as _bl

    return _bl._fmt_ref_mmYYYY(raw)  # noqa: SLF001


def _to_float_br(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        try:
            return float(v)
        except Exception:
            return 0.0
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def _ensure_state() -> None:
    if "glosa_mantida_items" not in st.session_state:
        st.session_state["glosa_mantida_items"] = []


def render() -> None:
    st.subheader("Lançamentos Glosa Mantida")
    _ensure_state()

    unidade = st.session_state.get("unidade") or "CMAP"
    convenios, label = get_convenios_por_unidade(unidade)

    # ---- Form (5 espaços) ----
    c1, c2, c3, c4, c5 = st.columns([2.2, 1.2, 1.2, 1.2, 1.2])

    with c1:
        convenio = st.selectbox(
            label or "Convênio",
            options=convenios,
            index=0 if convenios else None,
            key="gm_convenio",
        )

    with c2:
        competencia_raw = st.text_input(
            "Competência",
            placeholder="Ex.: 01/2026",
            key="gm_competencia",
        )

    with c3:
        remessa = st.text_input(
            "Remessa",
            placeholder="Ex.: 123456",
            key="gm_remessa",
        )

    # NFSe aparece só quando necessário
    precisa_nfse = str(convenio or "") in CONVENIOS_COM_NFSE_NO_HISTORICO
    with c4:
        if precisa_nfse:
            nfse = st.text_input(
                "Nº da NFSe",
                placeholder="Ex.: 98765",
                key="gm_nfse",
            )
        else:
            st.caption("Nº NFSe (não necessário)")
            nfse = ""

    with c5:
        valor = st.text_input(
            "Valor",
            placeholder="Ex.: 123,45",
            key="gm_valor",
        )

    colb1, colb2, colb3 = st.columns([1.2, 1.0, 2.0])
    with colb1:
        montar = st.button("Montar", type="primary")
    with colb2:
        limpar = st.button("Limpar lista")

    if limpar:
        st.session_state["glosa_mantida_items"] = []
        st.success("Lista limpa.")

    if montar:
        convenio_s = str(convenio or "").strip()
        competencia = _fmt_competencia(competencia_raw)
        remessa_s = str(remessa or "").strip()
        nfse_s = str(nfse or "").strip()
        valor_f = _to_float_br(valor)

        if not convenio_s:
            st.warning("Selecione um convênio.")
        elif not competencia:
            st.warning("Informe a competência (ex.: 01/2026).")
        elif not remessa_s:
            st.warning("Informe a remessa.")
        elif precisa_nfse and not nfse_s:
            st.warning("Informe o número da NFSe.")
        elif valor_f <= 0:
            st.warning("Informe um valor maior que zero.")
        else:
            if precisa_nfse:
                desc = (
                    f"Glosa Mantida - Glosa S/Rem. {remessa_s} - "
                    f"NFSe {nfse_s} - Fat. {competencia}"
                )
            else:
                desc = (
                    f"Glosa Mantida S/Glosa S/Rem. {remessa_s} - "
                    f"Faturamento Plano de Saúde  - {competencia}"
                )

            st.session_state["glosa_mantida_items"].append(
                {
                    "convenio": convenio_s,
                    "competencia": competencia,
                    "remessa": remessa_s,
                    "nfse": nfse_s,
                    "valor": float(valor_f),
                    "descricao": desc,
                }
            )
            st.success("Lançamento adicionado à lista.")

    # ---- Preview acumulado ----
    items: List[Dict] = st.session_state.get("glosa_mantida_items") or []

    st.markdown("---")

    st.markdown("#### Importar CSV (reanalisar / continuar)")

    up = st.file_uploader(
        "Envie um CSV já exportado desta aba",
        type=["csv"],
        key="glosa_mantida_uploader",
    )

    col_imp1, col_imp2 = st.columns(2)
    modo = col_imp1.radio(
        "Como importar?",
        ["Somar com os lançamentos atuais", "Substituir tudo pelos do CSV"],
        horizontal=True,
        key="glosa_mantida_import_mode",
    )

    if up is not None:
        try:
            df_in = pd.read_csv(up, dtype=str, sep=None, engine="python")
            df_in.columns = [c.strip() for c in df_in.columns]

            # Colunas mínimas esperadas (as que a aba salva no export)
            col_map = {
                "Convenio": "convenio",
                "Competencia": "competencia",
                "Remessa": "remessa",
                "NFSe": "nfse",
                "Valor": "valor",
                "Descricao": "descricao",
                "Conta Debito": "conta_debito",
                "Restricao Debito": "restricao_debito",
                "Conta Credito": "conta_credito",
                "Restricao Credito": "restricao_credito",
                "Subconta": "subconta",
            }

            # aceita também nomes já normalizados
            for k, v in list(col_map.items()):
                if k not in df_in.columns and v in df_in.columns:
                    col_map[v] = v

            # seleciona só o que existe e renomeia
            cols_exist = [c for c in col_map.keys() if c in df_in.columns]
            df_use = df_in[cols_exist].rename(columns={c: col_map[c] for c in cols_exist})

            # transforma em lista de dicts (items)
            imported_items = df_use.fillna("").to_dict(orient="records")

            if modo == "Substituir tudo pelos do CSV":
                st.session_state["glosa_mantida_items"] = imported_items
            else:
                st.session_state.setdefault("glosa_mantida_items", [])
                st.session_state["glosa_mantida_items"].extend(imported_items)

            st.success(f"CSV importado com {len(imported_items)} lançamento(s).")
            st.rerun()

        except Exception as e:
            st.error(f"Falha ao importar CSV: {e}")


        st.markdown("#### Pré-visualização (descrições acumuladas)")

        if not items:
            st.info("Nenhum lançamento montado ainda.")
            return

    total = sum(float(it.get("valor") or 0.0) for it in items)
    st.caption(f"Itens: **{len(items)}** | Total: **R$ {total:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))

    # Mostra só a descrição (como solicitado), mas mantém dados p/ export
    items = st.session_state.get("glosa_mantida_items", [])

    for idx, it in enumerate(items):
        c1, c2 = st.columns([0.92, 0.08])

        convenio = it.get("convenio", "")
        desc = it.get("descricao", "")
        v = _to_float_br(it.get("valor"))
        v_str = f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        with c1:
            st.write(f"{idx+1}. [{convenio}] {desc} — {v_str}")

        with c2:
            if st.button("--", key=f"glosa_mantida_del_{idx}", help="Excluir lançamento"):
                st.session_state["glosa_mantida_items"].pop(idx)
                st.rerun()

    st.markdown("---")

    # ---- Export CSV ----
    fname, csv_bytes = gerar_csv_glosa_mantida_bytes(items)
    st.download_button(
        "Exportar CSV",
        data=csv_bytes,
        file_name=fname,
        mime="text/csv",
        type="primary",
    )
