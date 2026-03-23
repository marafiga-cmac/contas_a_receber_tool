"""Processamento de faturamento para convênio Ipê."""

from __future__ import annotations

from io import BytesIO
import pandas as pd

from ..utils.normalizers import _dedupe_headers, _drop_nan_only_columns, _drop_rows_without_inicio
from ..utils.parsers import _excel_col_idx


def processar_ipe_arquivos(uploaded_files) -> pd.DataFrame:
    """
    Recebe lista de UploadedFile do Streamlit referentes ao convênio Ipê.
    Realiza o tratamento reproduzindo as mesmas regras e validações do Cabergs ID.
    - Resolve cabeçalhos a partir da 11ª linha
    - Extrai metadados chaves (Remessa, Competência)
    - Retorna um DataFrame consolidado, sanitizado e tipado.
    """
    if not uploaded_files:
        return pd.DataFrame()

    frames = []

    for uf in uploaded_files:
        name = getattr(uf, "name", "arquivo")
        raw = uf.read()
        ext = name.lower().split(".")[-1]

        # -----------------------
        # Caso XLSX: openpyxl
        # -----------------------
        if ext == "xlsx":
            try:
                import openpyxl
                wb = openpyxl.load_workbook(BytesIO(raw), data_only=True)
                ws = wb.active

                # valores importantes iguais ao cabergs
                remessa = ws["G5"].value
                competencia = ws["X5"].value

                # corrigir cabeçalho (linha 11)
                row_header = 11
                # B -> C
                ws.cell(row_header, _excel_col_idx("C")).value = ws.cell(row_header, _excel_col_idx("B")).value
                ws.cell(row_header, _excel_col_idx("B")).value = None
                # AB -> AF
                ws.cell(row_header, _excel_col_idx("AF")).value = ws.cell(row_header, _excel_col_idx("AB")).value
                ws.cell(row_header, _excel_col_idx("AB")).value = None
                # AQ -> AR
                ws.cell(row_header, _excel_col_idx("AR")).value = ws.cell(row_header, _excel_col_idx("AQ")).value
                ws.cell(row_header, _excel_col_idx("AQ")).value = None

                start_col = _excel_col_idx("B")
                max_col = ws.max_column

                headers = []
                for c in range(start_col, max_col + 1):
                    raw_val = ws.cell(row_header, c).value
                    if raw_val is None:
                        col_name = f"COL_{c}"
                    else:
                        s = str(raw_val).strip()
                        if s == "" or s.lower() == "nan":
                            col_name = f"COL_{c}"
                        else:
                            col_name = s
                    headers.append(col_name)

                headers = _dedupe_headers(headers)
                col_indices = list(range(start_col, max_col + 1))

                data_rows = []
                for r in range(row_header + 1, ws.max_row + 1):
                    row_vals = [ws.cell(r, c).value for c in col_indices]
                    # pula linha complementamente vazia
                    if all(v is None or str(v).strip() == "" for v in row_vals):
                        continue
                    data_rows.append(row_vals)

                df = pd.DataFrame(data_rows, columns=headers)
                df.columns = _dedupe_headers(df.columns.tolist())

                df = _drop_nan_only_columns(df)
                df = _drop_rows_without_inicio(df, "Início")

            except Exception as e:
                df = pd.DataFrame([{"Arquivo": name, "Erro": f"Falha ao ler XLSX Ipê: {e}"}])
                remessa, competencia = None, None

        # -----------------------
        # Caso XLS: pandas (xlrd)
        # -----------------------
        elif ext == "xls":
            try:
                raw_df = pd.read_excel(BytesIO(raw), header=None, engine="xlrd")

                # G5 e X5
                remessa = raw_df.iat[4, _excel_col_idx("G") - 1] if raw_df.shape[0] > 4 and raw_df.shape[1] > (_excel_col_idx("G") - 1) else None
                competencia = raw_df.iat[4, _excel_col_idx("X") - 1] if raw_df.shape[0] > 4 and raw_df.shape[1] > (_excel_col_idx("X") - 1) else None

                # Header adjustments (linha 11)
                hr = 10
                raw_df.iat[hr, _excel_col_idx("C") - 1] = raw_df.iat[hr, _excel_col_idx("B") - 1]
                raw_df.iat[hr, _excel_col_idx("B") - 1] = None
                raw_df.iat[hr, _excel_col_idx("AF") - 1] = raw_df.iat[hr, _excel_col_idx("AB") - 1]
                raw_df.iat[hr, _excel_col_idx("AB") - 1] = None
                raw_df.iat[hr, _excel_col_idx("AR") - 1] = raw_df.iat[hr, _excel_col_idx("AQ") - 1]
                raw_df.iat[hr, _excel_col_idx("AQ") - 1] = None

                start_c = _excel_col_idx("B") - 1
                headers = raw_df.iloc[hr, start_c:].tolist()
                headers = [
                    f"COL_{start_c+i+1}" if (h is None or str(h).strip() == "") else str(h).strip()
                    for i, h in enumerate(headers)
                ]

                df = raw_df.iloc[hr+1:, start_c:].copy()
                df.columns = _dedupe_headers(headers)
                df = df.dropna(how="all")

                df = _drop_nan_only_columns(df)
                df = _drop_rows_without_inicio(df, "Início")

            except Exception as e:
                df = pd.DataFrame([{"Arquivo": name, "Erro": f"Falha ao ler XLS Ipê: {e}"}])
                remessa, competencia = None, None

        else:
            df = pd.DataFrame([{"Arquivo": name, "Erro": "Extensão não suportada"}])
            remessa, competencia = None, None

        # Injection metadata columns
        for meta_col in ["Arquivo", "Remessa (G5)", "Competência (X5)", "Origem Extração"]:
            if meta_col in df.columns:
                df = df.rename(columns={meta_col: f"{meta_col} (orig)"})

        df.insert(0, "Arquivo", name)
        df.insert(1, "Remessa (G5)", remessa)
        df.insert(2, "Competência (X5)", competencia)
        df.insert(3, "Origem Extração", "Identificação Ipê")

        df.columns = _dedupe_headers(df.columns.tolist())
        df = _drop_nan_only_columns(df)
        df = _drop_rows_without_inicio(df, "Início")

        frames.append(df)

    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out = _drop_nan_only_columns(out)
    out = _drop_rows_without_inicio(out, "Início")

    return out
