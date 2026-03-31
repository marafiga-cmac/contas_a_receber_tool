"""Integração com Google Sheets."""

from __future__ import annotations

import os
from typing import List, Optional

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def _get_credentials(
    scopes: Optional[List[str]] = None,
    client_secrets_path: str = "client_secret.json",
    token_path: str = "token.json",
) -> Credentials:
    from google.auth.exceptions import RefreshError
    scopes = scopes or SCOPES

    def _save(creds: Credentials):
        os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except Exception:
            creds = None

    if creds and not creds.valid and creds.refresh_token:
        try:
            creds.refresh(Request()); _save(creds); return creds
        except (RefreshError, HttpError):
            try: os.remove(token_path)
            except OSError: pass
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(client_secrets_path):
            raise FileNotFoundError(
                f"Arquivo de client secrets não encontrado: {client_secrets_path}. "
                "Baixe do Google Cloud (OAuth client type: Desktop App)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, scopes)
        try:
            creds = flow.run_local_server(
                port=0, open_browser=True,
                authorization_prompt_message="",
                success_message="Autorização concluída. Pode fechar esta aba.",
                access_type="offline", prompt="consent",
            )
        except Exception:
            creds = flow.run_console(
                authorization_prompt_message="Visite a URL, autorize e cole o código aqui:",
                access_type="offline", prompt="consent",
            )
        _save(creds)
    return creds

@st.cache_resource
def get_sheets_service(client_secrets_path: str = "client_secret.json", token_path: str = "token.json"):
    """
    Retorna a instância 'service' global cacheadamente, economizando recursos de Build
    e repetições de leitura OAuth2 em disco por cada clique.
    """
    creds = _get_credentials(client_secrets_path=client_secrets_path, token_path=token_path)
    return build("sheets", "v4", credentials=creds)

# hash_funcs ignorando o SDK complexo build('sheets') do cache.
@st.cache_data(hash_funcs={"googleapiclient.discovery.Resource": lambda _: None}, ttl=900)
def _read_sheet_values(service, spreadsheet_id: str, sheet_name: str, header_row: int = 10, **_ignore):
    sheet = service.spreadsheets()
    range_a1 = f"'{sheet_name}'!A{header_row}:ZZ"
    resp = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_a1).execute()
    return resp.get("values", [])

@st.cache_data(hash_funcs={"googleapiclient.discovery.Resource": lambda _: None}, ttl=900)
def get_sheet_names(service, spreadsheet_id: str, **_ignore) -> List[str]:
    """Retorna os nomes de todas as abas de uma planilha."""
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    return [s.get("properties", {}).get("title", "") for s in sheets]
