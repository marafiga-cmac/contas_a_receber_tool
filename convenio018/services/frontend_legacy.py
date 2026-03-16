from __future__ import annotations
from datetime import date, datetime
import base64
import os
import mimetypes

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from backend import (
    gerar_csv_lancamentos_bytes,
    gerar_csv_recursos_bytes,
    gerar_csv_nfse_lancamentos_bytes,
)


# =============================================================================
# Listas de convênios por unidade
# =============================================================================

CONVENIOS_CMAP = [
    "Afpergs", "Amil", "Assefaz", "Banco Central", "Bradesco", "Cabergs", "Cabergs ID",
    "CarePlus", "Cassi", "Doctor", "Embratel", "Humana", "GEAP", "Gente Saúde",
    "Life", "Mediservice", "Notredame", "Postal Saúde", "Prevent Senior",
    "Proasa", "Saúde Caixa", "Sul America", "Capesesp", "Ipê Saúde", 
]

# ---- CMAC ----
# Regra 1133004 -> 1133003
CMAC_GLOSA_TO_3303 = {
    "Amil": ("20", "Amil Assistencia Med"),
    "Assefaz": ("27", "Fundacao Assistencia"),
    "Banco Central": ("43", "Pagamento Sigef Ap"),
    "Cassi": ("26", "Caixa de Assistencia"),
    "GEAP": ("105", "Geap Autogestao Em S"),
    "ICS": ("107", "Instituto Curitiba D"),
    "Itaú": ("9", "Porto Saude"),
    "Judicemed": ("17", "Associacao De Assist"),
    "Paraná Clínicas": ("101", "Sul America Companhia"),
    "Petrobrás": ("23", "Associacao Petrobras"),
    "Proasa": ("25", "Proasa Programa Adven"),
    "Sanepar": ("12", "Fundação Sanepar A"),
    "Saúde Caixa": ("15", "Saude Caixa"),
    "Voam": ("30", "Volvo Do Brasil Veicu"),
    "Select": ("109", "Select"),    
}

# Regra 1133004 -> 1133001
CMAC_GLOSA_TO_3301 = {
    "Bradesco": ("10", "Sinistro Ap/Certif"),
    "Conab": ("22", "Conab Sede Sureg Par"),
    "Copel": ("11", "Fundacao Copel"),
    "Global Araucária": ("48", "Santos E Assolari Tel"),
    "Global Paranaguá": ("24", "Global Tele Atendimen"),
    "Mediservice": ("100", "Mediservice Operadora Planos"),
    "MedSul": ("7", "Alca Servicos De Cobr"),
    "Notredame": ("18", "Notre Dame Intermedi"),
    "Postal Saúde": ("29", "Postal Saude - Caixa"),
    "Prevent Senior": ("102", "Prevent Senior Privat"),
    "Sul America": ("3", "Sul America Companhia"),
    "Life": ("45", "Life Empresarial Saude Ltda"),
}

# Lista consolidada de convênios CMAC (alfabética e sem duplicatas)
CONVENIOS_CMAC = sorted(
    set(list(CMAC_GLOSA_TO_3303.keys()) + list(CMAC_GLOSA_TO_3301.keys())),
    key=lambda s: s.lower()
)

DEPOSITO_SUBCONTA_BANCO = {
    "CMAP": "3708/0001649-7",
    "CMAC": "03645/00044210",
}

CSV_HEADER_FIRST_ROW = {
    "CMAP": ("1841", "Clínica Adventista de Porto Alegre - IASBS"),
    "CMAC": ("1941", "Clínica Adventista de Curitiba - IASBS"),
}

# =============================================================================
# LOGO ÚNICA (pré-visualização e impressão) — ajuste aqui se quiser trocar
# =============================================================================

from pathlib import Path
from ..config import APP_ICON_PATH

LOGO_PATH = str(APP_ICON_PATH) if APP_ICON_PATH.exists() else ""


