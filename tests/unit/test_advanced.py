"""Unit tests for the analytical-charts computations (advanced.py)."""

from __future__ import annotations

import pandas as pd
import pytest

from srag.data.analytics.advanced import (
    _diagnostic_method,
    _odds_ratio_with_ci,
    compute_antiviral_windows,
    compute_clinical_flow,
    compute_comorbidities_odds_ratio,
    compute_diagnostic_lethality,
    compute_diagnostic_methods,
    compute_icu_access,
    compute_imaging_severity,
    compute_lab_performance,
    compute_nosocomial_risk,
    compute_notification_delay,
    compute_sample_positivity,
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


def _icu_df(cases: list[tuple[str, int]]) -> pd.DataFrame:
    """ICU cases given as (hospital admission date, days waited for the ICU)."""
    admitted = pd.to_datetime([date for date, _ in cases])
    entered = admitted + pd.to_timedelta([days for _, days in cases], unit="D")
    return pd.DataFrame({"UTI": 1, "DT_INTERNA": admitted, "DT_ENTUTI": entered})


class TestIcuAccess:
    def test_empty_dataframe_and_missing_columns(self) -> None:
        for frame in (pd.DataFrame(), pd.DataFrame({"UTI": [1]})):
            result = compute_icu_access(frame)
            assert result["periods"] == []
            assert result["summary"]["total"] == 0
            assert result["summary"]["status"] is None
            assert result["summary"]["same_day_pct"] == 0.0

    def test_bands_and_summary(self) -> None:
        cases = (
            [("2024-03-10", 0)] * 30
            + [("2024-03-10", 2)] * 20
            + [("2024-03-10", 5)] * 6
            + [("2024-03-10", 12)] * 4
        )
        result = compute_icu_access(_icu_df(cases))
        period = result["periods"][0]
        assert period["period"] == "2024"
        assert (period["total"], period["same_day"], period["d1_3"]) == (60, 30, 20)
        assert (period["d4_7"], period["d8_plus"]) == (6, 4)

        summary = result["summary"]
        assert summary["same_day_pct"] == 50.0
        assert summary["over_limit"] == 10  # waited more than 3 days
        assert summary["over_limit_pct"] == 16.7
        assert summary["median_wait_days"] == 2.0  # only among the 30 who waited
        assert summary["status"] == "adequado"

    def test_small_period_is_hidden_but_still_counted_in_the_summary(self) -> None:
        cases = [("2023-05-01", 0)] * 10 + [("2024-05-01", 1)] * 50
        result = compute_icu_access(_icu_df(cases))
        assert [period["period"] for period in result["periods"]] == ["2024"]
        assert result["summary"]["total"] == 60

    def test_ignores_non_icu_missing_dates_and_invalid_waits(self) -> None:
        df = pd.DataFrame(
            {
                "UTI": [1, 2, 1, 1, 1],
                "DT_INTERNA": pd.to_datetime(["2024-01-10"] * 5),
                "DT_ENTUTI": pd.to_datetime(
                    ["2024-01-10", "2024-01-10", None, "2024-01-09", "2024-02-20"]
                ),
            }
        )
        # valid: row 0 only (row 1 is not ICU, 2 has no date, 3 negative, 4 waited 41 days)
        assert compute_icu_access(df)["summary"]["total"] == 1

    @pytest.mark.parametrize(
        ("wait_days", "status"),
        [(2, "adequado"), (3, "atencao"), (4, "atencao"), (5, "critico")],
    )
    def test_status_grades_the_median_wait(self, wait_days: int, status: str) -> None:
        result = compute_icu_access(_icu_df([("2024-01-10", wait_days)] * 60))
        assert result["summary"]["status"] == status

    def test_month_and_quarter_keys(self) -> None:
        month = compute_icu_access(_icu_df([("2024-03-10", 1)] * 20), "month")
        quarter = compute_icu_access(_icu_df([("2024-03-10", 1)] * 30), "quarter")
        assert [period["period"] for period in month["periods"]] == ["2024-03"]
        assert [period["period"] for period in quarter["periods"]] == ["2024-Q1"]

    def test_minimum_cases_depend_on_the_granularity(self) -> None:
        few = _icu_df([("2024-03-10", 1)] * 19)
        assert compute_icu_access(few, "month")["periods"] == []
        assert compute_icu_access(few, "month")["min_cases"] == 20

    def test_unknown_granularity_falls_back_to_year(self) -> None:
        result = compute_icu_access(_icu_df([("2024-03-10", 1)] * 50), "semana")
        assert result["granularity"] == "year"


def _cases(onset: str, count: int, **columns: object) -> pd.DataFrame:
    """``count`` identical cases with the given symptom-onset date and columns."""
    return pd.DataFrame({"DT_SIN_PRI": pd.to_datetime([onset] * count), **columns})


class TestDiagnosticMethod:
    def test_classifies_each_closing_criterion(self) -> None:
        df = pd.DataFrame(
            {
                "CRITERIO": [1, 1, 1, 1, 2, 3, 4, None, 9],
                "PCR_RESUL": [1, 2, None, 1, None, None, None, None, None],
                "RES_AN": [None, 1, None, 1, None, None, None, None, None],
            }
        )
        assert _diagnostic_method(df).tolist() == [
            "RT-PCR",
            "Antígeno Rápido",
            "Outros Laboratoriais",
            "RT-PCR",  # RT-PCR wins when the antigen test is also positive
            "Clínico-Epidemiológico",
            "Clínico",
            "Clínico-Imagem",
            "Desconhecido",
            "Desconhecido",
        ]

    def test_missing_columns_are_unknown(self) -> None:
        assert _diagnostic_method(pd.DataFrame({"X": [1, 2]})).tolist() == ["Desconhecido"] * 2


class TestDiagnosticMethods:
    def test_empty_dataframe(self) -> None:
        result = compute_diagnostic_methods(pd.DataFrame())
        assert result["periods"] == []
        assert result["summary"]["total"] == 0
        assert result["summary"]["laboratory_pct"] == 0.0

    def test_groups_and_summary(self) -> None:
        df = pd.concat(
            [
                _cases("2024-03-10", 20, CRITERIO=1, PCR_RESUL=1),
                _cases("2024-03-10", 10, CRITERIO=1, RES_AN=1),
                _cases("2024-03-10", 15, CRITERIO=2),
                _cases("2024-03-10", 5, CRITERIO=3),
            ],
            ignore_index=True,
        )
        result = compute_diagnostic_methods(df)
        summary = result["summary"]
        assert (summary["rt_pcr"], summary["antigeno_outros"]) == (20, 10)
        assert (summary["clinico_epi"], summary["clinico_outros"]) == (15, 5)
        assert summary["laboratory_pct"] == 60.0
        assert summary["rt_pcr_pct"] == 40.0
        assert result["periods"] == [
            {
                "period": "2024",
                "total": 50,
                "rt_pcr": 20,
                "antigeno_outros": 10,
                "clinico_epi": 15,
                "clinico_outros": 5,
            }
        ]

    def test_small_periods_are_hidden_but_counted_in_the_summary(self) -> None:
        df = pd.concat(
            [_cases("2023-01-10", 10, CRITERIO=2), _cases("2024-01-10", 50, CRITERIO=2)],
            ignore_index=True,
        )
        result = compute_diagnostic_methods(df)
        assert [period["period"] for period in result["periods"]] == ["2024"]
        assert result["summary"]["total"] == 60

    def test_cases_without_onset_date_count_only_in_the_summary(self) -> None:
        df = pd.concat(
            [_cases("2024-01-10", 50, CRITERIO=2), pd.DataFrame({"CRITERIO": [2] * 5})],
            ignore_index=True,
        )
        result = compute_diagnostic_methods(df)
        assert result["summary"]["total"] == 55
        assert result["periods"][0]["total"] == 50

    def test_quarter_keys(self) -> None:
        result = compute_diagnostic_methods(_cases("2024-05-01", 30, CRITERIO=2), "quarter")
        assert [period["period"] for period in result["periods"]] == ["2024-Q2"]


class TestNosocomialRisk:
    def test_empty_and_missing_column(self) -> None:
        for frame in (pd.DataFrame(), pd.DataFrame({"DT_SIN_PRI": ["2024-01-01"]})):
            result = compute_nosocomial_risk(frame)
            assert result["periods"] == []
            assert result["summary"]["known"] == 0
            assert result["summary"]["lethality"]["nosocomial"]["pct"] is None

    def test_percentage_ignores_unknown_origin(self) -> None:
        df = pd.concat(
            [
                _cases("2024-03-10", 3, NOSOCOMIAL=1),
                _cases("2024-03-10", 47, NOSOCOMIAL=2),
                _cases("2024-03-10", 20, NOSOCOMIAL=9),  # ignored origin
            ],
            ignore_index=True,
        )
        result = compute_nosocomial_risk(df)
        assert result["summary"]["known"] == 50
        assert result["summary"]["nosocomial_pct"] == 6.0
        assert result["periods"][0]["pct"] == 6.0
        assert result["alert_limit_pct"] is None  # a single period cannot define a limit

    def test_lethality_by_origin(self) -> None:
        df = pd.DataFrame(
            {
                "NOSOCOMIAL": [1] * 4 + [2] * 10,
                "EVOLUCAO": [2, 2, 1, 1] + [2] + [1] * 9,
            }
        )
        lethality = compute_nosocomial_risk(df)["summary"]["lethality"]
        assert lethality["nosocomial"] == {"resolved": 4, "deaths": 2, "pct": 50.0}
        assert lethality["community"] == {"resolved": 10, "deaths": 1, "pct": 10.0}

    def test_alert_flags_a_period_above_mean_plus_three_sigmas(self) -> None:
        months = [f"2024-{month:02d}-10" for month in range(1, 13)]
        frames = [_cases(day, 20, NOSOCOMIAL=[1] + [2] * 19) for day in months[:-1]] + [
            _cases(months[-1], 20, NOSOCOMIAL=[1] * 12 + [2] * 8)
        ]
        result = compute_nosocomial_risk(pd.concat(frames, ignore_index=True), "month")
        assert len(result["periods"]) == 12
        assert result["alert_limit_pct"] is not None
        flagged = [period["period"] for period in result["periods"] if period["alert"]]
        assert flagged == ["2024-12"]

    def test_no_alert_limit_with_few_periods(self) -> None:
        months = [f"2024-{month:02d}-10" for month in range(1, 7)]
        df = pd.concat(
            [_cases(day, 20, NOSOCOMIAL=[1] * 10 + [2] * 10) for day in months], ignore_index=True
        )
        result = compute_nosocomial_risk(df, "month")
        assert result["alert_limit_pct"] is None
        assert result["mean_pct"] == 50.0
        assert not any(period["alert"] for period in result["periods"])


class TestDiagnosticLethality:
    def _dataset(self) -> pd.DataFrame:
        def block(criterion: int, deaths: int, total: int, days: int, **extra: object):
            return pd.DataFrame(
                {
                    "CRITERIO": criterion,
                    "EVOLUCAO": [2] * deaths + [1] * (total - deaths),
                    "DT_NOTIFIC": pd.to_datetime(["2024-01-01"] * total),
                    "DT_EVOLUCA": pd.to_datetime(["2024-01-01"] * total) + pd.Timedelta(days=days),
                    "UTI": [1] * (total // 2) + [2] * (total - total // 2),
                    **extra,
                }
            )

        return pd.concat(
            [
                block(1, 10, 20, 10, PCR_RESUL=1),  # RT-PCR: 50% lethality
                block(2, 2, 20, 4),  # clinical-epidemiological: 10%
                block(3, 1, 5, 4),  # clinical: too few resolved cases
            ],
            ignore_index=True,
        )

    def test_ranks_methods_by_lethality(self) -> None:
        result = compute_diagnostic_lethality(self._dataset())
        assert [row["method"] for row in result["methods"]] == [
            "RT-PCR",
            "Clínico-Epidemiológico",
        ]
        rt_pcr = result["methods"][0]
        assert (rt_pcr["cases"], rt_pcr["resolved"], rt_pcr["deaths"]) == (20, 20, 10)
        assert rt_pcr["cfr"] == 50.0
        assert rt_pcr["median_days"] == 10.0
        assert rt_pcr["icu_pct"] == 50.0

    def test_hides_methods_with_too_few_resolved_cases(self) -> None:
        result = compute_diagnostic_lethality(self._dataset())
        assert result["hidden"] == ["Clínico"]
        assert result["min_resolved"] == 10

    def test_overall_lethality(self) -> None:
        overall = compute_diagnostic_lethality(self._dataset())["overall"]
        assert (overall["cases"], overall["resolved"], overall["deaths"]) == (45, 45, 13)
        assert overall["cfr"] == pytest.approx(28.9, abs=0.05)

    def test_empty_dataframe_and_missing_outcome(self) -> None:
        for frame in (pd.DataFrame(), pd.DataFrame({"CRITERIO": [1]})):
            result = compute_diagnostic_lethality(frame)
            assert result["methods"] == []
            assert result["overall"]["cfr"] is None

    def test_unfinished_cases_do_not_count_as_resolved(self) -> None:
        df = pd.DataFrame({"CRITERIO": 2, "EVOLUCAO": [2] * 5 + [1] * 5 + [9] * 10})
        row = compute_diagnostic_lethality(df)["methods"][0]
        assert (row["cases"], row["resolved"], row["cfr"]) == (20, 10, 50.0)


class TestLabPerformance:
    def _dataset(self) -> pd.DataFrame:
        nat = pd.NaT
        rows = [
            # PCR_RESUL, RES_AN, AMOSTRA, DT_COLETA, DT_PCR, DT_RES_AN
            (1, None, 1, "2024-01-01", "2024-01-03", nat),  # RT-PCR positive, 2 days
            (2, None, 1, "2024-01-01", "2024-01-06", nat),  # negative, 5 days
            (3, None, 1, "2024-01-01", "2024-01-12", nat),  # inconclusive, 11 days
            (5, None, 1, "2024-01-01", nat, nat),  # awaiting result: no result yet
            (None, 1, 1, "2024-01-01", nat, "2024-01-02"),  # antigen positive, 1 day
            (None, 2, 1, "2024-01-01", nat, "2024-01-04"),  # antigen negative, 3 days
            (None, None, 2, nat, nat, nat),  # no sample collected
            (None, None, None, nat, nat, nat),
            (None, None, 1, nat, nat, nat),  # collected but no result
            (1, None, 1, "2024-01-10", "2024-01-05", nat),  # result before collection: error
        ]
        return pd.DataFrame(
            rows,
            columns=["PCR_RESUL", "RES_AN", "AMOSTRA", "DT_COLETA", "DT_PCR", "DT_RES_AN"],
        ).assign(
            DT_COLETA=lambda d: pd.to_datetime(d["DT_COLETA"]),
            DT_PCR=lambda d: pd.to_datetime(d["DT_PCR"]),
            DT_RES_AN=lambda d: pd.to_datetime(d["DT_RES_AN"]),
        )

    def test_coverage_indicators(self) -> None:
        result = compute_lab_performance(self._dataset())
        assert result["total"] == 10
        # results: rows 0, 1, 2, 4, 5, 9 (code 5 = awaiting does not count)
        assert (result["result"]["count"], result["result"]["pct"]) == (6, 60.0)
        assert (result["collection"]["count"], result["collection"]["pct"]) == (8, 80.0)
        assert result["result"]["target_pct"] == result["collection"]["target_pct"] == 80

    def test_rt_pcr_latency_ignores_invalid_waits(self) -> None:
        latency = compute_lab_performance(self._dataset())["rt_pcr_latency"]
        assert latency["count"] == 3  # 2, 5 and 11 days; the negative wait is dropped
        assert latency["median"] == 5.0
        assert latency["p95"] == 10.4
        assert latency["within_target_pct"] == pytest.approx(66.7, abs=0.05)  # 2 of 3 <= 7 days
        assert latency["target_days"] == 7

    def test_turnaround_mixes_rt_pcr_and_antigen(self) -> None:
        turnaround = compute_lab_performance(self._dataset())["turnaround"]
        assert turnaround["count"] == 5  # 2, 5, 11 (RT-PCR) and 1, 3 (antigen)
        assert turnaround["mean"] == 4.4
        assert turnaround["median"] == 3.0
        assert turnaround["p90"] == 8.6
        assert turnaround["target_days"] == 2

    def test_positivity_among_cases_with_a_result(self) -> None:
        positivity = compute_lab_performance(self._dataset())["positivity"]
        assert positivity == {"tested": 6, "positive": 3, "pct": 50.0}

    def test_empty_and_missing_columns(self) -> None:
        for frame in (pd.DataFrame(), pd.DataFrame({"X": [1, 2]})):
            result = compute_lab_performance(frame)
            assert result["result"]["count"] == 0
            assert result["rt_pcr_latency"]["median"] is None
            assert result["rt_pcr_latency"]["within_target_pct"] is None
            assert result["turnaround"]["mean"] is None
            assert result["positivity"]["pct"] is None


class TestSamplePositivity:
    def _dataset(self) -> pd.DataFrame:
        naso = {"TP_AMOSTRA": 1, "PCR_RESUL": [1] * 15 + [2] * 5}
        other = {"TP_AMOSTRA": 4, "PCR_RESUL": [1] + [2] * 11}
        csf = {"TP_AMOSTRA": 5, "PCR_RESUL": [2] * 3}
        no_result = {"TP_AMOSTRA": 1, "PCR_RESUL": [None] * 4}
        return pd.concat(
            [pd.DataFrame(block) for block in (naso, other, csf, no_result)], ignore_index=True
        )

    def test_ranks_sample_types_by_volume(self) -> None:
        result = compute_sample_positivity(self._dataset())
        assert [row["sample_type"] for row in result["types"]] == [
            "Secreção naso/orofaringe",
            "Outra",
        ]
        naso, other = result["types"]
        assert (naso["tested"], naso["positive"], naso["positivity_pct"]) == (20, 15, 75.0)
        assert (other["tested"], other["positive"], other["positivity_pct"]) == (12, 1, 8.3)

    def test_small_types_are_listed_as_hidden(self) -> None:
        result = compute_sample_positivity(self._dataset())
        assert result["hidden"] == ["LCR"]
        assert result["min_tested"] == 10

    def test_overall_positivity_counts_only_cases_with_a_result(self) -> None:
        overall = compute_sample_positivity(self._dataset())["overall"]
        assert overall == {"tested": 35, "positive": 16, "pct": 45.7}

    def test_unknown_sample_type_is_grouped(self) -> None:
        df = pd.DataFrame({"PCR_RESUL": [2] * 12})
        types = compute_sample_positivity(df)["types"]
        assert [row["sample_type"] for row in types] == ["Não informado"]

    def test_empty_dataframe(self) -> None:
        result = compute_sample_positivity(pd.DataFrame())
        assert result["types"] == []
        assert result["overall"]["pct"] is None


class TestAntiviralWindows:
    def _dataset(self) -> pd.DataFrame:
        def treated(offset: int, evolucao: int, count: int) -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "ANTIVIRAL": 1,
                    "DT_SIN_PRI": pd.to_datetime(["2024-01-01"] * count),
                    "DT_ANTIVIR": pd.to_datetime(["2024-01-01"] * count)
                    + pd.Timedelta(days=offset),
                    "EVOLUCAO": evolucao,
                }
            )

        blocks = [
            treated(0, 1, 4),  # up to 1 day: 4 cures
            treated(2, 1, 3),
            treated(2, 2, 1),  # 2 days: 3 cures, 1 death
            treated(4, 1, 2),
            treated(4, 2, 2),  # 3 to 5 days: 2 cures, 2 deaths
            treated(8, 1, 2),
            treated(8, 2, 2),  # over 5 days: 2 cures, 2 deaths
            treated(20, 1, 2),  # start date too far from onset: not usable
            treated(1, 9, 1),  # unfinished outcome: not counted in any window
            pd.DataFrame({"ANTIVIRAL": 2, "EVOLUCAO": [1] * 7 + [2] * 3}),  # no antiviral
        ]
        return pd.concat(blocks, ignore_index=True)

    def test_outcome_per_window(self) -> None:
        windows = {w["key"]: w for w in compute_antiviral_windows(self._dataset())["windows"]}
        assert (windows["le1"]["total"], windows["le1"]["cure_pct"]) == (4, 100.0)
        assert (windows["d2"]["cure"], windows["d2"]["death"], windows["d2"]["cure_pct"]) == (
            3,
            1,
            75.0,
        )
        assert (windows["d3_5"]["cure_pct"], windows["d3_5"]["death_pct"]) == (50.0, 50.0)
        assert (windows["gt5"]["total"], windows["gt5"]["death_pct"]) == (4, 50.0)
        assert (windows["none"]["total"], windows["none"]["cure_pct"]) == (10, 70.0)

    def test_summary_indicators(self) -> None:
        result = compute_antiviral_windows(self._dataset())
        assert result["treated"] == 19
        assert result["with_dates"] == 17  # the 2 cases starting after 20 days are unusable
        assert result["median_days"] == 2.0
        assert result["within_2d_pct"] == 52.9  # 9 of 17 started within 2 days
        assert result["cure_within_2d_pct"] == 87.5  # 7 cures in 8 closed cases
        assert result["cure_without_antiviral_pct"] == 70.0
        assert result["death_after_5d_pct"] == 50.0

    def test_windows_keep_a_fixed_order(self) -> None:
        keys = [w["key"] for w in compute_antiviral_windows(self._dataset())["windows"]]
        assert keys == ["le1", "d2", "d3_5", "gt5", "none"]

    def test_without_treated_cases(self) -> None:
        df = pd.DataFrame({"ANTIVIRAL": [2, 2], "EVOLUCAO": [1, 1]})
        result = compute_antiviral_windows(df)
        assert result["treated"] == 0
        assert result["median_days"] is None
        assert result["within_2d_pct"] is None
        assert result["cure_within_2d_pct"] is None

    def test_empty_and_missing_outcome(self) -> None:
        for frame in (pd.DataFrame(), pd.DataFrame({"ANTIVIRAL": [1]})):
            result = compute_antiviral_windows(frame)
            assert result["windows"] == []
            assert result["treated"] == 0


