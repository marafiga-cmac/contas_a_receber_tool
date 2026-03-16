"""Compat: módulo legado `frontend.py`.

O código original do projeto importava `frontend` a partir da raiz.
Após o refactor, a implementação real ficou em:
`convenio018/services/frontend_legacy.py`.

Mantenha este arquivo fino para evitar quebrar imports antigos.
"""

from __future__ import annotations

from convenio018.services.frontend_legacy import *  # noqa: F401,F403
