"""Shared SIVEP reference codes and project overrides."""

MOSSORO_IBGE_CODES = ("2408003", "240800", "240800.0")
MOSSORO_IBGE_CODE = MOSSORO_IBGE_CODES[0]
MOSSORO_NAMES = ("MOSSORO", "MOSSORÓ")

# Project decision: only code 2 is counted as death.
DEATH_OUTCOMES = {2}
VALID_OUTCOMES = {1, 2, 3}

# --- Filtro "Base de análise" -------------------------------------------------
# Notificados = universo completo (sem filtro extra).
# Confirmados = classificação final etiológica (CLASSI_FIN), NÃO é confirmação
# laboratorial isolada — 1 (Influenza) e 5 (COVID-19) são os códigos SIVEP para
# "classificação final" fechada por esses dois agentes.
CONFIRMED_CLASSI_FIN = {1, 5}
BASE_ANALISE_VALUES = {"notificados", "confirmados", "obitos"}

# --- Filtro "Gravidade" -------------------------------------------------------
# Cada opção é independente (não são mutuamente exclusivas nos dados: um caso
# pode ter passado por UTI e também por internação comum antes/depois).
# UTI: campo UTI == 1 (Sim).
# Internação: campo HOSPITAL == 1 (Sim) — "Houve internação?" no dicionário SIVEP.
# Ventilação: campo SUPORT_VEN em {1, 2} — qualquer suporte ventilatório,
# invasivo (1) ou não invasivo (2); código 3 é "Não" e 9 é "Ignorado".
GRAVIDADE_VALUES = {"uti", "internacao", "ventilacao"}
VENTILACAO_CODES = {1, 2}

# --- Filtro "Sintomatologia" ---------------------------------------------------
# Todos os campos de sintoma SIVEP seguem o mesmo código: 1-Sim, 2-Não, 9-Ignorado
# (inclusive SATURACAO, que no dicionário é "Saturação O2 < 95%": 1-Sim, 2-Não,
# 9-Ignorado — não é uma medida contínua, é um sim/não como os demais).
# Chave curta (usada em ?sintomas=) -> coluna SIVEP real.
SYMPTOM_FIELDS: dict[str, str] = {
    "febre": "FEBRE",
    "tosse": "TOSSE",
    "garganta": "GARGANTA",
    "dispneia": "DISPNEIA",
    "desc_resp": "DESC_RESP",
    "saturacao": "SATURACAO",
    "diarreia": "DIARREIA",
    "vomito": "VOMITO",
    "dor_abd": "DOR_ABD",
    "fadiga": "FADIGA",
    "perd_olft": "PERD_OLFT",
    "perd_pala": "PERD_PALA",
    "outro_sin": "OUTRO_SIN",
}
SYMPTOM_PRESENT_CODE = 1