def render_relatorio_nfse_para_impressao(items: list[dict]):
    modo_nfse = (st.session_state.get("nfse_modo") or "").lower()

    # Colunas base
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
            "Valor envio XML - Remessa",
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

    # Ajustes especiais quando modo = "numero" (prefixo RG, etc.)
    if st.session_state.get("nfse_modo") == "numero":
        aux = pd.DataFrame(items or [])
        if "_nfse_match_kind" in aux.columns:
            mask_recurso = aux["_nfse_match_kind"].isin(["recurso", "nf_recurso"])

            # prefixo "RG - " em Ref.
            if "Ref." in df.columns:
                df.loc[mask_recurso, "Ref."] = df.loc[mask_recurso, "Ref."].apply(
                    lambda s: f"RG - {s}"
                    if (str(s or "").strip()[:4].upper() != "RG -")
                    else s
                )

            # "Valor NF" vira "Valor recursado" nas linhas recurso
            if "Valor NF" in df.columns:
                if "Valor recursado" in df.columns:
                    df.loc[mask_recurso, "Valor NF"] = df.loc[mask_recurso, "Valor recursado"]
                elif "Valor recursado" in aux.columns:
                    df.loc[mask_recurso, "Valor NF"] = aux.loc[mask_recurso, "Valor recursado"].values

            # Zera o Valor glosado apenas nas linhas de recurso
            if "Valor glosado" in df.columns:
                df.loc[mask_recurso, "Valor glosado"] = 0.0

    # --- helpers de moeda ---
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

    # --- totais ---
    total_envio_xml = float(
        df["Valor envio XML - Remessa"].apply(_to_float_any).sum()
    ) if "Valor envio XML - Remessa" in df.columns else 0.0
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

    # ✅ DF completo (vem do JSON), para garantir Nº NF / NF recurso na descrição
    df_csv = pd.DataFrame(items or [])
    for c in ["Nº Remessa", "Ref.", "Nº NF", "NF recurso", "Valor NF", "_nfse_match_kind"]:
        if c not in df_csv.columns:
            df_csv[c] = None

    # ✅ fallback: se Nº NF estiver vazio, usa NF recurso
    df_csv["Nº NF"] = (
        df_csv["Nº NF"].astype(str).replace({"None": "", "nan": ""})
    )
    mask_vazio = df_csv["Nº NF"].str.strip().eq("")
    df_csv.loc[mask_vazio, "Nº NF"] = df_csv.loc[mask_vazio, "NF recurso"]

    df_csv = df.copy()
    aux_all = pd.DataFrame(items or [])
    for extra_col in ["Nº NF", "NF recurso", "Valor recursado", "_nfse_match_kind"]:
        if extra_col in aux_all.columns:
            try:
                df_csv[extra_col] = aux_all[extra_col].values
            except Exception:
                df_csv[extra_col] = aux_all[extra_col]

    # Se for RG, garante que a coluna Nº NF (para descrição) tenha o número de "NF recurso"
    if "NF recurso" in df_csv.columns:
        mask_rg = df_csv.get("_nfse_match_kind", "").astype(str).str.lower().isin(["recurso","rg"])
        if "Ref." in df_csv.columns:
            mask_rg = mask_rg | df_csv["Ref."].astype(str).str.lower().str.startswith("rg")
        if "Nº NF" not in df_csv.columns:
            df_csv["Nº NF"] = ""
        df_csv.loc[
            mask_rg
            & df_csv["NF recurso"].notna()
            & (df_csv["NF recurso"].astype(str).str.strip() != ""),
            "Nº NF"
        ] = df_csv.loc[mask_rg, "NF recurso"]

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
    for c in ["Valor envio XML - Remessa", "Valor NF", "Valor glosado", "Imposto", "Glosa mantida"]:
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
        data_str=data_str,
        table_html=table_html,
        total_pairs=total_pairs,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=850, scrolling=True)


# --------------------------------------------------------------------------- #
# Aba: Capa (NFSe emitidas - faturamento)
# --------------------------------------------------------------------------- #

