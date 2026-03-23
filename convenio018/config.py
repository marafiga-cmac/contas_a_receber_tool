"""Configurações do projeto.

Centraliza constantes (IDs de planilhas, caminhos de assets, etc.) para evitar
hardcode espalhado pelo app.

- Para mudar os IDs das planilhas (CMAP/CMAC/ano), edite `SHEET_IDS`.
- Para trocar o ícone do app, substitua o arquivo em `assets/`.

Observação de segurança:
- **Não** comite `client_secret.json` e `token.json` no Git.
"""

from __future__ import annotations

from pathlib import Path

# Raiz do repositório (um nível acima do pacote `convenio018/`).
PROJECT_ROOT = Path(__file__).resolve().parents[1]

ASSETS_DIR = PROJECT_ROOT / "assets"
APP_ICON_PATH = ASSETS_DIR / "icone_bot.ico"

# IDs das planilhas Google Sheets (ajuste quando necessário)
SHEET_IDS = {
    "CMAP": {
        "2025": "1GSDhVvYCyiQ4DYu9a00eTuzSCWvP3FY7nF4nRT2ual4",
        "2026": "1onVIOCo9o-7Yt-3f9rS8n0dRzk9xOgDsHjDHPpN9UQ8",
    },
    "CMAC": {
        "2025": "1d6JCsv9LDYORig-951yzHo1qiwqnvpQD2TI3v8as7_8",
        "2026": "1Vi6UDESATcR9fy-sIC2ExRzyhVu8F8Qv02lFxdnIfc4",
    },
}

# Valores padrão de UI
DEFAULT_UNIDADE = "CMAP"
DEFAULT_CLIENT_SECRET = "client_secret.json"
DEFAULT_TOKEN_FILE = "token.json"

