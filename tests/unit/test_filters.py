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


class TestBaseAnalise:
    """Filtro 'Base de análise': notificados (default) / confirmados / obitos."""

    def test_default_none_returns_everyone(self) -> None:
        df = pd.DataFrame({"CLASSI_FIN": [1, 2, 3, 4, 5], "EVOLUCAO": [1, 2, 3, 9, 1]})
        out = apply_global_filters(df, base=None)
        assert len(out) == 5

    def test_notificados_explicit_returns_everyone(self) -> None:
        df = pd.DataFrame({"CLASSI_FIN": [1, 2, 3, 4, 5], "EVOLUCAO": [1, 2, 3, 9, 1]})
        out = apply_global_filters(df, base="notificados")
        assert len(out) == 5

    def test_confirmados_keeps_only_classi_fin_1_and_5(self) -> None:
        df = pd.DataFrame({"CLASSI_FIN": [1, 2, 3, 4, 5]})
        out = apply_global_filters(df, base="confirmados")
        assert sorted(out["CLASSI_FIN"].tolist()) == [1, 5]

    def test_confirmados_missing_column_returns_empty(self) -> None:
        df = pd.DataFrame({"OUTRA_COLUNA": [1, 2]})
        out = apply_global_filters(df, base="confirmados")
        assert len(out) == 0

    def test_obitos_keeps_only_evolucao_2(self) -> None:
        df = pd.DataFrame({"EVOLUCAO": [1, 2, 3, 9, 2]})
        out = apply_global_filters(df, base="obitos")
        assert len(out) == 2
        assert set(out["EVOLUCAO"]) == {2}

    def test_obitos_missing_column_returns_empty(self) -> None:
        df = pd.DataFrame({"OUTRA_COLUNA": [1, 2]})
        out = apply_global_filters(df, base="obitos")
        assert len(out) == 0

    def test_unknown_base_value_is_noop(self) -> None:
        df = pd.DataFrame({"CLASSI_FIN": [1, 2]})
        out = apply_global_filters(df, base="algo_invalido")
        assert len(out) == 2


class TestGravidade:
    """Filtro 'Gravidade': todos (default) / uti / internacao / ventilacao."""

    def test_default_none_returns_everyone(self) -> None:
        df = pd.DataFrame({"UTI": [1, 2, 9]})
        out = apply_global_filters(df, gravidade=None)
        assert len(out) == 3

    def test_todos_explicit_returns_everyone(self) -> None:
        df = pd.DataFrame({"UTI": [1, 2, 9]})
        out = apply_global_filters(df, gravidade="todos")
        assert len(out) == 3

    def test_uti_keeps_only_code_1(self) -> None:
        df = pd.DataFrame({"UTI": [1, 2, 9, None]})
        out = apply_global_filters(df, gravidade="uti")
        assert len(out) == 1

    def test_uti_missing_column_returns_empty(self) -> None:
        df = pd.DataFrame({"OUTRA": [1]})
        out = apply_global_filters(df, gravidade="uti")
        assert len(out) == 0

    def test_internacao_keeps_only_hospital_code_1(self) -> None:
        df = pd.DataFrame({"HOSPITAL": [1, 2, 9, None]})
        out = apply_global_filters(df, gravidade="internacao")
        assert len(out) == 1

    def test_ventilacao_keeps_invasiva_and_nao_invasiva(self) -> None:
        df = pd.DataFrame({"SUPORT_VEN": [1, 2, 3, 9, None]})
        out = apply_global_filters(df, gravidade="ventilacao")
        assert sorted(out["SUPORT_VEN"].tolist()) == [1, 2]

    def test_uti_and_internacao_are_not_mutually_exclusive(self) -> None:
        """Um caso com UTI==1 e HOSPITAL==1 conta nos dois filtros, sem exclusão."""
        df = pd.DataFrame({"UTI": [1, 1], "HOSPITAL": [1, 2]})
        uti_only = apply_global_filters(df, gravidade="uti")
        internacao_only = apply_global_filters(df, gravidade="internacao")
        assert len(uti_only) == 2
        assert len(internacao_only) == 1

    def test_unknown_gravidade_value_is_noop(self) -> None:
        df = pd.DataFrame({"UTI": [1, 2]})
        out = apply_global_filters(df, gravidade="algo_invalido")
        assert len(out) == 2


