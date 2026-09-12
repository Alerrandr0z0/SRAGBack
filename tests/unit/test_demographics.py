import numpy as np
import pandas as pd

from srag.data.analytics.demographics import (
    categorize_age,
    compute_citizen_pyramid,
    compute_population_pyramid,
    compute_race_profile,
    compute_schooling_profile,
)


class TestCategorizeAge:
    def test_exact_boundaries(self) -> None:
        boundaries = [
            (0, "0-1 ano"),
            (1, "0-1 ano"),
            (2, "2-4 anos"),
            (4, "2-4 anos"),
            (5, "5-9 anos"),
            (9, "5-9 anos"),
            (10, "10-14 anos"),
            (14, "10-14 anos"),
            (15, "15-19 anos"),
            (19, "15-19 anos"),
            (20, "20-29 anos"),
            (29, "20-29 anos"),
            (30, "30-39 anos"),
            (39, "30-39 anos"),
            (40, "40-49 anos"),
            (49, "40-49 anos"),
            (50, "50-59 anos"),
            (59, "50-59 anos"),
            (60, "60-69 anos"),
            (69, "60-69 anos"),
            (70, "70-79 anos"),
            (79, "70-79 anos"),
            (80, "80+ anos"),
            (120, "80+ anos"),
        ]
        for age, expected in boundaries:
            assert categorize_age(age) == expected, f"age={age} expected={expected}"

    def test_negative_age(self) -> None:
        assert categorize_age(-1) == "0-1 ano"


class TestCitizenPyramid:
    def test_fixed_categorize_age_bands(self) -> None:
        df = pd.DataFrame(
            {
                "NU_IDADE_N": [10, 12, 14, 16, 18, 20],
                "TP_IDADE": [3, 3, 3, 3, 3, 3],
                "CS_SEXO": ["M", "F", "M", "F", "M", "F"],
            }
        )
        res = compute_citizen_pyramid(df)
        assert [r["age_band"] for r in res] == [
            "0-1 ano",
            "2-4 anos",
            "5-9 anos",
            "10-14 anos",
            "15-19 anos",
            "20-29 anos",
            "30-39 anos",
            "40-49 anos",
            "50-59 anos",
            "60-69 anos",
            "70-79 anos",
            "80+ anos",
        ]
        by_band = {r["age_band"]: r for r in res}
        assert by_band["10-14 anos"]["male"] == 2
        assert by_band["10-14 anos"]["female"] == 1
        assert by_band["15-19 anos"]["male"] == 1
        assert by_band["15-19 anos"]["female"] == 1
        assert by_band["20-29 anos"]["female"] == 1

    def test_large_range_uses_fixed_bands(self) -> None:
        df = pd.DataFrame(
            {
                "NU_IDADE_N": [5, 15, 25, 35, 45, 55, 65, 75, 85],
                "TP_IDADE": [3, 3, 3, 3, 3, 3, 3, 3, 3],
                "CS_SEXO": ["M", "F", "M", "F", "M", "F", "M", "F", "M"],
            }
        )
        res = compute_citizen_pyramid(df)
        assert len(res) == 12
        by_band = {r["age_band"]: r for r in res}
        assert by_band["5-9 anos"]["male"] == 1
        assert by_band["80+ anos"]["male"] == 1

    def test_last_label_80_plus(self) -> None:
        df = pd.DataFrame(
            {
                "NU_IDADE_N": [5, 20, 40, 60, 85],
                "TP_IDADE": [3, 3, 3, 3, 3],
                "CS_SEXO": ["M", "F", "M", "F", "M"],
            }
        )
        res = compute_citizen_pyramid(df)
        assert "80+" in res[-1]["age_band"]

    def test_empty_df(self) -> None:
        assert compute_citizen_pyramid(pd.DataFrame()) == []

    def test_all_nan_age(self) -> None:
        df = pd.DataFrame(
            {"NU_IDADE_N": [np.nan, np.nan], "TP_IDADE": [3, 3], "CS_SEXO": ["M", "F"]}
        )
        assert compute_citizen_pyramid(df) == []


