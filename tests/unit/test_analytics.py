from datetime import date

import pandas as pd

from srag.data.analytics import (
    apply_global_filters,
    categorize_age,
    classificar_status_gripe,
    compute_time_series,
    compute_virus_distribution,
    infer_etiologic_agent,
    outcome_death_mask,
)


def test_categorize_age() -> None:
    assert categorize_age(0.5) == "0-1 ano"
    assert categorize_age(1.9) == "0-1 ano"
    assert categorize_age(2) == "2-4 anos"
    assert categorize_age(5) == "5-9 anos"
    assert categorize_age(15) == "15-19 anos"
    assert categorize_age(30) == "30-39 anos"
    assert categorize_age(50) == "50-59 anos"
    assert categorize_age(70) == "70-79 anos"
    assert categorize_age(85) == "80+ anos"


def test_compute_virus_distribution_empty() -> None:
    df = pd.DataFrame()
    assert compute_virus_distribution(df).empty


def test_compute_virus_distribution() -> None:
    df = pd.DataFrame(
        {
            "CLASSI_FIN": [1, 5, 5, 2, 4, None],
            "PCR_VSR": [0, 0, 0, 0, 0, 1],  # One VSR
        }
    )
    result = compute_virus_distribution(df)
    # VSR has priority 0, so it should be first
    assert result.iloc[0]["virus"] == "VSR"
    assert result[result["virus"] == "COVID-19"]["count"].iloc[0] == 2
    assert result[result["virus"] == "Influenza"]["count"].iloc[0] == 1


def test_apply_bairros_filter() -> None:
    df = pd.DataFrame({"BAIRRO_REF": ["CENTRO", "ALTO"]})
    filtered = apply_global_filters(df, bairros=["CENTRO"])
    assert len(filtered) == 1
    assert filtered.iloc[0]["BAIRRO_REF"] == "CENTRO"


def test_outcome_death_mask() -> None:
    values = pd.Series([1, 2, 3, None, 2, 1])
    mask = outcome_death_mask(values)
    assert mask.sum() == 2  # Only code 2 should be True
    assert not mask.iloc[0]  # code 1 = cure, not death
    assert not mask.iloc[2]  # code 3 should NOT count as death
    assert mask.iloc[1]  # code 2 = death


def test_infer_etiologic_agent() -> None:
    df = pd.DataFrame(
        {
            "CLASSI_FIN": [5, 5, 5, 1, 1, 2],
            "PCR_VSR": [1, 0, 0, 0, 0, 0],
            "AN_VSR": [0, 1, 0, 0, 0, 0],
        }
    )
    agents = infer_etiologic_agent(df)
    assert agents.iloc[0] == "VSR"
    assert agents.iloc[2] == "COVID-19"
    assert agents.iloc[3] == "Influenza"


def test_classificar_status_gripe() -> None:
    row_with_dose = {
        "VACINA": 1,
        "DT_UT_DOSE": date(2024, 5, 1),
        "DT_SIN_PRI": date(2024, 6, 1),
        "DT_1_DOSE": None,
        "DT_2_DOSE": None,
        "TP_IDADE": 3,
        "NU_IDADE_N": 30,
    }
    result = classificar_status_gripe(row_with_dose)
    assert result == "protegido"

    row_no_vaccine = {
        "VACINA": 2,
        "DT_UT_DOSE": None,
        "DT_1_DOSE": None,
        "DT_2_DOSE": None,
        "TP_IDADE": 3,
        "NU_IDADE_N": 30,
    }
    result = classificar_status_gripe(row_no_vaccine)
    assert result == "nao_vacinado"


def test_compute_time_series() -> None:
    df = pd.DataFrame({"DT_SIN_PRI": [date(2024, 1, 1), date(2024, 1, 5), date(2024, 1, 15)]})
    ts = compute_time_series(df)
    assert len(ts) >= 1
    assert "epi_week" in ts.columns
    assert "total" in ts.columns


