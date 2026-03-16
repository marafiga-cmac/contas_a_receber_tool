"""Pacote principal do app 'Identificação de Convênios'.

Estrutura sugerida:
- `convenio018/config.py`: constantes e caminhos
- `convenio018/ui/...`: componentes Streamlit (sidebar, abas)
- `convenio018/services/...`: regras de negócio / integração (Google Sheets, parsing)

Este refactor manteve compatibilidade reaproveitando o código existente em
`services/backend_legacy.py` e `services/frontend_legacy.py`, mas isolou a UI em
módulos menores para facilitar manutenção.
"""

__all__ = ["config"]