def _build_print_html_capa(titulo, data_str, table_html, total_geral, logo_data_uri=None):
    """Cabeçalho no padrão FO-FAT 021 (print do usuário)."""
    css = """
    <style>
    :root { color-scheme: light; }
    html, body { background:#ffffff !important; }
    body { font-family: Arial, Helvetica, sans-serif; color:#000; margin:0; padding:0; }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 24px; background:#ffffff; }

    .header-main {
        display:flex; align-items:center; justify-content:space-between;
        border-bottom:2px solid #000; padding-bottom:8px; margin-bottom:16px;
    }

    .logo-box { width: 180px; text-align:left; padding:0; }
    .logo-box img { max-width:150px; max-height:80px; display:block; }

    .title-box { flex:1; text-align:center; font-size:22px; font-weight:bold; color:#000; }

    .info-box { width:200px; border:1px solid #000; font-size:13px; padding:6px 10px; background:#fff; color:#000; }
    .info-row { display:flex; justify-content:space-between; padding:2px 0; }
    .info-label { font-weight:bold; margin-right:6px; }

    .meta { margin-top:6px; display:flex; justify-content:center; font-size:13px; }
    .meta b { margin-right:6px; }

    .print-toolbar.no-print {
        display:flex; justify-content:flex-end; gap:8px; margin: 6px 0 12px;
    }
    .print-btn {
        padding:8px 14px; border:1px solid #d0d7de; border-radius:8px; background:#f6f8fa;
        cursor:pointer; font-size:14px;
    }
    .print-btn:hover { background:#eef2f6; }

    /* Tabela base */
    table {
        border-collapse: separate;
        width: 100%;
        font-size: 15px; /* aumenta leitura */
        margin-top: 14px;
        background: #fff;
        color: #000;
    }

    /* Cabeçalho */
    thead th {
        text-align: center;
        border-bottom: 2px solid #000;
        padding: 10px 6px;
        background: #f3f3f3;
        color: #000;
        font-size: 15px;
    }

    /* Corpo */
    tbody td {
        border-bottom: 1px solid #ccc;
        padding: 10px 6px;
        font-size: 15px;
    }

    /* Remove fundo zebrado (opcional, fica mais clean com gap) */
    tbody tr:nth-child(even) td {
        background: #fafafa;
    }

    /* Colunas */
    th.col-nfse, td.col-nfse {
        text-align: center;
        width: 160px;
    }

    th.col-convenio, td.col-convenio {
        text-align: center;
        width: auto;
    }

    th.col-valor, td.col-valor {
        text-align: center;
        width: 180px;
        white-space: nowrap;
        font-weight: 600;
    }

        .total-footer {
        width: 100%;
        display: flex;
        justify-content: flex-end;
        margin-top: 20px;
    }

    .total-box {
        min-width: 240px;
        border-top: 2px solid #000;
        padding-top: 8px;
        text-align: right;
        font-size: 16px;
        font-weight: bold;
    }

    .total-label {
        margin-right: 8px;
    }

    @media print {
        .no-print { display:none !important; }
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
    </style>
    """

    logo_html = "<div class='logo-box'></div>"
    if logo_data_uri:
        logo_html = f"<div class='logo-box'><img src='{logo_data_uri}' /></div>"

    unidade_str = st.session_state.get("unidade") or ""

    html = f"""
    <html>
    <head>
        <meta charset='utf-8'/>
        {css}
    </head>
    <body>
        <div class='wrap'>

        <div class='header-main'>
            {logo_html}
            <div class='title-box'>{titulo}</div>
            <div class='info-box'>
            <div class='info-row'><span class='info-label'>FO-FAT</span><span>021</span></div>
            <div class='info-row'><span class='info-label'>Revisão</span><span>00</span></div>
            <div class='info-row'><span class='info-label'>Unidade:</span><span>{unidade_str}</span></div>
            </div>
        </div>

        <div class='meta'><b>DATA:</b><span>{data_str}</span></div>

        <div class='print-toolbar no-print'>
            <button class="print-btn" onclick="window.print()">🖨️ Imprimir</button>
        </div>

        {table_html}

        <div class='total-footer'>
            <div class='total-box'>
                <span class='total-label'>TOTAL:</span>
                <span>{total_geral}</span>
            </div>
        </div>

        </div>
    </body>
    </html>
    """

    return html

