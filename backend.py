"""Compat: módulo legado `backend.py`.

O código original do projeto importava `backend` a partir da raiz.
Após o refactor, a implementação real ficou em:
`convenio018/services/backend_legacy.py`.

Mantenha este arquivo fino para evitar quebrar imports antigos.
"""

from __future__ import annotations

from convenio018.services.backend_legacy import *  # noqa: F401,F403
