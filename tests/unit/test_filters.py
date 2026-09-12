"""Mutation-targeted tests for filters.py: apply_global_filters."""

import numpy as np
import pandas as pd

from srag.data.analytics.filters import (
    age_years,
    apply_global_filters,
    outcome_death_mask,
)


class TestAgeYears:
    def test_tp_3_years(self) -> None:
        df = pd.DataFrame({"NU_IDADE_N": [0, 1, 149, 150], "TP_IDADE": [3, 3, 3, 3]})
        res = age_years(df)
        assert list(res) == [0.0, 1.0, 149.0, 150.0]

    def test_tp_2_months(self) -> None:
        df = pd.DataFrame({"NU_IDADE_N": [0, 1, 11, 12], "TP_IDADE": [2, 2, 2, 2]})
        res = age_years(df)
        expected = [0.0, round(1 / 12, 6), round(11 / 12, 6), 1.0]
        assert list(round(v, 6) for v in res) == expected

    def test_tp_1_days(self) -> None:
        df = pd.DataFrame({"NU_IDADE_N": [0, 1, 30, 365], "TP_IDADE": [1, 1, 1, 1]})
        res = age_years(df)
        assert list(round(v, 4) for v in res) == [
            0.0,
            round(1 / 365.25, 4),
            round(30 / 365.25, 4),
            round(365 / 365.25, 4),
        ]

    def test_tp_na_fallback_years(self) -> None:
        df = pd.DataFrame({"NU_IDADE_N": [5, 42], "TP_IDADE": [pd.NA, None]})
        res = age_years(df)
        assert list(res) == [5.0, 42.0]

    def test_idade_anos_column_preferred(self) -> None:
        df = pd.DataFrame(
            {"IDADE_ANOS": [25, pd.NA, 50], "NU_IDADE_N": [1, 2, 3], "TP_IDADE": [3, 3, 3]}
        )
        res = age_years(df)
        assert list(round(v, 1) for v in res.dropna()) == [25.0, 50.0]

    def test_nu_idade_zero_all_tp(self) -> None:
        for tp in [1, 2, 3]:
            df = pd.DataFrame({"NU_IDADE_N": [0], "TP_IDADE": [tp]})
            res = age_years(df)
            assert res.iloc[0] == 0.0


class TestOutcomeDeathMask:
    def test_exact_death_code_2(self) -> None:
        s = pd.Series([1, 2, 3, 9])
        res = outcome_death_mask(s)
        assert list(res) == [False, True, False, False]

    def test_non_numeric_coerced(self) -> None:
        s = pd.Series(["2", "foo", None, np.nan])
        res = outcome_death_mask(s)
        assert list(res) == [True, False, False, False]


class TestApplyGlobalFiltersEmpty:
    def test_empty_df_returns_empty(self) -> None:
        res = apply_global_filters(pd.DataFrame(), bairros=["CENTRO"])
        assert len(res) == 0

    def test_none_filters_returns_original(self) -> None:
        df = pd.DataFrame({"A": [1, 2]})
        res = apply_global_filters(df, bairros=None)
        assert list(res["A"]) == [1, 2]


class TestBairros:
    def test_bairro_case_normalized(self) -> None:
        df = pd.DataFrame({"BAIRRO_REF": ["CENTRO", "Centro", "centro"]})
        res = apply_global_filters(df, bairros=["CENTRO"])
        assert len(res) == 3

    def test_bairro_nan_filled(self) -> None:
        df = pd.DataFrame({"BAIRRO_REF": [None, "Centro"]})
        res = apply_global_filters(df, bairros=["CENTRO"])
        assert len(res) == 1

    def test_bairro_empty_list(self) -> None:
        df = pd.DataFrame({"BAIRRO_REF": ["Centro"]})
        res = apply_global_filters(df, bairros=[])
        assert len(res) == 1

    def test_bairro_empty_string_excluded(self) -> None:
        df = pd.DataFrame({"BAIRRO_REF": ["", "Centro"]})
        res = apply_global_filters(df, bairros=["CENTRO"])
        assert len(res) == 1


class TestRuralAggregateBairroFilter:
    def test_area_rural_matches_all_rural_zone_cases(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["SITIO X", "AREA RURAL DE MOSSORO", "CENTRO"],
                "ZONA": ["Rural", "Urbana", "Urbana"],
            }
        )
        out = apply_global_filters(df, bairros=["AREA RURAL DE MOSSORO"])
        assert sorted(out["BAIRRO_REF"].tolist()) == [
            "AREA RURAL DE MOSSORO",
            "SITIO X",
        ]

    def test_plain_bairro_unaffected(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["CENTRO", "ALTO"],
                "ZONA": ["Urbana", "Urbana"],
            }
        )
        out = apply_global_filters(df, bairros=["CENTRO"])
        assert out["BAIRRO_REF"].tolist() == ["CENTRO"]


class TestOfficialBairroRule:
    def test_non_official_urban_name_aggregates_as_rural(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["MAISA", "CENTRO", "AREA RURAL DE MOSSORO"],
                "ZONA": ["Urbana", "Urbana", "Urbana"],
            }
        )
        out = apply_global_filters(df, bairros=["AREA RURAL DE MOSSORO"])
        assert sorted(out["BAIRRO_REF"].tolist()) == [
            "AREA RURAL DE MOSSORO",
            "MAISA",
        ]

    def test_official_bairro_filter_unaffected(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["CENTRO", "MAISA"],
                "ZONA": ["Rural", "Urbana"],
            }
        )
        out = apply_global_filters(df, bairros=["CENTRO"])
        assert out["BAIRRO_REF"].tolist() == ["CENTRO"]


class TestNaoInformadoExcludedFromRuralAggregate:
    def test_nao_informado_not_matched_by_rural_filter(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["NAO INFORMADO", None, "SITIO X"],
                "ZONA": ["Urbana", "Urbana", "Rural"],
            }
        )
        out = apply_global_filters(df, bairros=["AREA RURAL DE MOSSORO"])
        assert out["BAIRRO_REF"].tolist() == ["SITIO X"]