def render_relatorio_capa(items: list[dict], data_emissao: date):
    """Renderiza a Capa: NFSe / Convênio / Valor."""
    import streamlit.components.v1 as components

    st.subheader("NFSe Emitidas - Faturamento")

    if not items:
        st.info("Nenhuma NFS-e encontrada para esta data.")
        return

    df = pd.DataFrame(items).copy()
    for c in ["NFSe", "Convenio", "Valor"]:
        if c not in df.columns:
            df[c] = None
    df = df[["NFSe", "Convenio", "Valor"]]

    def _fmt_brl(x):
        try:
            v = float(x)
        except Exception:
            v = 0.0
        s = f"{v:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"

    df_show = df.copy()

    total_geral_valor = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0).sum()
    total_geral_fmt = _fmt_brl(total_geral_valor)

    df_show["Valor"] = df_show["Valor"].apply(_fmt_brl)

    st.dataframe(df_show, use_container_width=True, hide_index=True)

    table_html = (
        "<table>"
        "<thead><tr>"
        "<th class='col-nfse'>NFSe</th>"
        "<th class='col-convenio'>Convênio</th>"
        "<th class='col-valor'>Valor</th>"
        "</tr></thead><tbody>"
    )
    for _, r in df_show.iterrows():
        table_html += (
            f"<tr>"
            f"<td class='col-nfse'>{r['NFSe']}</td>"
            f"<td class='col-convenio'>{r['Convenio']}</td>"
            f"<td class='col-valor'>{r['Valor']}</td>"
            f"</tr>"
        )
    table_html += "</tbody></table>"

    titulo = "NFSe EMITIDAS - FATURAMENTO"
    data_str = data_emissao.strftime("%d/%m/%Y") if hasattr(data_emissao, "strftime") else str(data_emissao)
    html = _build_print_html_capa(
        titulo=titulo,
        data_str=data_str,
        table_html=table_html,
        total_geral=total_geral_fmt,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=850, scrolling=True)


def _guess_mime_from_name(name: str) -> str:
    if not name:
        return "image/png"
    mime, _ = mimetypes.guess_type(name)
    if mime:
        return mime
    low = name.lower()
    if low.endswith(".ico"):
        return "image/x-icon"
    if low.endswith(".jpg") or low.endswith(".jpeg"):
        return "image/jpeg"
    if low.endswith(".gif"):
        return "image/gif"
    return "image/png"

def _bytes_to_data_uri(raw: bytes, name_hint: str | None = None) -> str:
    mime = _guess_mime_from_name(name_hint or "")
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"

def _file_to_data_uri(file) -> str | None:
    if not file:
        return None
    raw = file.read()
    mime = getattr(file, "type", None) or _guess_mime_from_name(getattr(file, "name", "") or "")
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"

def _path_to_data_uri(path: str) -> str | None:
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read()
        return _bytes_to_data_uri(raw, path)
    except Exception:
        return None

# Carrega a logo padrão uma única vez
if "logo_data_uri" not in st.session_state:
    st.session_state["logo_data_uri"] = _path_to_data_uri(LOGO_PATH)


# =============================================================================
# Helper: lista de convênios e overrides por unidade (para reuso em outras abas)
# =============================================================================

def get_convenios_por_unidade(unidade: str):
    """
    Retorna (lista_de_convenios, label) de acordo com a unidade selecionada.
    - CMAP: usa CONVENIOS_CMAP (já existente no projeto)
    - CMAC: união de chaves dos dicionários CMAC
    """
    unidade = (unidade or "").strip().upper()
    if unidade == "CMAC":
        return CONVENIOS_CMAC, "Convênio (CMAC)"
    # padrão: CMAP
    try:
        return sorted(CONVENIOS_CMAP, key=lambda s: s.lower()), "Convênio (CMAP)"
    except Exception:
        return [], "Convênio (CMAP)"
    