class TestImagingSeverity:
    def _dataset(self) -> pd.DataFrame:
        normal = pd.DataFrame(
            {
                "RAIOX_RES": 1,
                "UTI": [1] * 3 + [2] * 9,
                "EVOLUCAO": [2] * 1 + [1] * 11,
            }
        )
        consolidation = pd.DataFrame(
            {
                "RAIOX_RES": 3,
                "UTI": [1] * 8 + [2] * 2,
                "EVOLUCAO": [2] * 5 + [1] * 4 + [9],
            }
        )
        few = pd.DataFrame({"RAIOX_RES": 2, "UTI": [1] * 4, "EVOLUCAO": [2] * 4})
        return pd.concat([normal, consolidation, few], ignore_index=True)

    def test_icu_and_lethality_per_finding(self) -> None:
        rows = {
            row["finding"]: row
            for row in compute_imaging_severity(self._dataset())["xray"]["rows"]
        }
        assert rows["Normal"]["total"] == 12
        assert rows["Normal"]["icu_pct"] == 25.0
        assert rows["Normal"]["death_pct"] == 8.3  # 1 death in 12 closed cases
        # 10 cases, one unfinished: lethality uses only the 9 with a known outcome
        assert rows["Consolidação"]["resolved"] == 9
        assert rows["Consolidação"]["death_pct"] == 55.6
        assert rows["Consolidação"]["icu_pct"] == 80.0

    def test_rare_findings_are_hidden_and_rows_follow_volume(self) -> None:
        xray = compute_imaging_severity(self._dataset())["xray"]
        assert xray["hidden"] == ["Infiltrado intersticial"]
        assert [row["finding"] for row in xray["rows"]] == ["Normal", "Consolidação"]

    def test_missing_ct_column_gives_no_rows(self) -> None:
        ct = compute_imaging_severity(self._dataset())["ct"]
        assert ct == {"rows": [], "hidden": []}

    def test_empty_dataframe(self) -> None:
        result = compute_imaging_severity(pd.DataFrame())
        assert result["xray"]["rows"] == []
        assert result["ct"]["rows"] == []


