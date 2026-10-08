"""Unit tests for the analytical-charts computations (advanced.py)."""

from __future__ import annotations

import pandas as pd
import pytest

from srag.data.analytics.advanced import (
    _odds_ratio_with_ci,
    compute_clinical_flow,
    compute_comorbidities_odds_ratio,
    compute_symptoms_signature,
)


class TestClinicalFlow:
    def test_empty_dataframe(self) -> None:
        assert compute_clinical_flow(pd.DataFrame()) == {"nodes": [], "links": []}

    def test_links_follow_the_four_stages(self) -> None:
        df = pd.DataFrame(
            {
                "NOSOCOMIAL": [2, 2, 2, 1],
                "UTI": [1, 1, 2, 2],
                "SUPORT_VEN": [1, 3, 3, 3],
                "EVOLUCAO": [2, 1, 1, 1],
            }
        )
        flow = compute_clinical_flow(df)
        links = {(link["source"], link["target"]): link for link in flow["links"]}

        assert links[("Comunitária", "Internado em UTI")]["value"] == 2
        assert links[("Comunitária", "Internado em Enfermaria")]["value"] == 1
        assert links[("Infecção Hospitalar", "Internado em Enfermaria")]["value"] == 1
        assert links[("Vent. Invasiva", "Óbito")]["value"] == 1
        names = {node["name"] for node in flow["nodes"]}
        assert {"Comunitária", "Cura", "Óbito", "Sem Suporte"} <= names

    def test_percentages_sum_to_100_per_source(self) -> None:
        df = pd.DataFrame(
            {
                "NOSOCOMIAL": [2, 2, 2, 2],
                "UTI": [1, 1, 1, 2],
                "SUPORT_VEN": [3, 3, 3, 3],
                "EVOLUCAO": [1, 1, 2, 1],
            }
        )
        flow = compute_clinical_flow(df)
        by_source: dict[str, float] = {}
        for link in flow["links"]:
            by_source[link["source"]] = by_source.get(link["source"], 0.0) + link["pct"]
        assert all(abs(total - 100.0) < 0.2 for total in by_source.values())

    def test_missing_columns_fall_back_to_ignored_labels(self) -> None:
        df = pd.DataFrame({"EVOLUCAO": [1, 2]})
        flow = compute_clinical_flow(df)
        names = {node["name"] for node in flow["nodes"]}
        assert {"Origem (Ignorado)", "Internação (Ignorado)", "Suporte (Ignorado)"} <= names

    def test_unknown_outcome_is_open_case(self) -> None:
        df = pd.DataFrame({"EVOLUCAO": [9, None]})
        names = {node["name"] for node in compute_clinical_flow(df)["nodes"]}
        assert "Em Aberto" in names


class TestOddsRatio:
    def test_known_two_by_two_table(self) -> None:
        # a=10 b=5 c=5 d=20 -> OR = (10*20)/(5*5) = 8.0
        odds, lo, hi = _odds_ratio_with_ci(10, 5, 5, 20)
        assert odds == pytest.approx(8.0)
        assert lo == pytest.approx(1.87, abs=0.01)
        assert hi == pytest.approx(34.2, abs=0.1)

    def test_zero_cell_uses_haldane_correction(self) -> None:
        odds, lo, hi = _odds_ratio_with_ci(0, 5, 5, 20)
        assert odds > 0
        assert lo < odds < hi

    def _dataset(self) -> pd.DataFrame:
        # DIABETES: 10 dead + 5 alive exposed; 5 dead + 20 alive unexposed.
        rows = (
            [{"DIABETES": 1, "EVOLUCAO": 2}] * 10
            + [{"DIABETES": 1, "EVOLUCAO": 1}] * 5
            + [{"DIABETES": 2, "EVOLUCAO": 2}] * 5
            + [{"DIABETES": 2, "EVOLUCAO": 1}] * 20
        )
        return pd.DataFrame(rows)

    def test_row_matches_hand_calculation(self) -> None:
        rows = {row["name"]: row for row in compute_comorbidities_odds_ratio(self._dataset())}
        diabetes = rows["Diabetes"]
        assert diabetes["value"] == 15
        assert diabetes["deaths"] == 10
        assert diabetes["odds_ratio"] == pytest.approx(8.0)
        assert diabetes["lethality"] == pytest.approx(66.67, abs=0.01)
        assert diabetes["prevalence"] == pytest.approx(37.5)
        assert diabetes["ci_lower"] < diabetes["odds_ratio"] < diabetes["ci_upper"]

    def test_factor_without_exposed_cases_has_undefined_or(self) -> None:
        rows = {row["name"]: row for row in compute_comorbidities_odds_ratio(self._dataset())}
        # Column absent from the data -> no exposed cases -> OR reported as 0.
        assert rows["Asma"]["value"] == 0
        assert rows["Asma"]["odds_ratio"] == 0.0

    def test_sorted_by_odds_ratio_descending(self) -> None:
        result = compute_comorbidities_odds_ratio(self._dataset())
        ratios = [row["odds_ratio"] for row in result]
        assert ratios == sorted(ratios, reverse=True)
        assert result[0]["name"] == "Diabetes"

    def test_empty_dataframe(self) -> None:
        assert compute_comorbidities_odds_ratio(pd.DataFrame()) == []

    def test_without_outcome_column_everything_is_undefined(self) -> None:
        result = compute_comorbidities_odds_ratio(pd.DataFrame({"DIABETES": [1, 2]}))
        assert all(row["odds_ratio"] == 0.0 for row in result)