if "logo_path" not in st.session_state:
    st.session_state["logo_path"] = LOGO_PATH

if not st.session_state.get("logo_data_uri"):
    st.session_state["logo_data_uri"] = _path_to_data_uri(st.session_state["logo_path"])    

# =============================================================================
# Formulário (UI principal)
# =============================================================================

def render_form():
    unidade = st.session_state.get("unidade") or "CMAP"

    # prefs para CSV conforme unidade
    header_cols = CSV_HEADER_FIRST_ROW.get(unidade, CSV_HEADER_FIRST_ROW["CMAP"])
    deposito_subconta = DEPOSITO_SUBCONTA_BANCO.get(
        unidade,
        DEPOSITO_SUBCONTA_BANCO["CMAP"]
    )

    st.session_state["csv_prefs"] = {
        "header_first_row": header_cols,
        "deposito_subconta_banco": deposito_subconta,
    }

    # convênios e overrides por unidade
    csv_convenio_overrides = {}
    if unidade == "CMAP":
        convenios = sorted(CONVENIOS_CMAP, key=lambda s: s.lower())

        csv_convenio_overrides = {
            "Cabergs": {"deposito_subconta_banco": "00270617409902"},
            "Saúde Caixa": {"deposito_subconta_banco": "0374-50090", "deposito_suffix": "Saude Caixa Pgto Credenc", "glosa_neg_target": "1133003"},
            "Bradesco": {"subconta_convenio": "10", "deposito_suffix": "Sinistro Ap/Certif."},
            "CarePlus": {"subconta_convenio": "63", "deposito_suffix": "Care Plus Medicina"},
            "Prevent Senior": {"subconta_convenio": "91", "deposito_suffix": "Prevent Senior Privat"},
            "Sul America": {"subconta_convenio": "3", "deposito_suffix": "Sul America", "glosa_neg_trget": "1133001"},
            "Notredame": {"subconta_convenio": "47", "deposito_suffix": "Notre Dame Intermedi"},
            "Assefaz": {"glosa_neg_target": "1133003"},
            "Cassi": {"glosa_neg_target": "1133003"},
            "Amil": {"glosa_neg_target": "1133003"},
            "Banco Central": {"glosa_neg_target": "1133003"},
            "GEAP": {"glosa_neg_target": "1133003"},
            "Geap": {"glosa_neg_target": "1133003"},
            "Doctor": {"glosa_neg_target": "1133003"},
            "Mediservice": {"subconta_convenio": "16", "deposito_suffix": "Mediservice Operadora Planos", "glosa_neg_target": "1133001"},

        }

    else:
        convenios_dict = {}
        for nome, (sub, suffix) in CMAC_GLOSA_TO_3303.items():
            convenios_dict[nome] = {
                "subconta_convenio": sub,
                "deposito_suffix": suffix,
                "glosa_neg_target": "1133003",
            }
        for nome, (sub, suffix) in CMAC_GLOSA_TO_3301.items():
            convenios_dict[nome] = {
                "subconta_convenio": sub,
                "deposito_suffix": suffix,
                "glosa_neg_target": "1133001",
            }

        deposito_overrides = {
            "Petrobras": "3722-130049991",
            "Petrobrás": "3722-130049991",
            "Saúde Caixa": "0374-50082",
        }
        for k, conta in deposito_overrides.items():
            if k in convenios_dict:
                convenios_dict[k]["deposito_subconta_banco"] = conta

        convenios = sorted(convenios_dict.keys(), key=lambda s: s.lower())
        csv_convenio_overrides = convenios_dict

    st.session_state["csv_convenio_overrides"] = csv_convenio_overrides

    st.markdown("Selecione o **convênio** e a **data de pagamento**.")

    convenio = st.selectbox(
        "Convênio",
        options=[""] + convenios,
        index=(
            ([""] + convenios).index(
                st.session_state.get("selected_convenio") or ""
            )
            if (st.session_state.get("selected_convenio") or "") in ([""] + convenios)
            else 0
        ),
    )

    # --- REGRA (UI): CABERGS no CMAP -> permitir upload XLS/XLSX ---
    is_cabergs = (str(convenio or "").strip().lower() == "cabergs id")
    is_cmap = (str(unidade or "").strip().upper() == "CMAP")

    if is_cmap and is_cabergs:
        st.markdown("---")
        st.subheader("Arquivo adicional (CABERGS)")
        st.caption("Envie o arquivo XLS/XLSX do CABERGS para aplicarmos regras específicas (vamos tratar isso depois).")

        cabergs_xls_files = st.file_uploader(
        "Enviar arquivo(s) CABERGS (XLS/XLSX)",
        type=["xls", "xlsx"],
        accept_multiple_files=True,
        key="cabergs_xls_uploader",
        )

        st.session_state["cabergs_xls_files"] = cabergs_xls_files
    else:
        # limpa quando troca de convênio/unidade (evita ficar arquivo antigo na sessão)
        st.session_state["cabergs_xls_files"] = []

    # --- CABERGS (CMAP): sem data e sem botão; processa automaticamente pelo upload ---
    if is_cmap and is_cabergs:
        data_pagamento = None
        submitted = False
    else:
        data_pagamento = st.date_input(
            "Data de pagamento",
            value=st.session_state.get("selected_date") or date.today(),
            format="DD/MM/YYYY",
            help=(
                "Serão consideradas linhas cuja **Data pgto remessa** "
                "ou **Data pgto recurso** coincidam com a data informada."
            ),
        )

        submitted = st.button("Continuar", type="primary", use_container_width=True)

    output_dir = st.session_state.get("output_dir") or "."
    modelo_csv = st.session_state.get("modelo_csv") or ""

    return {
        "submitted": submitted,
        "convenio": convenio,
        "data_pagamento": data_pagamento,
        "output_dir": output_dir,
        "modelo_csv": modelo_csv,
        "cabergs_xls_files": st.session_state.get("cabergs_xls_files", []),
    }

