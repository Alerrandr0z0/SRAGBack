"""Shared SIVEP reference codes and project overrides."""

MOSSORO_IBGE_CODES = ("2408003", "240800", "240800.0")
MOSSORO_IBGE_CODE = MOSSORO_IBGE_CODES[0]
MOSSORO_NAMES = ("MOSSORO", "MOSSORÓ")

# Project decision: only code 2 is counted as death.
DEATH_OUTCOMES = {2}
VALID_OUTCOMES = {1, 2, 3}
