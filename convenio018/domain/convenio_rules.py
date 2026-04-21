"""Regras de convênio e preferências contábeis por unidade."""

from __future__ import annotations

CONVENIOS_CMAP = [
    "Afpergs", "Amil", "Assefaz", "Banco Central", "Bradesco", "Cabergs",
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

def get_csv_convenio_overrides(unidade: str) -> dict:
    """
    Retorna regras de banco (subconta_convenio, deposito_suffix, glosa_neg_target)
    para injetar no CSV final, de acordo com o convênio.
    """
    unidade = (unidade or "").strip().upper()
    if unidade == "CMAP":
        return {
            "Cabergs": {"deposito_subconta_banco": "00270617409902"},
            "Saúde Caixa": {"deposito_subconta_banco": "0374-50090", "deposito_suffix": "Saude Caixa Pgto Credenc", "glosa_neg_target": "1133003"},
            "Bradesco": {"subconta_convenio": "10", "deposito_suffix": "Sinistro Ap/Certif."},
            "CarePlus": {"subconta_convenio": "63", "deposito_suffix": "Care Plus Medicina"},
            "Prevent Senior": {"subconta_convenio": "91", "deposito_suffix": "Prevent Senior Privat"},
            "Sul America": {"subconta_convenio": "3", "deposito_suffix": "Sul America"},
            "Notredame": {"subconta_convenio": "47", "deposito_suffix": "Notre Dame Intermedi"},
            "Assefaz": {"glosa_neg_target": "1133003"},
            "Cassi": {"glosa_neg_target": "1133003"},
            "Amil": {"glosa_neg_target": "1133003"},
            "Banco Central": {"glosa_neg_target": "1133003"},
            "GEAP": {"glosa_neg_target": "1133003"},
            "Geap": {"glosa_neg_target": "1133003"},
            "Doctor": {"glosa_neg_target": "1133003"},
        }

    # CMAC
    convenios_dict = {}
    for nome, (sub, suffix) in CMAC_GLOSA_TO_3303.items():
        convenios_dict[nome] = {
            "subconta_convenio": sub,
            "deposito_suffix": suffix,
            "glosa_neg_target": "1133003",
        }
    for nome, (sub, suffix) in CMAC_GLOSA_TO_3301.items():
        convenios_dict[nome] = {
            "subconta_convenio": sub,
            "deposito_suffix": suffix,
            "glosa_neg_target": "1133001",
        }

    deposito_overrides = {
        "Petrobras": "3722-130049991",
        "Petrobrás": "3722-130049991",
        "Saúde Caixa": "0374-50082",
    }
    for k, conta in deposito_overrides.items():
        if k in convenios_dict:
            convenios_dict[k]["deposito_subconta_banco"] = conta

    return convenios_dict
