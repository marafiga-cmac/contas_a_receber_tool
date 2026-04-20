"""Constantes compartilhadas para parsing e geração de CSV."""

from __future__ import annotations

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ------------------------- Normalização de colunas --------------------------

REQUIRED_FIELDS = {
    "n remessa": "Nº Remessa", "no remessa": "Nº Remessa", "nº remessa": "Nº Remessa", "numero remessa": "Nº Remessa",
    "ref": "Ref.", "ref.": "Ref.", "referencia": "Ref.",
    "n nf": "Nº NF", "no nf": "Nº NF", "nº nf": "Nº NF", "numero nf": "Nº NF", "nfse": "Nº NF",
    "nfs-e": "Nº NF", "nfs e": "Nº NF",
    "nf recurso": "NF recurso",
    "nf de recurso": "NF recurso",
    "nf_rec": "NF recurso",
    "nf rec": "NF recurso",
    "nf recurso glosa": "NF recurso",
    "valor envio xml - remessa": "Valor envio XML - Remessa", "valor envio xml remessa": "Valor envio XML - Remessa",
    "valor pgto": "Valor pgto", "valor pagamento": "Valor pgto",
    "valor glosado": "Valor glosado",
    "imposto": "Imposto", "imp.": "Imposto", "impostos": "Imposto",
    "glosa mantida": "Glosa mantida", "glosa mant.": "Glosa mantida",
    "valor pago": "Valor pago",
    "valor nf rg": "Valor NF RG",
    "valor nf": "Valor NF",
    "valor da nf": "Valor NF",
    "vlr nf": "Valor NF",
    "valor nota": "Valor NF",
    "valor nota fiscal": "Valor NF",
}
COMBINED_IMPOSTO_GLOSA_KEYS = ["imposto glosa mantida", "imposto/glosa mantida", "imposto e glosa mantida"]

REMESSAS_COLUMNS = [
    "Nº Remessa","Ref.","Nº NF",
    "Valor envio XML - Remessa","Valor pgto","Valor glosado","Imposto","Glosa mantida"
]
RECURSOS_COLUMNS = [
    "Nº Remessa","Ref.","Nº NF",
    "Valor glosado","Valor pago","Imposto","Glosa mantida"
]

# Colunas por nome (usadas na leitura de datas/valor recursado)
REMESSA_DATE_KEYS = [
    "data pgto remessa", "data remessa", "data pagamento remessa",
    "dt pgto remessa", "dt remessa"
]
RECURSO_DATE_KEYS = [
    "data emissão nf.", "data emissao nf",
    "data pgto recurso", "data pagamento recurso",
    "data recurso", "data pgto rec", "dt pgto recurso"
]
VALOR_RECURSADO_KEYS = [
    "valor nf rg", "valor recursado",  # priorizado
    "valor recurso", "valor recurso (rec)", "valor glosado"
]

CSV_COLS = 13
CSV_DELIM = ";"

