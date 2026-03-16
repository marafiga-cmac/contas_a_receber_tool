"""Templates HTML e helpers visuais compartilhados pelos relatórios."""

from __future__ import annotations

import base64
import mimetypes

import pandas as pd
import streamlit as st

from ...config import APP_ICON_PATH

LOGO_PATH = str(APP_ICON_PATH) if APP_ICON_PATH.exists() else ""

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



def ensure_logo_defaults() -> None:
    if "logo_path" not in st.session_state:
        st.session_state["logo_path"] = LOGO_PATH
    if not st.session_state.get("logo_data_uri"):
        st.session_state["logo_data_uri"] = _path_to_data_uri(st.session_state["logo_path"])


ensure_logo_defaults()

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


def _build_print_html_capa(titulo, data_str, table_html, logo_data_uri=None):
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

        </div>
    </body>
    </html>
    """

    return html

