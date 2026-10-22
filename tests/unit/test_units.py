"""Unit tests for the health-unit computations (units.py)."""

from __future__ import annotations

import pandas as pd

from srag.data.analytics.units import (
    compute_hospital_stay,
    compute_notifying_units,
    compute_unit_notification_delay,
    compute_vaccine_journey,
)
from srag.data.cnes import unit_name


class TestCnesNames:
    def test_known_code_resolves_to_name(self) -> None:
        assert unit_name("9631631") == "SUA CLINICA AUGE"

    def test_unknown_code_is_kept_readable(self) -> None:
        assert unit_name(" 123 ") == "CNES 123"


class TestNotifyingUnits:
    def test_empty_dataframe(self) -> None:
        assert compute_notifying_units(pd.DataFrame()) == {
            "total": 0,
            "unidentified": 0,
            "items": [],
        }

    def test_counts_outcomes_per_unit_and_unidentified(self) -> None:
        df = pd.DataFrame(
            {
                "ID_UNIDADE": ["9631631", "9631631", "9631631.0", "111", None, ""],
                "EVOLUCAO": [1, 2, 3, 9, 1, 1],
            }
        )
        result = compute_notifying_units(df)
        assert result["total"] == 6
        assert result["unidentified"] == 2
        first = result["items"][0]
        assert first["name"] == "SUA CLINICA AUGE"
        assert (first["total"], first["cure"], first["death"], first["other"]) == (3, 1, 1, 1)
        assert result["items"][1]["name"] == "CNES 111"
        assert result["items"][1]["other"] == 1

    def test_missing_column(self) -> None:
        result = compute_notifying_units(pd.DataFrame({"EVOLUCAO": [1, 2]}))
        assert result["items"] == []
        assert result["unidentified"] == 2


class TestUnitNotificationDelay:
    def _frame(self) -> pd.DataFrame:
        rows = []
        for delay in (1, 2, 3, 4, 5):
            rows.append(("9631631", "2025-01-01", f"2025-01-{1 + delay:02d}"))
        for delay in (12, 12, 13, 14, 15):
            rows.append(("111", "2025-01-01", f"2025-01-{1 + delay:02d}"))
        rows += [("222", "2025-01-01", "2025-01-03")] * 2  # too few cases
        rows += [("9631631", "2025-01-10", "2025-01-02")]  # notified before symptoms
        return pd.DataFrame(rows, columns=["ID_UNIDADE", "DT_SIN_PRI", "DT_NOTIFIC"])

    def test_ranks_longest_median_first_and_hides_small_units(self) -> None:
        result = compute_unit_notification_delay(self._frame())
        assert [row["id_unidade"] for row in result["units"]] == ["111", "9631631"]
        assert result["hidden_count"] == 1
        slow = result["units"][0]
        assert slow["median_days"] == 13.0
        assert slow["status"] == "critico"
        assert slow["within_limit_pct"] == 0.0
        fast = result["units"][1]
        assert fast["unit"] == "SUA CLINICA AUGE"
        assert fast["total"] == 5  # the inverted-date case is ignored
        assert fast["status"] == "adequado"
        assert fast["within_limit_pct"] == 100.0

    def test_empty(self) -> None:
        result = compute_unit_notification_delay(pd.DataFrame())
        assert result["units"] == []
        assert result["limit_days"] == 7


class TestHospitalStay:
    def test_empty(self) -> None:
        result = compute_hospital_stay(pd.DataFrame())
        assert result["closed"] == 0
        assert result["curve"] == []
        assert result["median_days"] is None

    def test_medians_by_outcome_and_curve(self) -> None:
        df = pd.DataFrame(
            {
                "EVOLUCAO": [1, 1, 1, 2, 9, 1],
                "DT_INTERNA": ["2025-01-01"] * 6,
                "DT_EVOLUCA": [
                    "2025-01-03",
                    "2025-01-05",
                    "2025-01-09",
                    "2025-01-11",
                    "2025-01-05",
                    "2024-12-01",  # negative stay is invalid
                ],
                "DT_SIN_PRI": ["2025-01-01"] * 6,
            }
        )
        result = compute_hospital_stay(df)
        assert result["closed"] == 4
        assert result["median_cure_days"] == 4.0
        assert result["median_death_days"] == 10.0
        assert result["bed_days"] == 2 + 4 + 8 + 10
        by_day = {point["day"]: point for point in result["curve"]}
        assert by_day[0] == {"day": 0, "cure_pct": 0.0, "death_pct": 0.0}
        assert by_day[4]["cure_pct"] == 50.0
        assert by_day[10]["death_pct"] == 25.0
        assert by_day[45]["cure_pct"] == 75.0
        assert len(result["curve"]) == 46

    def test_ignores_stays_longer_than_the_limit(self) -> None:
        df = pd.DataFrame(
            {"EVOLUCAO": [1], "DT_INTERNA": ["2025-01-01"], "DT_EVOLUCA": ["2025-12-01"]}
        )
        assert compute_hospital_stay(df)["closed"] == 0


class TestVaccineJourney:
    def test_empty(self) -> None:
        assert compute_vaccine_journey(pd.DataFrame())["stages"] == []

    def test_metrics_per_stage_in_order(self) -> None:
        df = pd.DataFrame(
            {
                "VACINA_COV": [2, 2, 2, 1, 1],
                "DOSE_1_COV": [None, None, None, "2022-01-01", "2022-01-01"],
                "DOSE_2_COV": [None, None, None, "2022-02-01", None],
                "DT_SIN_PRI": ["2025-01-01"] * 5,
                "DT_INTERNA": ["2025-01-03", "2025-01-05", "2025-01-03", "2025-01-02", None],
                "DT_EVOLUCA": ["2025-01-13", "2025-01-09", "2025-01-08", "2025-01-12", None],
                "EVOLUCAO": [1, 2, 1, 1, None],
                "UTI": [1, 1, 2, 2, 9],
            }
        )
        result = compute_vaccine_journey(df)
        names = [stage["stage"] for stage in result["stages"]]
        assert names == ["Não vacinado", "Só a 1ª dose", "Esquema completo"]
        unvaccinated = result["stages"][0]
        assert unvaccinated["total"] == 3
        assert unvaccinated["median_days_to_hospital"] == 2.0
        assert unvaccinated["median_stay_days"] == 5.0
        assert unvaccinated["icu_pct"] == 66.7
        assert unvaccinated["cure_pct"] == 66.7
        assert unvaccinated["death_pct"] == 33.3
        only_first = result["stages"][1]
        assert only_first["cure_pct"] is None  # no resolved case
        assert only_first["icu_pct"] is None  # ICU unknown