# =============================================================================
# Helpers de exibição/print
# =============================================================================

def _fmt_brl(v):
    try:
        s = f"{float(v):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def _df_for_print(df: pd.DataFrame, monetary_cols):
    dfp = df.copy()
    for col in monetary_cols:
        if col in dfp.columns:
            dfp[col] = dfp[col].apply(_fmt_brl)
    return dfp

def _build_print_html(titulo, convenio, data_str, table_html, total_pairs, logo_data_uri=None):
    css = """
    <style>
      :root { color-scheme: light; }
      html, body { background:#ffffff !important; }
      body { font-family: Arial, Helvetica, sans-serif; color:#000; margin:0; padding:0; }
      .wrap { max-width: 1100px; margin: 0 auto; padding: 24px; background:#ffffff; }

      .header-main {
        display:flex; align-items:center; justify-content:space-between;
        border-bottom:2px solid #000; padding-bottom:8px; margin-bottom:16px;
      }

      .logo-box { width: 180px; text-align:left; padding:0; }
      .logo-box img { max-width:150px; max-height:80px; display:block; }

      .title-box { flex:1; text-align:center; font-size:22px; font-weight:bold; color:#000; }

      .info-box { width:200px; border:1px solid #000; font-size:13px; padding:6px 10px; background:#fff; color:#000; }
      .info-row { display:flex; justify-content:space-between; padding:2px 0; }
      .info-label { font-weight:bold; margin-right:6px; }

      .print-toolbar.no-print {
        display:flex; justify-content:flex-end; gap:8px; margin: 6px 0 12px;
      }
      .print-btn {
        padding:8px 14px; border:1px solid #d0d7de; border-radius:8px; background:#f6f8fa;
        cursor:pointer; font-size:14px;
      }
      .print-btn:hover { background:#eef2f6; }

      .cardbar { display:grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0 20px; }
      @media (max-width:800px) { .cardbar { grid-template-columns: 1fr; } }
      .card { background:#f8fafc; border:1px solid #ccc; border-radius:6px; padding:10px; color:#000; }

      .card .k { font-size: 12px; color:#444; margin-bottom: 2px; }
      .card .v { font-size: 16px; font-weight: 600; }

      table { border-collapse: collapse; width:100%; font-size: 13px; margin-top:12px; background:#fff; color:#000; }
      thead th { text-align:left; border-bottom:2px solid #000; padding:8px; background:#f3f3f3; color:#000; }
      tbody td { border-bottom:1px solid #ccc; padding:6px; }
      tbody tr:nth-child(even) td { background:#fafafa; }

      @media print {
        .no-print { display:none !important; }
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      }
    </style>
    """

    cards_html = "".join(
        f'<div class="card"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for (k, v) in total_pairs
    )

    logo_html = f'<img src="{logo_data_uri}" alt="Logo">' if logo_data_uri else ""

    html = f"""{css}
    <div class="wrap">
      <div class="header-main">
        <div class="logo-box">{logo_html}</div>
        <div class="title-box">{titulo}</div>
        <div class="info-box">
          <div class="info-row"><span class="info-label">FO-FAT</span><span>019</span></div>
          <div class="info-row"><span class="info-label">Revisão</span><span>00</span></div>
          <div class="info-row"><span class="info-label">Unidade</span><span>{st.session_state.get("unidade") or ""}</span></div>
        </div>
      </div>

      <div class="print-toolbar no-print">
        <button class="print-btn" onclick="window.print()">🖨️ Imprimir</button>
      </div>

      <div style="margin-bottom:8px; font-size:13px;">
        <strong>Convênio:</strong> {convenio} &nbsp;|&nbsp; <strong>Competência:</strong> {data_str}
      </div>

      <div class="cardbar">{cards_html}</div>

      <div class="table">{table_html}</div>
    </div>"""
    return html

