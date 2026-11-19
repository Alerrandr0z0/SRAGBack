"""Unit tests: corredor endêmico, perfil de quem morre e antiviral por faixa etária."""

from __future__ import annotations

import pandas as pd

from srag.data.analytics.advanced import compute_antiviral_delay_by_age
from srag.data.analytics.clinical_profile import compute_fatal_profile
from srag.data.analytics.endemic import compute_endemic_channel


def _cases_in_week(year: int, week_monday: str, n: int) -> list[dict[str, str]]:
    return [{"DT_SIN_PRI": week_monday} for _ in range(n)]


def _history(years: list[int], per_week: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in years:
        # 2ª segunda-feira de janeiro: SE 2 em qualquer dos anos usados.
        rows += _cases_in_week(year, f"{year}-01-12", per_week)
    return rows


class TestEndemicChannel:
    def test_empty(self) -> None:
        result = compute_endemic_channel(pd.DataFrame())
        assert result["enough_history"] is False
        assert result["weeks"] == []

    def test_needs_three_previous_years(self) -> None:
        df = pd.DataFrame(_history([2023, 2024, 2025], 2))
        result = compute_endemic_channel(df)
        assert result["enough_history"] is False
        assert result["history_years"] == [2023, 2024]
        assert result["reference_year"] == 2025

    def test_band_and_status(self) -> None:
        rows = _history([2022, 2023, 2024], 4) + _cases_in_week(2025, "2025-01-08", 30)
        result = compute_endemic_channel(pd.DataFrame(rows))
        assert result["enough_history"] is True
        assert result["history_years"] == [2022, 2023, 2024]
        week = result["weeks"][1]  # SE 2
        assert week["week"] == 2
        assert week["median"] == 4.0
        assert week["cases"] == 30
        assert week["status"] == "epidemic"
        assert result["current_week"] == 2
        assert result["current_status"] == "epidemic"
        assert result["weeks"][2]["cases"] is None  # semanas futuras sem casos
        assert result["weeks_above"] == 1

    def test_reference_year_can_be_chosen(self) -> None:
        rows = _history([2021, 2022, 2023, 2024], 3) + _cases_in_week(2025, "2025-01-08", 3)
        result = compute_endemic_channel(pd.DataFrame(rows), reference_year=2024)
        assert result["reference_year"] == 2024
        assert result["history_years"] == [2021, 2022, 2023]


class TestFatalProfile:
    def test_empty(self) -> None:
        assert compute_fatal_profile(pd.DataFrame()) == {"deaths": None, "survivors": None}

    def test_profiles(self) -> None:
        df = pd.DataFrame(
            [
                {"EVOLUCAO": 2, "IDADE_ANOS": 80.0, "VACINA": 2, "VACINA_COV": 2, "DIABETES": 1},
                {"EVOLUCAO": 2, "IDADE_ANOS": 70.0, "VACINA": 1, "VACINA_COV": 2, "DIABETES": 2},
                {"EVOLUCAO": 2, "IDADE_ANOS": 60.0, "VACINA": 9, "VACINA_COV": 9, "DIABETES": 9},
                {"EVOLUCAO": 1, "IDADE_ANOS": 10.0, "VACINA": 2, "VACINA_COV": 2, "DIABETES": 2},
            ]
        )
        result = compute_fatal_profile(df)
        deaths, survivors = result["deaths"], result["survivors"]
        assert deaths["count"] == 3
        assert deaths["median_age"] == 70.0
        assert deaths["unvaccinated_known"] == 2  # o ignorado fica fora
        assert deaths["unvaccinated_pct"] == 50.0
        assert deaths["risk_factor_known"] == 2
        assert deaths["risk_factor_pct"] == 50.0
        assert deaths["reliable"] is False
        assert survivors["median_age"] == 10.0
        assert survivors["risk_factor_pct"] == 0.0


class TestAntiviralDelayByAge:
    def test_empty(self) -> None:
        result = compute_antiviral_delay_by_age(pd.DataFrame())
        assert result["bands"] == []
        assert result["overall"] is None

    def test_delay_per_band(self) -> None:
        rows = [
            {"IDADE_ANOS": 3.0, "ANTIVIRAL": 1, "DT_SIN_PRI": "2025-03-01", "DT_ANTIVIR": d}
            for d in ("2025-03-02", "2025-03-04", "2025-03-09")  # 1, 3 e 8 dias
        ]
        rows.append({"IDADE_ANOS": 3.0, "ANTIVIRAL": 2, "DT_SIN_PRI": "2025-03-01"})
        rows.append({"IDADE_ANOS": 85.0, "ANTIVIRAL": 2, "DT_SIN_PRI": "2025-03-01"})
        result = compute_antiviral_delay_by_age(pd.DataFrame(rows))
        young = next(band for band in result["bands"] if band["key"] == "0-4")
        assert young["treated"] == 3
        assert young["median_days"] == 3.0
        assert young["timely_pct"] == 33.3
        assert young["untreated_pct"] == 25.0
        assert young["reliable"] is False
        oldest = next(band for band in result["bands"] if band["key"] == "80+")
        assert oldest["treated"] == 0
        assert oldest["median_days"] is None
        assert oldest["untreated_pct"] == 100.0
        assert result["overall"]["treated"] == 3
