"""Shared fixtures for integration tests.

Provides a small set of deterministic, semantically distinct DataFrames
covering the main test scenarios: mixed, empty, covid-only, pediatric,
high-mortality. Each fixture injects into the shared in-memory cache
that `get_df()` consults on entry, so the routers see the controlled
data without touching the real database.
"""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from srag.api.main import _cache
from srag.utils.epi_weeks import compute_epi_week_columns


def _inject(df: pd.DataFrame) -> None:
    if "_epi_week" not in df.columns and "DT_SIN_PRI" in df.columns:
        epi = compute_epi_week_columns(df["DT_SIN_PRI"])
        df = pd.concat([df, epi], axis=1)
    _cache["df"] = df
    _cache["loaded_at"] = datetime.now(UTC)


def _clear() -> None:
    _cache["df"] = None
    _cache["loaded_at"] = None


def make_srag_row(i: int, **overrides: object) -> dict[str, object]:
    """Build a SIVEP-shaped row. Any field can be overridden by kwargs."""
    evolucao = 1
    if i == 0:
        evolucao = 2
    elif i == 1:
        evolucao = 3
    row: dict[str, object] = {
        "DT_NOTIFIC": date(2024, 5, 1 + i),
        "DT_SIN_PRI": date(2024, 4, 25),
        "ID_MUNICIP": "2408003",
        "ID_MN_RESI": "2408003",
        "CLASSI_FIN": 5,
        "ID_UNIDADE": "HOSPITAL A",
        "BAIRRO_REF": "CENTRO",
        "ZONA": "URBANA",
        "NU_IDADE_N": 30,
        "TP_IDADE": 3,
        "IDADE_ANOS": 30.0,
        "CS_SEXO": "M",
        "CS_RACA": 1,
        "EVOLUCAO": evolucao,
        "UTI": 2,
        "HOSPITAL": 1,
        "SUPORT_VEN": 3,
        "NOSOCOMIAL": 2,
        "VACINA_COV": 1,
        "DOSE_1_COV": date(2024, 1, 1),
        "DT_INTERNA": date(2024, 5, 1) if i % 2 == 0 else None,
        "DT_EVOLUCA": date(2024, 5, 10) if i % 2 == 0 else None,
        "DT_ENTUTI": date(2024, 5, 2) if i % 4 == 0 else None,
        "DT_SAIDUTI": date(2024, 5, 8) if i % 4 == 0 else None,
        "DOSE_2_COV": None,
        "DOSE_REF": None,
        "DOSE_2REF": None,
        "DOS_RE_BI": None,
        "VACINA": 2,
        "DT_UT_DOSE": None,
        "PCR_VSR": 0,
        "AN_VSR": 0,
        "PCR_RESUL": 1,
        "RES_AN": 1,
        "PCR_FLUASU": 1,
        "PCR_FLUBLI": 1,
        "ANTIVIRAL": 1 if i % 2 == 0 else 2,
        "DT_ANTIVIR": date(2024, 4, 27) if i % 2 == 0 else None,
        "TRAT_COV": 2,
        "TIPO_TRAT": None,
        "CRITERIO": 1,
        "CO_LAB_AN": "LAB A",
        "DT_COLETA": date(2024, 4, 28),
        "DT_PCR": date(2024, 4, 30) if i % 3 == 0 else None,
        "DT_RES_AN": None,
        "TP_AMOSTRA": 1,
        "AMOSTRA": 1,
        "CO_DETEC": 0,
    }
    row.update(overrides)
    return row


@pytest.fixture
def mock_srag_df() -> pd.DataFrame:
    """15-row mixed dataset (cures, deaths, ignored). Default scenario."""
    data = [make_srag_row(i) for i in range(15)]
    df = pd.DataFrame(data)
    _inject(df)
    yield df
    _clear()


@pytest.fixture
def empty_srag_df() -> pd.DataFrame:
    """Empty DataFrame. Triggers the empty-path branches in every endpoint."""
    df = pd.DataFrame()
    _inject(df)
    yield df
    _clear()


@pytest.fixture
def covid_only_df() -> pd.DataFrame:
    """20 rows of pure COVID cases (CLASSI_FIN=5). Useful for agents filter."""
    data = [make_srag_row(i, CLASSI_FIN=5) for i in range(20)]
    df = pd.DataFrame(data)
    _inject(df)
    yield df
    _clear()


@pytest.fixture
def pediatric_df() -> pd.DataFrame:
    """15 rows of children (< 18 years). Useful for pediatric profiles."""
    data = [make_srag_row(i, NU_IDADE_N=5, TP_IDADE=3, IDADE_ANOS=5.0) for i in range(15)]
    df = pd.DataFrame(data)
    _inject(df)
    yield df
    _clear()


@pytest.fixture
def high_mortality_df() -> pd.DataFrame:
    """15 rows where 50% are deaths (EVOLUCAO=2). Useful for lethality tests."""
    data = [make_srag_row(i, EVOLUCAO=2 if i % 2 == 0 else 1) for i in range(15)]
    df = pd.DataFrame(data)
    _inject(df)
    yield df
    _clear()
