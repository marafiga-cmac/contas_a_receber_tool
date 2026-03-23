"""Gestão do banco de dados SQLite nativo do projeto."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path("database.db")

def save_dataframe_to_sqlite(df: pd.DataFrame, table_name: str) -> int:
    """
    Salva um DataFrame numera banco de dados SQLite local.
    Se a tabela não existir, será criada automaticamente usando o layout do DataFrame.
    
    Args:
        df: DataFrame com os dados a serem iterados.
        table_name: O nome da tabela de destino.
        
    Returns:
        int: O número de registros afetados.
    """
    if df is None or df.empty:
        return 0

    # Força os cabeçalhos de colunas do DataFrame a ser string, 
    # proativamente removendo caracteres perigosos de SQL
    df.columns = df.columns.astype(str).str.replace(r"[^\w\s_]", "", regex=True)

    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)
        return len(df)
