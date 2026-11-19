"""Unit tests for the clinical-profile indicators (clinical_profile.py)."""

from __future__ import annotations

import pandas as pd
import pytest

from srag.data.analytics.clinical_profile import (
    MIN_RELIABLE_RESOLVED,
    compute_risk_factor_load,
    compute_severity_cascade,
    compute_warning_signs,
)


def _cases(rows: list[dict[str, int]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _step(result: dict, key: str) -> dict:
    return next(step for step in result["steps"] if step["key"] == key)


class TestSeverityCascade:
    def _dataset(self) -> pd.DataFrame:
        return _cases(
            [
                {"HOSPITAL": 1, "UTI": 1, "SUPORT_VEN": 1, "EVOLUCAO": 2},  # UTI, ventilado, óbito
                {"HOSPITAL": 1, "UTI": 2, "SUPORT_VEN": 3, "EVOLUCAO": 1},  # enfermaria, cura
                {"HOSPITAL": 2, "UTI": 2, "SUPORT_VEN": 3, "EVOLUCAO": 1},  # ambulatorial
                {"HOSPITAL": 2, "UTI": 1, "SUPORT_VEN": 2, "EVOLUCAO": 2},  # UTI sem HOSPITAL=1
            ]
        )

    def test_empty_dataframe(self) -> None:
        assert compute_severity_cascade(pd.DataFrame()) == {"total": 0, "steps": []}

    def test_steps_and_percentages(self) -> None:
        result = compute_severity_cascade(self._dataset())
        assert result["total"] == 4
        assert [step["cases"] for step in result["steps"]] == [4, 3, 2, 1]
        assert [step["pct"] for step in result["steps"]] == [100.0, 75.0, 50.0, 25.0]

    def test_icu_patient_counts_as_hospitalised_even_without_the_hospital_flag(self) -> None:
        # A linha 3 só tem UTI=1; ainda assim é internada.
        assert _step(compute_severity_cascade(self._dataset()), "hospitalized")["cases"] == 3

    def test_lethality_per_step(self) -> None:
        result = compute_severity_cascade(self._dataset())
        assert _step(result, "notified")["lethality"] == 50.0
        assert _step(result, "icu")["lethality"] == 100.0
        assert _step(result, "invasive_ventilation")["deaths"] == 1

    def test_only_outcome_two_is_death(self) -> None:
        df = _cases([{"HOSPITAL": 1, "UTI": 2, "SUPORT_VEN": 3, "EVOLUCAO": 3}] * 2)
        step = _step(compute_severity_cascade(df), "notified")
        assert step["deaths"] == 0
        assert step["lethality"] == 0.0

    def test_open_cases_do_not_enter_the_lethality_denominator(self) -> None:
        df = _cases(
            [
                {"HOSPITAL": 1, "UTI": 2, "SUPORT_VEN": 3, "EVOLUCAO": 2},
                {"HOSPITAL": 1, "UTI": 2, "SUPORT_VEN": 3, "EVOLUCAO": 9},
            ]
        )
        step = _step(compute_severity_cascade(df), "notified")
        assert (step["cases"], step["resolved"], step["lethality"]) == (2, 1, 100.0)

    def test_lethality_is_none_without_resolved_cases(self) -> None:
        df = _cases([{"HOSPITAL": 1, "UTI": 2, "SUPORT_VEN": 3, "EVOLUCAO": 9}])
        assert _step(compute_severity_cascade(df), "icu")["lethality"] is None

    def test_missing_columns_do_not_break(self) -> None:
        result = compute_severity_cascade(pd.DataFrame({"X": [1, 2]}))
        assert [step["cases"] for step in result["steps"]] == [2, 0, 0, 0]

    def test_reliability_flag_follows_the_minimum(self) -> None:
        many = _cases(
            [{"HOSPITAL": 1, "UTI": 2, "SUPORT_VEN": 3, "EVOLUCAO": 1}] * MIN_RELIABLE_RESOLVED
        )
        few = many.head(MIN_RELIABLE_RESOLVED - 1)
        assert _step(compute_severity_cascade(many), "notified")["reliable"] is True
        assert _step(compute_severity_cascade(few), "notified")["reliable"] is False


class TestWarningSigns:
    def _dataset(self) -> pd.DataFrame:
        rows = []
        # 10 com dispneia: 5 óbitos; 10 sem dispneia: 1 óbito.
        rows += [{"DISPNEIA": 1, "DESC_RESP": 2, "SATURACAO": 2, "EVOLUCAO": 2}] * 5
        rows += [{"DISPNEIA": 1, "DESC_RESP": 2, "SATURACAO": 2, "EVOLUCAO": 1}] * 5
        rows += [{"DISPNEIA": 2, "DESC_RESP": 2, "SATURACAO": 2, "EVOLUCAO": 2}] * 1
        rows += [{"DISPNEIA": 2, "DESC_RESP": 2, "SATURACAO": 2, "EVOLUCAO": 1}] * 9
        return _cases(rows)

    def test_empty_dataframe(self) -> None:
        assert compute_warning_signs(pd.DataFrame()) == {"baseline": None, "signs": []}

    def test_lethality_with_and_without_the_sign(self) -> None:
        result = compute_warning_signs(self._dataset())
        dispneia = next(sign for sign in result["signs"] if sign["key"] == "dispneia")
        assert dispneia["lethality"] == 50.0
        assert dispneia["lethality_without"] == 10.0
        assert dispneia["cases"] == 10
        assert result["baseline"] == 30.0

    def test_signs_are_sorted_by_lethality(self) -> None:
        signs = compute_warning_signs(self._dataset())["signs"]
        values = [sign["lethality"] if sign["lethality"] is not None else -1 for sign in signs]
        assert values == sorted(values, reverse=True)
        assert signs[0]["key"] == "dispneia"

    def test_sign_nobody_has_gets_none_lethality(self) -> None:
        result = compute_warning_signs(self._dataset())
        saturacao = next(sign for sign in result["signs"] if sign["key"] == "saturacao")
        assert saturacao["cases"] == 0
        assert saturacao["lethality"] is None
        assert saturacao["lethality_without"] == 30.0

    def test_missing_symptom_columns_do_not_break(self) -> None:
        result = compute_warning_signs(pd.DataFrame({"EVOLUCAO": [1, 2]}))
        assert all(sign["cases"] == 0 for sign in result["signs"])


class TestRiskFactorLoad:
    def _dataset(self) -> pd.DataFrame:
        return _cases(
            [
                {"DIABETES": 2, "CARDIOPATI": 2, "RENAL": 2, "EVOLUCAO": 1},
                {"DIABETES": 1, "CARDIOPATI": 2, "RENAL": 2, "EVOLUCAO": 1},
                {"DIABETES": 1, "CARDIOPATI": 1, "RENAL": 2, "EVOLUCAO": 2},
                {"DIABETES": 1, "CARDIOPATI": 1, "RENAL": 1, "EVOLUCAO": 2},
                {"DIABETES": 1, "CARDIOPATI": 1, "RENAL": 1, "EVOLUCAO": 1},
            ]
        )

    def test_empty_dataframe(self) -> None:
        assert compute_risk_factor_load(pd.DataFrame()) == {
            "baseline": None,
            "factors": [],
            "buckets": [],
        }

    def test_buckets_group_cases_by_number_of_factors(self) -> None:
        result = compute_risk_factor_load(self._dataset())
        assert [bucket["key"] for bucket in result["buckets"]] == ["0", "1", "2", "3+"]
        assert [bucket["cases"] for bucket in result["buckets"]] == [1, 1, 1, 2]

    def test_lethality_per_bucket(self) -> None:
        buckets = compute_risk_factor_load(self._dataset())["buckets"]
        assert [bucket["lethality"] for bucket in buckets] == [0.0, 0.0, 100.0, 50.0]

    def test_percentages_sum_to_one_hundred(self) -> None:
        buckets = compute_risk_factor_load(self._dataset())["buckets"]
        assert sum(bucket["pct"] for bucket in buckets) == pytest.approx(100.0)

    def test_other_factors_field_is_not_counted(self) -> None:
        df = _cases([{"OUT_MORBI": 1, "EVOLUCAO": 1}])
        buckets = compute_risk_factor_load(df)["buckets"]
        assert buckets[0]["cases"] == 1  # continua em "nenhum fator"
        assert "Outros fatores" not in compute_risk_factor_load(df)["factors"]

    def test_unknown_values_are_not_counted_as_factors(self) -> None:
        df = _cases([{"DIABETES": 9, "CARDIOPATI": 2, "EVOLUCAO": 1}])
        assert compute_risk_factor_load(df)["buckets"][0]["cases"] == 1