class TestNotificationDelay:
    def _cases(self, bairro: str, delays: list[int]) -> pd.DataFrame:
        onset = pd.to_datetime(["2024-03-01"] * len(delays))
        return pd.DataFrame(
            {
                "BAIRRO_REF": bairro,
                "DT_SIN_PRI": onset,
                "DT_NOTIFIC": onset + pd.to_timedelta(delays, unit="D"),
            }
        )

    def _dataset(self) -> pd.DataFrame:
        return pd.concat(
            [
                self._cases("ALTO", [2, 3, 4, 4, 5, 6, -1, 61, 61]),  # 6 valid cases
                self._cases("MEIO", [8, 9, 10, 11, 12]),
                self._cases("BAIXO", [12, 12, 13, 14, 15]),
                self._cases("POUCOS", [3, 3, 3, 3]),  # below the minimum of 5 cases
                self._cases("NAO INFORMADO", [1] * 6),  # not a place
            ],
            ignore_index=True,
        )

    def test_ranks_bairros_from_the_longest_median_delay(self) -> None:
        result = compute_notification_delay(self._dataset())
        assert [row["bairro"] for row in result["bairros"]] == ["BAIXO", "MEIO", "ALTO"]

    def test_row_statistics_and_status(self) -> None:
        rows = {
            row["bairro"]: row for row in compute_notification_delay(self._dataset())["bairros"]
        }
        assert (rows["ALTO"]["total"], rows["ALTO"]["median_days"]) == (6, 4.0)
        assert rows["ALTO"]["within_limit_pct"] == 100.0
        assert rows["ALTO"]["status"] == "adequado"  # median <= 5
        assert rows["MEIO"]["median_days"] == 10.0
        assert rows["MEIO"]["status"] == "atencao"  # median <= 10
        assert rows["MEIO"]["within_limit_pct"] == 0.0
        assert (rows["BAIXO"]["median_days"], rows["BAIXO"]["mean_days"]) == (13.0, 13.2)
        assert rows["BAIXO"]["status"] == "critico"

    def test_small_bairros_are_counted_but_not_ranked(self) -> None:
        result = compute_notification_delay(self._dataset())
        assert result["hidden_count"] == 1
        assert "POUCOS" not in [row["bairro"] for row in result["bairros"]]

    def test_unknown_bairro_is_never_ranked_but_counts_in_the_overall(self) -> None:
        result = compute_notification_delay(self._dataset())
        assert "NAO INFORMADO" not in [row["bairro"] for row in result["bairros"]]
        # 26 valid delays (negative and >60 excluded); 16 of them within 7 days
        assert result["overall"]["total"] == 26
        assert result["overall"]["median_days"] == 4.0
        assert result["overall"]["within_limit_pct"] == 61.5
        assert result["overall"]["status"] == "adequado"

    def test_thresholds_are_exposed(self) -> None:
        result = compute_notification_delay(self._dataset())
        assert (result["limit_days"], result["warn_days"], result["critical_days"]) == (7, 5, 10)
        assert result["min_cases"] == 5

    def test_empty_and_missing_columns(self) -> None:
        for frame in (pd.DataFrame(), pd.DataFrame({"BAIRRO_REF": ["A"]})):
            result = compute_notification_delay(frame)
            assert result["bairros"] == []
            assert result["overall"]["median_days"] is None
            assert result["overall"]["status"] is None

    def test_without_bairro_column_only_the_overall_exists(self) -> None:
        df = self._dataset().drop(columns=["BAIRRO_REF"])
        result = compute_notification_delay(df)
        assert result["bairros"] == []
        assert result["overall"]["total"] == 26
