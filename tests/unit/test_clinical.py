import numpy as np
import pandas as pd

from srag.data.analytics.clinical import (
    compute_maternal_profile,
    compute_risk_factors_full_profile,
)


class TestRiskFactorsFullProfile:
    def test_exact_counts(self) -> None:
        df = pd.DataFrame(
            {
                "PUERPERA": [1, 2],
                "CARDIOPATI": [1, np.nan],
                "HEMATOLOGI": [np.nan, np.nan],
            }
        )
        res = {r["factor"]: r["count"] for r in compute_risk_factors_full_profile(df)}
        assert res["Puérpera"] == 1
        assert res["Cardiopatia"] == 1
        assert res["Doença hematológica"] == 0

    def test_missing_column_returns_zero(self) -> None:
        df = pd.DataFrame({"PUERPERA": [1]})
        res = {r["factor"]: r["count"] for r in compute_risk_factors_full_profile(df)}
        assert res["Cardiopatia"] == 0

    def test_empty_df(self) -> None:
        assert compute_risk_factors_full_profile(pd.DataFrame()) == []


class TestMaternalProfile:
    def test_counts_gestantes_1_to_4(self) -> None:
        df = pd.DataFrame(
            {
                "CS_SEXO": ["F", "F", "F", "F", "F", "M"],
                "CS_GESTANT": [1, 2, 3, 4, 5, 1],
            }
        )
        res = compute_maternal_profile(df)
        assert res == {"gestantes_total": 4}

    def test_empty_df_defaults(self) -> None:
        assert compute_maternal_profile(pd.DataFrame()) == {"gestantes_total": 0}

    def test_no_females(self) -> None:
        df = pd.DataFrame({"CS_SEXO": ["M", "M"], "CS_GESTANT": [1, 9]})
        assert compute_maternal_profile(df) == {"gestantes_total": 0}


class TestComorbiditiesPareto:
    def test_sorted_desc_with_cumulative(self) -> None:
        from srag.data.analytics.clinical import compute_comorbidities_pareto

        df = pd.DataFrame(
            {
                "DIABETES": [1, 1, 1, 2, 9],
                "CARDIOPATI": [1, 2, 2, 2, 2],
                "ASMA": [2, 2, 2, 2, 2],
            }
        )
        res = compute_comorbidities_pareto(df)
        assert [(r["name"], r["value"]) for r in res] == [
            ("Diabetes", 3),
            ("Cardiopatia", 1),
        ]
        assert res[-1]["cumulative"] == 100.0
        assert res[0]["cumulative"] == 75.0

    def test_empty_df(self) -> None:
        from srag.data.analytics.clinical import compute_comorbidities_pareto

        assert compute_comorbidities_pareto(pd.DataFrame()) == []


class TestFluVaccinationDonut:
    def test_fixed_order_and_sum(self) -> None:
        from srag.data.analytics.clinical import compute_flu_vaccination_donut

        df = pd.DataFrame({"VACINA": [1, 2, 9, 2], "DT_UT_DOSE": [None] * 4})
        res = compute_flu_vaccination_donut(df)
        assert [r["label"] for r in res] == [
            "Vacinado",
            "Não vacinado",
            "Ignorado",
        ]
        assert sum(r["count"] for r in res) == 4

    def test_empty_df_zeroed_slices(self) -> None:
        from srag.data.analytics.clinical import compute_flu_vaccination_donut

        res = compute_flu_vaccination_donut(pd.DataFrame())
        assert len(res) == 3
        assert all(r["count"] == 0 for r in res)