class TestSymptomsSignature:
    def _dataset(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "CLASSI_FIN": [5, 5, 5, 1, 1, 5],
                "PCR_VSR": [0, 0, 0, 0, 0, 1],
                "AN_VSR": [0, 0, 0, 0, 0, 0],
                "NU_IDADE_N": [30, 30, 70, 30, 30, 1],
                "TP_IDADE": [3, 3, 3, 3, 3, 3],
                "FEBRE": [1, 1, 1, 1, 2, 1],
                "TOSSE": [1, 2, 1, 1, 1, 1],
            }
        )

    def test_empty_dataframe(self) -> None:
        assert compute_symptoms_signature(pd.DataFrame()) == {
            "labels": [],
            "bands": [],
            "matrices": {},
        }

    def test_default_profile_uses_four_age_bands(self) -> None:
        result = compute_symptoms_signature(self._dataset())
        assert result["bands"] == ["Criança", "Adolescente", "Adulto", "Idoso"]
        assert set(result["matrices"]) == {"covid", "gripe", "vsr"}
        assert len(result["labels"]) == 13

    def test_prevalence_and_counts(self) -> None:
        result = compute_symptoms_signature(self._dataset())
        febre = result["labels"].index("Febre")
        adulto = result["bands"].index("Adulto")
        # COVID adults: rows 0 and 1 (age 30). Both have fever -> 100%, 2 cases.
        assert result["matrices"]["covid"][febre][adulto] == [100.0, 2]
        # Flu adults: rows 3 and 4. One of two has fever -> 50%, 1 case.
        assert result["matrices"]["gripe"][febre][adulto] == [50.0, 1]

    def test_vsr_positive_case_is_not_double_counted_as_covid(self) -> None:
        result = compute_symptoms_signature(self._dataset())
        febre = result["labels"].index("Febre")
        crianca = result["bands"].index("Criança")
        # Row 5 is CLASSI_FIN=5 but PCR_VSR=1 -> counted only under VSR.
        assert result["matrices"]["vsr"][febre][crianca] == [100.0, 1]
        assert result["matrices"]["covid"][febre][crianca] == [0.0, 0]

    def test_symptoms_sorted_by_total_prevalence(self) -> None:
        result = compute_symptoms_signature(self._dataset())
        totals = [
            sum(
                result["matrices"][agent][i][b][0]
                for agent in result["matrices"]
                for b in range(len(result["bands"]))
            )
            for i in range(len(result["labels"]))
        ]
        assert totals == sorted(totals, reverse=True)

    @pytest.mark.parametrize(
        ("profile", "expected"),
        [
            ("crianca", ["<2 anos", "2-5 anos", "6-11 anos"]),
            ("adolescente", ["12-14 anos", "15-19 anos"]),
            ("adulto", ["20-39 anos", "40-59 anos"]),
            ("idoso", ["60-69 anos", "70-79 anos", "80+ anos"]),
        ],
    )
    def test_profiles_change_the_bands(self, profile: str, expected: list[str]) -> None:
        assert compute_symptoms_signature(self._dataset(), profile)["bands"] == expected

    def test_unknown_profile_falls_back_to_all(self) -> None:
        result = compute_symptoms_signature(self._dataset(), "invalido")
        assert result["bands"] == ["Criança", "Adolescente", "Adulto", "Idoso"]
