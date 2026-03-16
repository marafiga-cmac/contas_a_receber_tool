"""Geração de arquivos CSV contábeis."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

import pandas as pd

# ---- Streamlit é opcional aqui (rodamos sem falhar fora do Streamlit) ----
try:
    import streamlit as st  # para ler session_state se existir
except Exception:  # pragma: no cover
    st = None

from ..domain.csv_layouts import CSV_COLS, CSV_DELIM
from ..utils.formatting import _ensure_len, _fmt_ref_mmYYYY, _fmt_amount_csv, _slugify

def gerar_csv_glosa_mantida_bytes(
    items: list[dict],
    encoding: str = "cp1252",
):
    """Gera CSV de lançamentos contábeis para *Glosa Mantida* (manual).

    Cada item gera 2 linhas (padrão do seu template de importação):
      - Débito:  3149021 / restrição "2"  / valor positivo
      - Crédito: 1133004 / restrição "0A" / valor negativo

    Observações:
      - A subconta é a mesma lógica dos demais relatórios (SUBCONTA_MAP + overrides).
      - A 1ª linha do CSV ("header_first_row") segue o mesmo padrão dos outros CSVs.
    """

    import io
    import csv as _csv
    import unicodedata

    # ---- prefs / overrides / unidade (igual outras funções de CSV) ----
    prefs: dict = {}
    ovrs: dict = {}
    unidade: str = ""
    if st is not None:
        try:
            prefs = st.session_state.get("csv_prefs", {}) or {}
            ovrs = st.session_state.get("csv_convenio_overrides", {}) or {}
            unidade = st.session_state.get("unidade", "") or ""
        except Exception:
            prefs, ovrs, unidade = {}, {}, ""

    header_first_row = prefs.get("header_first_row")
    if not header_first_row:
        header_first_row = (
            ("1941", "Clínica Adventista de Curitiba - IASBS")
            if (unidade or "").upper() == "CMAC"
            else ("1841", "Clínica Adventista de Porto Alegre - IASBS")
        )

    # Mesmo SUBCONTA_MAP usado nas outras funções
    SUBCONTA_MAP = {
        "Afpergs": "13",
        "Proasa": "51",
        "Amil": "39",
        "Assefaz": "27",
        "Banco Central": "43",
        "Cassi": "26",
        "Doctor": "54",
        "Embratel": "18",
        "Humana": "55",
        "GEAP": "19",
        "Geap": "19",
        "Postal Saúde": "29",
        "Prevent Senior": "91",
        "Saúde Caixa": "15",
        "Medservice": "16",
        "Life": "45",
        "Gente Saúde": "59",
        "Capesesp": "20",
        "Ipê Saúde": "12",
    }

    def _nfc(s):
        return unicodedata.normalize("NFC", s) if isinstance(s, str) else s

    rows = [_ensure_len(list(header_first_row), CSV_COLS)]

    total = 0.0
    for it in (items or []):
        try:
            convenio = str(it.get("convenio") or "").strip()
            desc = str(it.get("descricao") or it.get("desc") or "").strip()
            val = it.get("valor")

            # converte valor
            try:
                val_f = float(val)
            except Exception:
                s = str(val).strip().replace("R$", "").replace(" ", "")
                if "," in s and "." in s:
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s:
                    s = s.replace(",", ".")
                val_f = float(s) if s else 0.0

            if not convenio or not desc or val_f == 0:
                continue

            oconv: dict = {}
            if isinstance(ovrs, dict):
                oconv = ovrs.get(convenio, {}) or {}

            subconta_convenio = (
                oconv.get("subconta_convenio")
                or SUBCONTA_MAP.get(convenio, "13")
            )

            total += float(val_f)

            # Débito
            rows.append(_ensure_len([
                "3149021", subconta_convenio, "10", "1110", "2",
                _fmt_amount_csv(val_f), "N", _nfc(desc),
            ], CSV_COLS))

            # Crédito
            rows.append(_ensure_len([
                "1133004", subconta_convenio, "10", "1110", "0A",
                "-" + _fmt_amount_csv(val_f), "N", _nfc(desc),
            ], CSV_COLS))

        except Exception:
            continue

    sio = io.StringIO()
    writer = _csv.writer(sio, delimiter=CSV_DELIM, lineterminator="\r\n")
    writer.writerows(rows)
    csv_text = sio.getvalue()
    csv_bytes = csv_text.encode(encoding, errors="replace")

    from datetime import date as _date

    date_str = _date.today().strftime("%Y%m%d")
    n = int(len(items or []))
    fname = f"lanc_glosa_mantida_{date_str}_n{n}_total{float(total):.2f}.csv"
    return fname, csv_bytes

# ------------------------- Geração do CSV de lançamentos --------------------
# (mantido igual ao original do usuário, apenas limpeza leve e comentários)
# ... (mantido integralmente a partir daqui) ...

def gerar_csv_lancamentos_bytes(
    df_remessas: pd.DataFrame,
    rem_totals: Dict[str, float],
    df_recursos: pd.DataFrame,
    rec_totals: Dict[str, float],
    selected_date: date,
    selected_convenio: str,
    modelo_csv_path: Optional[str] = None,
    encoding: str = "cp1252",
):
    import io, csv, unicodedata

    prefs: dict = {}
    ovrs: dict = {}
    unidade: str = ""
    if st is not None:
        try:
            prefs = st.session_state.get("csv_prefs", {}) or {}
            ovrs = st.session_state.get("csv_convenio_overrides", {}) or {}
            unidade = st.session_state.get("unidade", "") or ""
        except Exception:
            prefs, ovrs, unidade = {}, {}, ""

    oconv: dict = {}
    if isinstance(ovrs, dict):
        oconv = ovrs.get(selected_convenio, {}) or {}

    header_first_row = prefs.get("header_first_row")
    if not header_first_row:
        if (unidade or "").upper() == "CMAC":
            header_first_row = ("1941", "Clínica Adventista de Curitiba - IASBS")
        else:
            header_first_row = ("1841", "Clínica Adventista de Porto Alegre - IASBS")

    deposito_subconta_banco = (
        oconv.get("deposito_subconta_banco")
        or prefs.get("deposito_subconta_banco")
        or ("03645/00044210" if (unidade or "").upper() == "CMAC" else "3708/0001649-7")
    )

    deposito_prefix = (prefs.get("deposito_prefix") or ("Ac. Depósito")).strip()
    if not deposito_prefix.lower().startswith("ac."):
        deposito_prefix = f"Ac. {deposito_prefix.lstrip()}"

    oconv = ovrs.get(selected_convenio, {})

    SUBCONTA_MAP = {
        "Afpergs": "13", "Proasa": "51", 
        "Amil": "39","Assefaz": "27","Banco Central": "43","Cassi": "26","Doctor": "54",
        "Embratel": "18","Humana": "55","GEAP": "19","Geap": "19",
        "Postal Saúde": "29","Prevent Senior": "91","Saúde Caixa": "15", "Mediservice": "16", "Life": "45",
        "Gente Saúde": "59", "Ipê Saúde": "12",
    }
    DEPOSITO_SUFFIX = {
        "Afpergs": "Assoc Func Publicos", "Proasa": "Proasa Programa Adven",
        "Amil": "Amil Assistencia Med","Assefaz": "Fundacao Assistencia",
        "Banco Central": "Pagamento Sigef Ap","Cassi": "Caixa de Assistencia",
        "Doctor": "Doctor Clin Ope De P","Embratel": "Telos Fundacao Embrat",
        "Humana": "Humana Saude Ltda","GEAP": "Geap Autogestao Em S","Geap": "Geap Autogestao Em S",
        "Postal Saúde": "Postal Saúde","Prevent Senior": "Prevent Senior Privat","Saúde Caixa": "Saúde Caixa",
        "Mediservice": "Ac. Mediservice Operadora Planos Sau","Life": "Ac. Life Empresarial Saúde Ltda",
        "Gente Saúde": "Ac. Gente Clube - Benefi", "Ipê Saúde": "Ac. Ipê Saúde",
    }

    subconta_convenio = oconv.get("subconta_convenio") or SUBCONTA_MAP.get(selected_convenio, "13")
    deposito_suffix = oconv.get("deposito_suffix") or DEPOSITO_SUFFIX.get(selected_convenio, selected_convenio)
    glosa_neg_target = oconv.get("glosa_neg_target") or ("1133003" if selected_convenio in ("Afpergs", "Proasa") else "1133001")

    def _nfc(s):
        return unicodedata.normalize("NFC", s) if isinstance(s, str) else s

    def _norm_str(x):
        return (str(x).strip() if x is not None else "").replace("\u00A0", " ")

    def _to_float(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        try:
            return float(v)
        except Exception:
            s = str(v).strip().replace("R$", "").replace(" ", "")
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            try:
                return float(s)
            except Exception:
                return None

    def _dedupe(df, keys):
        if df is None or len(df) == 0:
            return df
        df = df.copy()
        for c in ["Nº Remessa","Nº NF","Ref."]:
            if c in df.columns:
                df[c] = df[c].apply(_norm_str)
        for c in keys:
            if c in df.columns:
                df[c] = df[c].apply(_to_float)
        subset = [c for c in ["Nº Remessa","Nº NF","Ref."] + keys if c in df.columns]
        if subset:
            df = df.drop_duplicates(subset=subset, keep="first")
        else:
            df = df.drop_duplicates(keep="first")
        return df.dropna(how="all")

    df_remessas = _dedupe(df_remessas, ["Valor pgto","Valor glosado"])
    df_recursos = _dedupe(df_recursos, ["Valor pago"])

    rows = [_ensure_len(list(header_first_row), CSV_COLS)]

    total_debito = (rem_totals.get("total_pago") or 0.0) + (rec_totals.get("total_pago") or 0.0)

    # --- monta descrição do depósito SEMPRE com data; se o sufixo já vier com "Ac.", removemos para não duplicar
    dep_suffix_clean = str(deposito_suffix or "").strip()
    if dep_suffix_clean.lower().startswith("ac."):
        dep_suffix_clean = dep_suffix_clean[3:].lstrip(" -–—").strip()

    desc_deposito = _nfc(f"{deposito_prefix} {selected_date.strftime('%d/%m/%Y')} - {dep_suffix_clean}")


    rows.append(_ensure_len([
        "2162001", deposito_subconta_banco, "10", "1110", "0A",
        _fmt_amount_csv(total_debito), "N", desc_deposito
    ], CSV_COLS))

    deposito_prefix = (prefs.get("deposito_prefix") or "Ac. Depósito").strip()
    if not deposito_prefix.lower().startswith("ac."):
        deposito_prefix = f"Ac. {deposito_prefix.lstrip()}"

    if df_remessas is not None and len(df_remessas) > 0:
        for _, r in df_remessas.iterrows():
            num_remessa = str(r.get("Nº Remessa") or "").strip()
            num_nf = str(r.get("Nº NF") or "").strip()
            ref_fmt = _fmt_ref_mmYYYY(str(r.get("Ref.") or "").strip())

            val_pgto = r.get("Valor pgto")
            try:
                val_pgto = float(val_pgto) if val_pgto is not None else None
            except Exception:
                val_pgto = None
            if val_pgto is not None and not pd.isna(val_pgto) and val_pgto != 0:
                desc_rem = _nfc(f"Rec. Rem. {num_remessa} - NFSe {num_nf} - Fat. {ref_fmt}")
                rows.append(_ensure_len([
                    "1133001", subconta_convenio, "10", "1110", "0A",
                    "-" + _fmt_amount_csv(val_pgto), "N", desc_rem
                ], CSV_COLS))

            val_glosa = r.get("Valor glosado") or 0
            try:
                val_glosa = float(val_glosa)
            except Exception:
                val_glosa = 0.0

            if abs(val_glosa) > 0:
                if glosa_neg_target == "1133001":
                    desc_g = _nfc(f"Glosa S/Rem. {num_remessa} - NFSe {num_nf} - Fat. {ref_fmt}")
                else:
                    desc_g = _nfc(f"Glosa S/Rem. {num_remessa} - Faturamento Plano de Saúde - {ref_fmt}")

                rows.append(_ensure_len([
                    "1133004", subconta_convenio, "10", "1110", "0A",
                    _fmt_amount_csv(val_glosa), "N", desc_g
                ], CSV_COLS))
                rows.append(_ensure_len([
                    glosa_neg_target, subconta_convenio, "10", "1110", "0A",
                    "-" + _fmt_amount_csv(val_glosa), "N", desc_g
                ], CSV_COLS))

    if df_recursos is not None and len(df_recursos) > 0:
        for _, r in df_recursos.iterrows():
            num_remessa = str(r.get("Nº Remessa") or "").strip()
            num_nf = str(r.get("Nº NF") or "").strip()
            ref_fmt = _fmt_ref_mmYYYY(str(r.get("Ref.") or "").strip())

            val_pago = r.get("Valor pago")
            try:
                val_pago = float(val_pago) if val_pago is not None else None
            except Exception:
                val_pago = None
            if val_pago is not None and not pd.isna(val_pago) and val_pago != 0:
                desc_rec = _nfc(f"Rec. Rem. {num_remessa} - NFSe {num_nf} - Rg. {ref_fmt}")
                rows.append(_ensure_len([
                    "1133001", subconta_convenio, "10", "1110", "0A",
                    "-" + _fmt_amount_csv(val_pago), "N", desc_rec
                ], CSV_COLS))

    import io, csv as _csv
    sio = io.StringIO()
    writer = _csv.writer(sio, delimiter=CSV_DELIM, lineterminator="\r\n")
    writer.writerows(rows)
    csv_text = sio.getvalue()
    csv_bytes = csv_text.encode(encoding, errors="replace")

    conv_slug = _slugify(selected_convenio)
    date_str = selected_date.strftime("%Y%m%d")
    n_rem = int(len(df_remessas) if df_remessas is not None else 0)
    n_rec = int(len(df_recursos) if df_recursos is not None else 0)
    total_str = f"{float(total_debito):.2f}"
    fname = f"lanc_{conv_slug}_{date_str}_rem{n_rem}_rec{n_rec}_total{total_str}.csv"
    return fname, csv_bytes

def gerar_csv_recursos_bytes(
    df_recursos: pd.DataFrame,
    rec_totals: Dict[str, float],
    df_remessas: Optional[pd.DataFrame],
    rem_totals: Dict[str, float],
    selected_date: date,
    selected_convenio: str,
    modelo_csv_path: Optional[str] = None,
    encoding: str = "cp1252",
    add_debito_if_only_resources: bool = True,
):
    import io, csv as _csv, unicodedata

    prefs: dict = {}
    ovrs: dict = {}
    unidade: str = ""
    if st is not None:
        try:
            prefs = st.session_state.get("csv_prefs", {}) or {}
            ovrs = st.session_state.get("csv_convenio_overrides", {}) or {}
            unidade = st.session_state.get("unidade", "") or ""
        except Exception:
            prefs, ovrs, unidade = {}, {}, ""

    oconv: dict = {}
    if isinstance(ovrs, dict):
        oconv = ovrs.get(selected_convenio, {}) or {}

    header_first_row = prefs.get("header_first_row")
    if not header_first_row:
        header_first_row = ("1941", "Clínica Adventista de Curitiba - IASBS") if (unidade or "").upper() == "CMAC" \
                           else ("1841", "Clínica Adventista de Porto Alegre - IASBS")

    deposito_subconta_banco = (
        oconv.get("deposito_subconta_banco")
        or prefs.get("deposito_subconta_banco")
        or ("03645/00044210" if (unidade or "").upper() == "CMAC" else "3708/0001649-7")
    )

    deposito_prefix = (prefs.get("deposito_prefix") or "Ac. Depósito").strip()
    if not deposito_prefix.lower().startswith("ac."):
        deposito_prefix = f"Ac. {deposito_prefix.lstrip()}"

    SUBCONTA_MAP = {
        "Afpergs": "13", "Proasa": "51",
        "Amil": "39","Assefaz": "27","Banco Central": "43","Cassi": "26","Doctor": "54",
        "Embratel": "18","Humana": "55","GEAP": "19","Geap": "19",
        "Postal Saúde": "29","Prevent Senior": "91","Saúde Caixa": "15",
        "Medservice": "16", "Life": "45", "Gente Saúde": "59", "Capesesp": "20", "Ipê Saúde": "12",
    }
    DEPOSITO_SUFFIX = {
        "Afpergs": "Assoc Func Publicos", "Proasa": "Proasa",
        "Amil": "Amil Assistencia Med","Assefaz": "Fundacao Assistencia",
        "Banco Central": "Pagamento Sigef Ap","Cassi": "Caixa de Assistencia",
        "Doctor": "Doctor Clin Ope De P","Embratel": "Telos Fundacao Embrat",
        "Humana": "Humana Saude Ltda","GEAP": "Geap Autogestao Em S","Geap": "Geap Autogestao Em S",
        "Postal Saúde": "Postal Saúde","Prevent Senior": "Prevent Senior Privat","Saúde Caixa": "Saúde Caixa",
        "Mediservice": "Ac. Mediservice Operadora Planos Sau",
        "Life": "Ac. Life Empresarial Saúde Ltda",
        "Gente Saúde": "Ac. Gente Clube - Benefi", "Capesesp": "Caixa De Previdencia", "Ipê Saúde": "Ipê Saúde",
    }

    subconta_convenio = oconv.get("subconta_convenio") or SUBCONTA_MAP.get(selected_convenio, "13")
    deposito_suffix = oconv.get("deposito_suffix") or DEPOSITO_SUFFIX.get(selected_convenio, selected_convenio)
    glosa_neg_target = oconv.get("glosa_neg_target") or ("1133003" if selected_convenio in ("Afpergs", "Proasa") else "1133001")

    def _nfc(s): return unicodedata.normalize("NFC", s) if isinstance(s, str) else s

    def _norm_str(x): return (str(x).strip() if x is not None else "").replace("\u00A0", " ")
    def _to_float(v):
        if v is None or (isinstance(v, float) and pd.isna(v)): return None
        try: return float(v)
        except Exception:
            s = str(v).strip().replace("R$","").replace(" ","")
            if "," in s and "." in s: s = s.replace(".","").replace(",",".")
            elif "," in s: s = s.replace(",",".")
            try: return float(s)
            except Exception: return None
    def _dedupe_recursos(df):
        if df is None or len(df) == 0: return df
        df = df.copy()
        for c in ["Nº Remessa","Nº NF","Ref."]:
            if c in df.columns: df[c] = df[c].apply(_norm_str)
        if "Valor pago" in df.columns: df["Valor pago"] = df["Valor pago"].apply(_to_float)
        subset = [c for c in ["Nº Remessa","Nº NF","Ref.","Valor pago"] if c in df.columns]
        if subset: df = df.drop_duplicates(subset=subset, keep="first")
        else: df = df.drop_duplicates(keep="first")
        return df.dropna(how="all")

    df_recursos = _dedupe_recursos(df_recursos)

    rows = [_ensure_len(list(header_first_row), CSV_COLS)]

    total_remessas_pago = float(rem_totals.get("total_pago") or 0.0)
    total_recursos_pago = float(rec_totals.get("total_pago") or 0.0)
    is_only_resources_day = (total_remessas_pago == 0.0) and (df_remessas is None or len(df_remessas) == 0)

    if add_debito_if_only_resources and is_only_resources_day and total_recursos_pago > 0:
        dep_suffix_clean = str(deposito_suffix or "").strip()
        if dep_suffix_clean.lower().startswith("ac."):
            dep_suffix_clean = dep_suffix_clean[3:].lstrip(" -–—").strip()

        desc_deposito = _nfc(f"{deposito_prefix} {selected_date.strftime('%d/%m/%Y')} - {dep_suffix_clean}")

        rows.append(_ensure_len([
            "2162001", deposito_subconta_banco, "10", "1110", "0A",
            _fmt_amount_csv(total_recursos_pago), "N", desc_deposito
        ], CSV_COLS))

    if df_recursos is not None and len(df_recursos) > 0:
        for _, r in df_recursos.iterrows():
            num_remessa = str(r.get("Nº Remessa") or "").strip()
            num_nf = str(r.get("Nº NF") or "").strip()
            ref_fmt = _fmt_ref_mmYYYY(str(r.get("Ref.") or "").strip())

            val_pago = r.get("Valor pago")
            try:
                val_pago = float(val_pago) if val_pago is not None else None
            except Exception:
                val_pago = None
            if val_pago is None or pd.isna(val_pago) or val_pago == 0:
                continue

            if glosa_neg_target == "1133001":
                conta = "1133004"
                desc_rec = _nfc(f"Rec. Glosa S/Rem. {num_remessa} - NFSe {num_nf} - Fat. {ref_fmt}")
            else:
                conta = "1133001"
                desc_rec = _nfc(f"Rec. Rem. {num_remessa} - NFSe {num_nf} - Rg. {ref_fmt}")

            rows.append(_ensure_len([
                conta, subconta_convenio, "10", "1110", "0A",
                "-" + _fmt_amount_csv(val_pago), "N", desc_rec
            ], CSV_COLS))

    sio = io.StringIO()
    writer = _csv.writer(sio, delimiter=CSV_DELIM, lineterminator="\r\n")
    writer.writerows(rows)
    csv_text = sio.getvalue()
    csv_bytes = csv_text.encode(encoding, errors="replace")

    conv_slug = _slugify(selected_convenio)
    date_str = selected_date.strftime("%Y%m%d")
    n_rec = int(len(df_recursos) if df_recursos is not None else 0)
    fname = f"lanc_recursos_{conv_slug}_{date_str}_n{n_rec}_total{total_recursos_pago:.2f}.csv"
    return fname, csv_bytes

def gerar_csv_nfse_lancamentos_bytes(
    df_nfse: pd.DataFrame,
    selected_convenio: str,
    referencia_str: Optional[str] = None,
    encoding: str = "cp1252",
):
    """
    Gera CSV de lançamentos contábeis para o Relatório NFS-e.

    Regra pedida:
      - Para cada linha/remessa do relatório:
          • 1 lançamento na conta 1133001 (Débito / +)
          • 1 lançamento na conta 1133003 (Crédito / -)
        Usando a MESMA lógica de subconta dos demais CSVs (SUBCONTA_MAP + overrides).
        Descrição:
          "Rem. (Nº Remessa) - NFSe (Nº NF) - Fat. (Ref.)"
    """
    import io, csv as _csv, unicodedata

    # ---- prefs / overrides / unidade (igual outras funções de CSV) ----
    prefs: dict = {}
    ovrs: dict = {}
    unidade: str = ""
    if st is not None:
        try:
            prefs = st.session_state.get("csv_prefs", {}) or {}
            ovrs = st.session_state.get("csv_convenio_overrides", {}) or {}
            unidade = st.session_state.get("unidade", "") or ""
        except Exception:
            prefs, ovrs, unidade = {}, {}, ""

    oconv: dict = {}
    if isinstance(ovrs, dict):
        oconv = ovrs.get(selected_convenio, {}) or {}

    header_first_row = prefs.get("header_first_row")
    if not header_first_row:
        header_first_row = (
            ("1941", "Clínica Adventista de Curitiba - IASBS")
            if (unidade or "").upper() == "CMAC"
            else ("1841", "Clínica Adventista de Porto Alegre - IASBS")
        )

    # Mesmo SUBCONTA_MAP usado nas outras funções
    SUBCONTA_MAP = {
        "Afpergs": "13",
        "Proasa": "51",
        "Amil": "39",
        "Assefaz": "27",
        "Banco Central": "43",
        "Cassi": "26",
        "Doctor": "54",
        "Embratel": "18",
        "Humana": "55",
        "GEAP": "19",
        "Geap": "19",
        "Postal Saúde": "29",
        "Prevent Senior": "91",
        "Saúde Caixa": "15",
        "Medservice": "16",
        "Life": "45",
        "Gente Saúde": "59",
        "Capesesp": "20",
        "Ipê Saúde": "12",
    }

    subconta_convenio = (
        oconv.get("subconta_convenio")
        or SUBCONTA_MAP.get(selected_convenio, "13")
    )

    def _nfc(s):
        return unicodedata.normalize("NFC", s) if isinstance(s, str) else s

    def _to_float(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        try:
            return float(v)
        except Exception:
            s = str(v).strip().replace("R$", "").replace(" ", "")
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            try:
                return float(s)
            except Exception:
                return None

    # ---- se não tiver dados, só devolve o cabeçalho ----
    rows = [_ensure_len(list(header_first_row), CSV_COLS)]
    if df_nfse is None or len(df_nfse) == 0:
        sio = io.StringIO()
        w = _csv.writer(sio, delimiter=CSV_DELIM, lineterminator="\r\n")
        w.writerows(rows)
        csv_bytes = sio.getvalue().encode(encoding, errors="replace")
        conv_slug = _slugify(selected_convenio)
        fname = f"lanc_nfse_{conv_slug}_vazio.csv"
        return fname, csv_bytes

    total_debito = 0.0
    n_itens = 0

    # Garante colunas esperadas
    for c in ["Nº Remessa", "Nº NF", "NF recurso", "Ref.", "Valor NF"]:
        if c not in df_nfse.columns:
            df_nfse[c] = None

    for _, r in df_nfse.iterrows():
        num_remessa = str(r.get("Nº Remessa") or "").strip()

        # Número de NF a usar na descrição:
        # - Para "RG" (NF encontrada em NF recurso), usa o campo "NF recurso"
        # - Caso contrário, usa "Nº NF" (padrão)
        nf_normal = str(r.get("Nº NF") or "").strip()
        nf_recurso = str(r.get("NF recurso") or "").strip()
        match_kind = str(r.get("_nfse_match_kind") or "").strip().lower()
        ref_raw = str(r.get("Ref.") or "").strip()
        ref_fmt = _fmt_ref_mmYYYY(ref_raw)

        is_rg = (match_kind in ("recurso", "rg")) or ref_raw.strip().lower().startswith("rg")
        nf_to_use = nf_recurso if (is_rg and nf_recurso) else (nf_normal or nf_recurso)

        # Valor a lançar:
        # - RG => Valor recursado
        # - normal => Valor NF
        if is_rg:
            valor_lanc = _as_number(r.get("Valor recursado"))
        else:
            valor_lanc = _as_number(r.get("Valor NF"))

        valor_lanc = float(valor_lanc or 0.0)
        if valor_lanc == 0:
            continue

        # Descrição:
        # Normal: "Rem. (N° Remessa) - NFSe (NFSe) - Fat. (Ref.)"
        # RG:     "... - NFSe (NF recurso) - Rg. (Ref.)"
        if is_rg:
            desc = f"Rem. {num_remessa} - NFSe {nf_to_use} - Rg. {ref_fmt}"
        else:
            desc = f"Rem. {num_remessa} - NFSe {nf_to_use} - Fat. {ref_fmt}"

        # Contas:
        # - normal: débito 1133001 / crédito 1133003
        # - RG:     débito 1133001 / crédito 1133004
        conta_credito = "1133004" if is_rg else "1133003"

        rows.append(_ensure_len([
            "1133001", subconta_convenio, "10", "1110", "0A",
            _fmt_amount_csv(valor_lanc), "N", _nfc(desc)
        ], CSV_COLS))

        rows.append(_ensure_len([
            conta_credito, subconta_convenio, "10", "1110", "0A",
            "-" + _fmt_amount_csv(valor_lanc), "N", _nfc(desc)
        ], CSV_COLS))

    # ---- grava CSV ----
    sio = io.StringIO()
    writer = _csv.writer(sio, delimiter=CSV_DELIM, lineterminator="\r\n")
    writer.writerows(rows)
    csv_text = sio.getvalue()
    csv_bytes = csv_text.encode(encoding, errors="replace")

    conv_slug = _slugify(selected_convenio)
    ref_slug = _slugify(referencia_str) if referencia_str else ""
    total_str = f"{float(total_debito):.2f}"

    if ref_slug:
        fname = f"lanc_nfse_{conv_slug}_{ref_slug}_n{n_itens}_total{total_str}.csv"
    else:
        fname = f"lanc_nfse_{conv_slug}_n{n_itens}_total{total_str}.csv"

    return fname, csv_bytes

def gerar_csv_lancamentos_unimed_bytes(
    payload: dict,
    encoding: str = "cp1252",
):
    """
    Regras:
    - Débito: 1136001 / sub 1141, um lançamento por entidade com o SOMATÓRIO
      do 'Valor Reembolsado' dos itens daquela entidade.
      Descrição: "{Entidade} - Depósito C/c - Unimed"

    - Crédito: 1131001 / sub 1122, um lançamento por item (nome) daquela entidade,
      com o valor do 'Valor Reembolsado' (negativo).
      Descrição: 'NFSe {Número Nota Fiscal} - {Titular}'
    """
    import io, csv as _csv, unicodedata

    # Pega header_first_row do modelo padrão do teu sistema (igual as outras rotinas)
    prefs: dict = {}
    unidade: str = ""
    if st is not None:
        try:
            prefs = st.session_state.get("csv_prefs", {}) or {}
            unidade = st.session_state.get("unidade", "") or ""
        except Exception:
            prefs, unidade = {}, ""

    unid = (unidade or "").strip().upper()

    deb_subconta = "1141"

    if unid == "CMAP":
        cred_subconta = "1121"
    else:
        # padrão CMAC (e qualquer outro caso)
        cred_subconta = "1122"

    header_first_row = prefs.get("header_first_row")
    if not header_first_row:
        # mesmo padrão usado no resto do backend.py
        if (unidade or "").upper() == "CMAC":
            header_first_row = ("1941", "Clínica Adventista de Curitiba - IASBS")
        else:
            header_first_row = ("1841", "Clínica Adventista de Porto Alegre - IASBS")

    def _nfc(s):
        return unicodedata.normalize("NFC", s) if isinstance(s, str) else s

    def _to_float(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        try:
            return float(v)
        except Exception:
            s = str(v).strip().replace("R$", "").replace(" ", "")
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            try:
                return float(s)
            except Exception:
                return 0.0

    def _formatar_nome_titulo(nome: str) -> str:
        """
        Primeira letra maiúscula em cada palavra,
        mantendo conectores em minúsculo.
        """
        if not nome:
            return ""

        conectores = {
            "de", "da", "do", "das", "dos", "e"
        }

        partes = nome.strip().lower().split()
        resultado = []

        for p in partes:
            if p in conectores:
                resultado.append(p)
            else:
                resultado.append(p.capitalize())

        return " ".join(resultado)


    items = payload.get("items") or []
    if not items:
        # devolve só header, arquivo vazio
        rows = [_ensure_len(list(header_first_row), CSV_COLS)]
        sio = io.StringIO()
        w = _csv.writer(sio, delimiter=CSV_DELIM, lineterminator="\r\n")
        w.writerows(rows)
        return "lanc_unimed_vazio.csv", sio.getvalue().encode(encoding, errors="replace")

    # Monta DataFrame a partir do JSON (pega campos que você citou)
    base_rows = []
    for it in items:
        entidade = str(it.get("Entidade") or "").strip()
        titular = str(it.get("Titular") or "").strip()

        row_xlsx = it.get("row_xlsx") or {}
        nf = row_xlsx.get("Número Nota Fiscal")
        valor = row_xlsx.get("Valor Reembolsado")

        base_rows.append({
            "Entidade": entidade,
            "Titular": titular,
            "NumeroNF": "" if nf is None else str(nf).strip(),
            "ValorReembolsado": _to_float(valor),
        })

    df = pd.DataFrame(base_rows)
    df = df[df["Entidade"].astype(str).str.strip() != ""].copy()
    df = df[df["ValorReembolsado"] != 0].copy()

    # Header do arquivo
    rows = [_ensure_len(list(header_first_row), CSV_COLS)]

    # 1) DÉBITO por entidade (somatório)
    debitos = df.groupby("Entidade", dropna=False)["ValorReembolsado"].sum().reset_index()
    for _, r in debitos.iterrows():
        ent = str(r["Entidade"]).strip()
        total = float(r["ValorReembolsado"] or 0.0)
        if total == 0:
            continue

        desc = f"{ent} - Depósito C/c - Unimed"
        rows.append(_ensure_len([
            "1136001", deb_subconta, "10", "1110", "0A",
            _fmt_amount_csv(total), "N", _nfc(desc)
        ], CSV_COLS))

        # 2) CRÉDITO item a item (por pessoa) para essa entidade
        df_ent = df[df["Entidade"] == ent]
        for _, ri in df_ent.iterrows():
            valor_i = float(ri["ValorReembolsado"] or 0.0)
            if valor_i == 0:
                continue
            nf_i = str(ri["NumeroNF"] or "").strip()
            tit_raw = str(ri["Titular"] or "").strip()
            tit_fmt = _formatar_nome_titulo(tit_raw)
            desc_i = f"NFSe {nf_i} - {tit_fmt}".strip()

            rows.append(_ensure_len([
                "1131001", cred_subconta, "10", "1110", "0A",
                "-" + _fmt_amount_csv(valor_i), "N", _nfc(desc_i)
            ], CSV_COLS))

    # Gera bytes
    sio = io.StringIO()
    w = _csv.writer(sio, delimiter=CSV_DELIM, lineterminator="\r\n")
    w.writerows(rows)
    csv_bytes = sio.getvalue().encode(encoding, errors="replace")

    # Nome do arquivo
    total_geral = float(df["ValorReembolsado"].sum() or 0.0)
    fname = f"lanc_unimed_total{total_geral:.2f}.csv"
    return fname, csv_bytes

