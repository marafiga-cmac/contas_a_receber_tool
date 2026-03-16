# Identificação de Convênios (Project 018)

Este repositório é um **refactor organizacional** do seu projeto original.
A regra de negócio (Sheets/CSV/JSON) foi preservada e a UI Streamlit foi
separada por abas para facilitar manutenção.

## Como rodar

1) Crie/ative um venv

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

2) Instale dependências

```bash
pip install -r requirements.txt
```

3) (Opcional) Coloque o `client_secret.json` na raiz do projeto

4) Rode o Streamlit

```bash
streamlit run app.py
```

## Estrutura

- `app.py` – entry-point do Streamlit (bem pequeno)
- `convenio018/` – pacote principal
  - `config.py` – IDs das planilhas, caminhos e defaults
  - `ui/sidebar.py` – sidebar (unidade, output_dir, credenciais)
  - `ui/tabs/` – cada aba em um arquivo
  - `services/` – regras de negócio (neste refactor: código legado reaproveitado)
- `assets/` – ícone do app, etc.

## Segurança (importante)

- **Não** versionar `client_secret.json` e `token.json`.
- Se você for usar Git, coloque estes arquivos no `.gitignore`.

## Migração gradual do legado

Hoje, a UI chama `convenio018.services.api`, que por enquanto reexporta as
funções de `backend_legacy.py` e `frontend_legacy.py`.

Quando você quiser melhorar o projeto, o caminho mais seguro é:
1. Copiar 1 função do `*_legacy.py` para um módulo novo (ex: `services/nfse.py`)
2. Atualizar `services/api.py` para apontar para a nova implementação
3. Rodar seus testes manuais no Streamlit



## Estrutura refatorada

- `convenio018/integrations/`: acesso externo (Google Sheets)
- `convenio018/domain/`: regras e constantes de convênio/CSV
- `convenio018/utils/`: helpers puros de parsing, normalização e formatação
- `convenio018/services/`: fluxos de negócio e exportações
- `convenio018/ui/forms/`: formulário principal
- `convenio018/ui/reports/`: relatórios e templates de impressão

Os arquivos `backend.py`, `frontend.py`, `convenio018/services/backend_legacy.py` e `convenio018/services/frontend_legacy.py` foram mantidos apenas por compatibilidade.
