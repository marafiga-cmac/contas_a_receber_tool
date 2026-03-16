"""Regras de convênio e preferências contábeis por unidade."""

from __future__ import annotations

CONVENIOS_CMAP = [
    "Afpergs", "Amil", "Assefaz", "Banco Central", "Bradesco", "Cabergs", "Cabergs ID",
    "CarePlus", "Cassi", "Doctor", "Embratel", "Humana", "GEAP", "Gente Saúde",
    "Life", "Mediservice", "Notredame", "Postal Saúde", "Prevent Senior",
    "Proasa", "Saúde Caixa", "Sul America", "Capesesp", "Ipê Saúde", 
]

# ---- CMAC ----
# Regra 1133004 -> 1133003
CMAC_GLOSA_TO_3303 = {
    "Amil": ("20", "Amil Assistencia Med"),
    "Assefaz": ("27", "Fundacao Assistencia"),
    "Banco Central": ("43", "Pagamento Sigef Ap"),
    "Cassi": ("26", "Caixa de Assistencia"),
    "GEAP": ("105", "Geap Autogestao Em S"),
    "ICS": ("107", "Instituto Curitiba D"),
    "Itaú": ("9", "Porto Saude"),
    "Judicemed": ("17", "Associacao De Assist"),
    "Paraná Clínicas": ("101", "Paraná Clínicas"),
    "Petrobrás": ("23", "Associacao Petrobras"),
    "Proasa": ("25", "Proasa Programa Adven"),
    "Sanepar": ("12", "Fundação Sanepar A"),
    "Saúde Caixa": ("15", "Saude Caixa"),
    "Voam": ("30", "Volvo Do Brasil Veicu"),
    "Select": ("109", "Select"),    
}

# Regra 1133004 -> 1133001
CMAC_GLOSA_TO_3301 = {
    "Bradesco": ("10", "Sinistro Ap/Certif"),
    "Conab": ("22", "Conab Sede Sureg Par"),
    "Copel": ("11", "Fundacao Copel"),
    "Global Araucária": ("48", "Santos E Assolari Tel"),
    "Global Paranaguá": ("24", "Global Tele Atendimen"),
    "Mediservice": ("100", "Mediservice Operadora Planos"),
    "MedSul": ("7", "Alca Servicos De Cobr"),
    "Notredame": ("18", "Notre Dame Intermedi"),
    "Postal Saúde": ("29", "Postal Saude - Caixa"),
    "Prevent Senior": ("102", "Prevent Senior Privat"),
    "Sul America": ("3", "Sul America Companhia"),
    "Life": ("45", "Life Empresarial Saude Ltda"),
}

# Lista consolidada de convênios CMAC (alfabética e sem duplicatas)
CONVENIOS_CMAC = sorted(
    set(list(CMAC_GLOSA_TO_3303.keys()) + list(CMAC_GLOSA_TO_3301.keys())),
    key=lambda s: s.lower()
)

DEPOSITO_SUBCONTA_BANCO = {
    "CMAP": "3708/0001649-7",
    "CMAC": "03645/00044210",
}

CSV_HEADER_FIRST_ROW = {
    "CMAP": ("1841", "Clínica Adventista de Porto Alegre - IASBS"),
    "CMAC": ("1941", "Clínica Adventista de Curitiba - IASBS"),
}



def get_convenios_por_unidade(unidade: str):
    """
    Retorna (lista_de_convenios, label) de acordo com a unidade selecionada.
    - CMAP: usa CONVENIOS_CMAP (já existente no projeto)
    - CMAC: união de chaves dos dicionários CMAC
    """
    unidade = (unidade or "").strip().upper()
    if unidade == "CMAC":
        return CONVENIOS_CMAC, "Convênio (CMAC)"
    # padrão: CMAP
    try:
        return sorted(CONVENIOS_CMAP, key=lambda s: s.lower()), "Convênio (CMAP)"
    except Exception:
        return [], "Convênio (CMAP)"