class TestSintomas:
    """Filtro 'Sintomatologia': multi-seleção com regra AND entre selecionados."""

    def test_none_returns_everyone(self) -> None:
        df = pd.DataFrame({"FEBRE": [1, 2]})
        out = apply_global_filters(df, sintomas=None)
        assert len(out) == 2

    def test_empty_list_returns_everyone(self) -> None:
        df = pd.DataFrame({"FEBRE": [1, 2]})
        out = apply_global_filters(df, sintomas=[])
        assert len(out) == 2

    def test_single_symptom_keeps_only_code_1(self) -> None:
        df = pd.DataFrame({"FEBRE": [1, 2, 9, None]})
        out = apply_global_filters(df, sintomas=["febre"])
        assert len(out) == 1

    def test_two_symptoms_use_and_logic(self) -> None:
        df = pd.DataFrame(
            {
                "FEBRE": [1, 1, 2, 1],
                "TOSSE": [1, 2, 1, 1],
            }
        )
        out = apply_global_filters(df, sintomas=["febre", "tosse"])
        # Só a linha 0 e a 3 têm os dois sintomas == 1.
        assert len(out) == 2

    def test_all_thirteen_symptom_keys_map_to_real_columns(self) -> None:
        from srag.data.references import SYMPTOM_FIELDS

        columns = {
            "FEBRE": 1,
            "TOSSE": 1,
            "GARGANTA": 1,
            "DISPNEIA": 1,
            "DESC_RESP": 1,
            "SATURACAO": 1,
            "DIARREIA": 1,
            "VOMITO": 1,
            "DOR_ABD": 1,
            "FADIGA": 1,
            "PERD_OLFT": 1,
            "PERD_PALA": 1,
            "OUTRO_SIN": 1,
        }
        df = pd.DataFrame({k: [v] for k, v in columns.items()})
        out = apply_global_filters(df, sintomas=list(SYMPTOM_FIELDS.keys()))
        assert len(out) == 1

    def test_unknown_symptom_key_is_ignored_defensively(self) -> None:
        df = pd.DataFrame({"FEBRE": [1, 2]})
        out = apply_global_filters(df, sintomas=["chave_invalida"])
        assert len(out) == 2


class TestFilterCombinations:
    """Combinação entre bairro/base/gravidade/sintomas — todos compostos com AND."""

    def test_bairro_and_base_combine(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["CENTRO", "CENTRO", "ABOLICAO"],
                "CLASSI_FIN": [1, 3, 1],
            }
        )
        out = apply_global_filters(df, bairros=["CENTRO"], base="confirmados")
        assert len(out) == 1
        assert out.iloc[0]["BAIRRO_REF"] == "CENTRO"
        assert out.iloc[0]["CLASSI_FIN"] == 1

    def test_base_and_gravidade_combine(self) -> None:
        df = pd.DataFrame(
            {
                "EVOLUCAO": [2, 2, 1],
                "UTI": [1, 2, 1],
            }
        )
        out = apply_global_filters(df, base="obitos", gravidade="uti")
        assert len(out) == 1

    def test_gravidade_and_sintomas_combine(self) -> None:
        df = pd.DataFrame(
            {
                "UTI": [1, 1, 2],
                "FEBRE": [1, 2, 1],
            }
        )
        out = apply_global_filters(df, gravidade="uti", sintomas=["febre"])
        assert len(out) == 1

    def test_all_four_filters_combine(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["CENTRO", "CENTRO", "CENTRO", "ABOLICAO"],
                "CLASSI_FIN": [1, 1, 3, 1],
                "UTI": [1, 2, 1, 1],
                "FEBRE": [1, 1, 1, 1],
            }
        )
        out = apply_global_filters(
            df,
            bairros=["CENTRO"],
            base="confirmados",
            gravidade="uti",
            sintomas=["febre"],
        )
        assert len(out) == 1
        assert out.iloc[0]["BAIRRO_REF"] == "CENTRO"

    def test_existing_bairro_filter_still_works_alone(self) -> None:
        """Regressão: filtros novos com default None não alteram o filtro de bairro."""
        df = pd.DataFrame({"BAIRRO_REF": ["CENTRO", "ABOLICAO"]})
        out = apply_global_filters(df, bairros=["CENTRO"])
        assert out["BAIRRO_REF"].tolist() == ["CENTRO"]