# =============================================================================
# Relatórios (abas)
# =============================================================================

def render_relatorio_remessas(
    df: pd.DataFrame,
    totals: dict,
    selected_date: date,
    selected_convenio: str,
    json_path: str | None,
    modelo_csv: str | None,
    df_recursos: pd.DataFrame | None,
    recursos_totais: dict | None,
    unidade: str,
):
    st.subheader("Relatório — Pagamento de Remessas")

    if df is None or len(df) == 0:
        st.info("Nenhum dado para a data informada.")
        return

    try:
        st.dataframe(
            df, hide_index=True, use_container_width=True,
            column_config={
                "Valor envio XML - Remessa": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor pgto": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor glosado": st.column_config.NumberColumn(format="R$ %.2f"),
                "Imposto": st.column_config.NumberColumn(format="R$ %.2f"),
                "Glosa mantida": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
    except Exception:
        st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Valor total envio XML", _fmt_brl(totals.get("total_envio_xml", 0)))
        st.metric("Valor total glosado", _fmt_brl(totals.get("total_glosado", 0)))
    with c2:
        st.metric("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0)))
        st.metric("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0)))
    with c3:
        st.metric("Valor total pago", _fmt_brl(totals.get("total_pago", 0)))
        st.metric("Número de remessas", f"{len(df)}")

    st.session_state["remessas_df"] = df
    st.session_state["remessas_totais"] = totals
    st.markdown("---")
    st.markdown("### Exportar lançamentos contábeis")

    if df_recursos is None:
        df_recursos = pd.DataFrame()
    if recursos_totais is None:
        recursos_totais = {}

    fname, csv_bytes = gerar_csv_lancamentos_bytes(
        df_remessas=df,
        rem_totals=totals,
        df_recursos=df_recursos,
        rec_totals=recursos_totais,
        selected_date=selected_date,
        selected_convenio=selected_convenio,
        modelo_csv_path=modelo_csv or "",
    )

    st.download_button(
        f"⬇️ Baixar CSV ({selected_convenio})",
        data=csv_bytes,
        file_name=fname,
        mime="text/csv",
        use_container_width=True,
        key="dl_csv_convenio",
    )

    st.markdown("### Versão para impressão")
    if not st.session_state.get("logo_data_uri"):
        st.session_state["logo_data_uri"] = _path_to_data_uri(
            st.session_state.get("logo_path") or LOGO_PATH
        )

    dfp = _df_for_print(
        df,
        ["Valor envio XML - Remessa", "Valor pgto", "Valor glosado", "Imposto", "Glosa mantida"],
    )
    table_html = dfp.to_html(index=False, border=0, escape=False)

    total_pairs = [
        ("Valor total envio XML", _fmt_brl(totals.get("total_envio_xml", 0))),
        ("Valor total glosado", _fmt_brl(totals.get("total_glosado", 0))),
        ("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0))),
        ("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0))),
        ("Valor total pago", _fmt_brl(totals.get("total_pago", 0))),
        ("Número de remessas", f"{len(df)}"),
    ]

    html = _build_print_html(
        titulo="Relatório — Pagamento de Remessas",
        convenio=selected_convenio,
        data_str=selected_date.strftime("%d/%m/%Y"),
        table_html=table_html,
        total_pairs=total_pairs,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=800, scrolling=True)

def render_relatorio_recursos(
    df: pd.DataFrame,
    totals: dict,
    selected_date: date,
    selected_convenio: str,
    unidade: str,
):
    st.subheader("Relatório — Recurso de Glosa")

    if df is None or len(df) == 0:
        st.info("Nenhum dado para a data informada.")
        return

    try:
        st.dataframe(
            df, hide_index=True, use_container_width=True,
            column_config={
                "Valor glosado": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor pago": st.column_config.NumberColumn(format="R$ %.2f"),
                "Imposto": st.column_config.NumberColumn(format="R$ %.2f"),
                "Glosa mantida": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
    except Exception:
        st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Valor total de Glosa", _fmt_brl(totals.get("total_glosa", 0)))
        st.metric("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0)))
    with c2:
        st.metric("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0)))
        st.metric("Valor total pago", _fmt_brl(totals.get("total_pago", 0)))
    with c3:
        st.metric("Número de remessas", f"{len(df)}")

    st.markdown("---")
    st.markdown("### Exportar lançamentos de recebimento de recurso de glosa")

    rem_df_ss = st.session_state.get("remessas_df")
    rem_totais_ss = st.session_state.get("remessas_totais") or {}

    fname_rec, csv_bytes_rec = gerar_csv_recursos_bytes(
        df_recursos=df,
        rec_totals=totals,
        df_remessas=rem_df_ss,
        rem_totals=rem_totais_ss,
        selected_date=selected_date,
        selected_convenio=selected_convenio,
        add_debito_if_only_resources=True,
    )

    st.download_button(
        f"⬇️ Baixar CSV de recursos ({selected_convenio})",
        data=csv_bytes_rec,
        file_name=fname_rec,
        mime="text/csv",
        use_container_width=True,
        key="dl_csv_recursos",
    )

    st.markdown("### Versão para impressão")
    if not st.session_state.get("logo_data_uri"):
        st.session_state["logo_data_uri"] = _path_to_data_uri(
            st.session_state.get("logo_path") or LOGO_PATH
        )
    dfp = _df_for_print(
        df,
        ["Valor glosado", "Valor pago", "Imposto", "Glosa mantida"],
    )
    table_html = dfp.to_html(index=False, border=0, escape=False)

    total_pairs = [
        ("Valor total de Glosa", _fmt_brl(totals.get("total_glosa", 0))),
        ("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0))),
        ("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0))),
        ("Valor total pago", _fmt_brl(totals.get("total_pago", 0))),
        ("Número de remessas", f"{len(df)}"),
    ]

    html = _build_print_html(
        titulo="Relatório — Recurso de Glosa",
        convenio=selected_convenio,
        data_str=selected_date.strftime("%d/%m/%Y"),
        table_html=table_html,
        total_pairs=total_pairs,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=800, scrolling=True)
