"""Performance benchmarks for analytics hot paths.

Uses pytest-benchmark (already a dev dependency): it calibrates rounds,
reports min/mean/max and supports ``--benchmark-save`` / ``--benchmark-compare``
for regression tracking. These tests double as smoke checks (shapes only);
correctness belongs to the unit suite.

Excluded from the default suite via the ``slow`` marker (``make test`` runs
``-m "not slow"``). Run explicitly with ``make bench``.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from srag.data.analytics import (
    apply_global_filters,
    categorize_age,
    classificar_status_gripe,
    compute_time_series,
    compute_virus_distribution,
    infer_etiologic_agent,
    outcome_death_mask,
)
from srag.data.loader import _normalize_age_to_years

pytestmark = pytest.mark.slow


def generate_test_data(n_rows: int = 1000) -> pd.DataFrame:
    """Generate test data for benchmarks."""
    return pd.DataFrame(
        {
            "DT_SIN_PRI": [date(2024, 1, 1) + timedelta(days=i) for i in range(n_rows)],
            "CLASSI_FIN": [(i % 5) + 1 for i in range(n_rows)],
            "PCR_VSR": [i % 2 for i in range(n_rows)],
            "UTI": [(i % 4) + 1 for i in range(n_rows)],
            "EVOLUCAO": [(i % 4) + 1 for i in range(n_rows)],
            "NU_IDADE_N": [i % 100 for i in range(n_rows)],
            "TP_IDADE": [3] * n_rows,
            "CS_RACA": [(i % 6) + 1 for i in range(n_rows)],
            "CS_SEXO": ["M" if i % 2 == 0 else "F" for i in range(n_rows)],
            "BAIRRO_REF": ["CENTRO" if i % 2 == 0 else "ALTO" for i in range(n_rows)],
        }
    )


@pytest.fixture(params=[100, 10_000], ids=["small", "large"])
def frame(request: pytest.FixtureRequest) -> pd.DataFrame:
    """Benchmark frames. Built in the fixture so generation time is not measured."""
    return generate_test_data(request.param)


def test_categorize_age_single(benchmark) -> None:
    """Benchmark: categorize single age."""
    assert benchmark(categorize_age, 30.5) == "30-39 anos"


def test_categorize_age_batch(benchmark) -> None:
    """Benchmark: categorize 1000 ages."""
    ages = [i % 100 for i in range(1000)]
    assert len(benchmark(lambda: [categorize_age(a) for a in ages])) == 1000


def test_normalize_age_years(benchmark) -> None:
    """Benchmark: normalize age in years (most common)."""
    assert benchmark(_normalize_age_to_years, 30, 3) == 30.0


def test_normalize_age_batch(benchmark) -> None:
    """Benchmark: normalize 1000 ages."""
    data = [(i % 100, 3) for i in range(1000)]
    result = benchmark(lambda: [_normalize_age_to_years(age, tp) for age, tp in data])
    assert len(result) == 1000


def test_outcome_death_mask(benchmark, frame: pd.DataFrame) -> None:
    """Benchmark: death mask."""
    assert len(benchmark(outcome_death_mask, frame["EVOLUCAO"])) == len(frame)


def test_infer_etiologic_agent(benchmark, frame: pd.DataFrame) -> None:
    """Benchmark: infer agent."""
    assert len(benchmark(infer_etiologic_agent, frame)) == len(frame)


def test_compute_virus_distribution(benchmark, frame: pd.DataFrame) -> None:
    """Benchmark: compute virus distribution."""
    assert not benchmark(compute_virus_distribution, frame).empty


def test_compute_time_series(benchmark, frame: pd.DataFrame) -> None:
    """Benchmark: compute time series."""
    assert len(benchmark(compute_time_series, frame)) >= 0


def test_apply_global_filters_by_bairro(benchmark) -> None:
    """Benchmark: apply global filters by bairro."""
    df = generate_test_data(5000)
    result = benchmark(apply_global_filters, df, bairros=["CENTRO"])
    assert len(result) <= len(df)


def test_classificar_status_gripe(benchmark) -> None:
    """Benchmark: classify vaccination status for flu."""
    row = {
        "VACINA": 1,
        "DT_UT_DOSE": date(2024, 6, 1),
        "DT_1_DOSE": None,
        "DT_2_DOSE": None,
        "TP_IDADE": 3,
        "NU_IDADE_N": 30,
        "DT_SIN_PRI": date(2024, 7, 1),
    }
    assert benchmark(classificar_status_gripe, row) in [
        "protegido",
        "dose_1",
        "dose_2",
        "dose_unica",
        "vencida",
        "nao_vacinado",
        "ignorado",
        "inconsistencia",
    ]