class TestPopulationPyramid:
    def test_single_year_buckets(self) -> None:
        df = pd.DataFrame(
            {
                "NU_IDADE_N": [20, 20, 21, 30],
                "TP_IDADE": [3, 3, 3, 3],
                "CS_SEXO": ["M", "F", "M", "F"],
            }
        )
        res = compute_population_pyramid(df)
        assert [r["age"] for r in res] == list(range(31))
        by_age = {r["age"]: r for r in res}
        assert by_age[20] == {"age": 20, "male": 1, "female": 1}
        assert by_age[21] == {"age": 21, "male": 1, "female": 0}
        assert by_age[30] == {"age": 30, "male": 0, "female": 1}
        assert by_age[0] == {"age": 0, "male": 0, "female": 0}

    def test_empty_and_all_nan(self) -> None:
        assert compute_population_pyramid(pd.DataFrame()) == []
        df = pd.DataFrame({"NU_IDADE_N": [np.nan], "TP_IDADE": [3], "CS_SEXO": ["M"]})
        assert compute_population_pyramid(df) == []


class TestRaceProfile:
    def test_exact_code_mapping(self) -> None:
        df = pd.DataFrame({"CS_RACA": [1, 2, 3, 4, 5]})
        res = {r["label"]: r["count"] for r in compute_race_profile(df)}
        assert res["Branca"] == 1
        assert res["Preta"] == 1
        assert res["Amarela"] == 1
        assert res["Parda"] == 1
        assert res["Indígena"] == 1

    def test_code_9_ignored(self) -> None:
        df = pd.DataFrame({"CS_RACA": [9, 1]})
        res = {r["label"]: r["count"] for r in compute_race_profile(df)}
        assert res == {"Branca": 1}

    def test_empty_df(self) -> None:
        assert compute_race_profile(pd.DataFrame()) == []

    def test_missing_column(self) -> None:
        assert compute_race_profile(pd.DataFrame({"OUTRA": [1]})) == []


class TestSchoolingProfile:
    def test_exact_mapping(self) -> None:
        df = pd.DataFrame(
            {
                "NU_IDADE_N": [30, 30, 30, 30, 30, 30],
                "TP_IDADE": [3, 3, 3, 3, 3, 3],
                "CS_ESCOL_N": [0, 1, 2, 3, 4, 9],
            }
        )
        res = {r["label"]: r["count"] for r in compute_schooling_profile(df)}
        assert res["Sem escolaridade"] == 1

    def test_escol_5_with_age_ge_7_filtered(self) -> None:
        df = pd.DataFrame(
            {
                "NU_IDADE_N": [30, 5],
                "TP_IDADE": [3, 3],
                "CS_ESCOL_N": [5, 5],
            }
        )
        res = {r["label"]: r["count"] for r in compute_schooling_profile(df)}
        assert "Não se aplica" in res
        assert res["Não se aplica"] == 1

    def test_empty_df(self) -> None:
        assert compute_schooling_profile(pd.DataFrame()) == []

    def test_missing_column(self) -> None:
        assert compute_schooling_profile(pd.DataFrame({"NU_IDADE_N": [30]})) == []


class TestAgePareto:
    def test_sorted_desc_and_cumulative_closes_at_100(self) -> None:
        from srag.data.analytics.demographics import compute_age_pareto

        df = pd.DataFrame(
            {
                "NU_IDADE_N": [65, 70, 66, 67, 5, 30],
                "TP_IDADE": [3, 3, 3, 3, 3, 3],
            }
        )
        res = compute_age_pareto(df)
        counts = [r["count"] for r in res]
        assert counts == sorted(counts, reverse=True)
        assert res[0] == {"label": "60-69 anos", "count": 3, "cumulative": 50.0}
        assert res[-1]["cumulative"] == 100.0
        assert sum(counts) == 6

    def test_empty_df(self) -> None:
        from srag.data.analytics.demographics import compute_age_pareto

        assert compute_age_pareto(pd.DataFrame()) == []
