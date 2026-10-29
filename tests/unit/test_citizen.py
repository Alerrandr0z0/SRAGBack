"""Unit tests for the citizen computations (citizen.py)."""

from __future__ import annotations

import pandas as pd

from srag.data.analytics.citizen import (
    compute_animal_contact,
    compute_covid_dose_stage,
    compute_maternal_outcomes,
    compute_occupation_profile,
    compute_vaccine_manufacturers,
)


class TestMaternalOutcomes:
    def test_empty_dataframe(self) -> None:
        result = compute_maternal_outcomes(pd.DataFrame())
        assert result["groups"] == []
        assert result["gestantes_total"] == 0

    def test_groups_and_outcomes(self) -> None:
        df = pd.DataFrame(
            {
                "CS_SEXO": ["F", "F", "F", "F", "F", "M"],
                "CS_GESTANT": [1, 1, 3, 5, 1, 1],
                "PUERPERA": [2, 2, 2, 1, 1, 2],
                "EVOLUCAO": [1, 2, 1, 1, 1, 2],
                "UTI": [2, 1, 1, 2, 2, 1],
            }
        )
        result = compute_maternal_outcomes(df)
        groups = {g["group"]: g for g in result["groups"]}
        # Row 4 is puérpera (never also gestante); the man is ignored.
        assert groups["Gest. 1º tri"]["total"] == 2
        assert groups["Gest. 1º tri"]["cure"] == 1
        assert groups["Gest. 1º tri"]["death"] == 1
        assert groups["Gest. 3º tri"]["icu"] == 1
        assert groups["Puérpera"]["total"] == 2
        assert result["gestantes_total"] == 3
        assert result["puerperas_total"] == 2

    def test_missing_columns_do_not_break(self) -> None:
        assert compute_maternal_outcomes(pd.DataFrame({"CS_SEXO": ["F"]}))["groups"] == []


class TestOccupationProfile:
    def test_ranks_and_ignores_blanks(self) -> None:
        df = pd.DataFrame(
            {"PAC_DSCBO": ["pedreiro", "Pedreiro ", "professor", "", None, "999999", "IGNORADO"]}
        )
        result = compute_occupation_profile(df)
        assert result["items"][0] == {"label": "PEDREIRO", "count": 2}
        assert result["informed"] == 3
        assert result["total"] == 7

    def test_top_n(self) -> None:
        df = pd.DataFrame({"PAC_DSCBO": [f"JOB{i}" for i in range(20)]})
        assert len(compute_occupation_profile(df, top_n=5)["items"]) == 5

    def test_empty(self) -> None:
        assert compute_occupation_profile(pd.DataFrame())["items"] == []


class TestAnimalContact:
    def test_counts_and_ignored(self) -> None:
        df = pd.DataFrame({"AVE_SUINO": [1, 2, 2, 3, 9, None]})
        result = compute_animal_contact(df)
        counts = {i["label"]: i["count"] for i in result["items"]}
        assert counts == {"Aves ou suínos": 1, "Outros animais": 1, "Sem contato": 2}
        assert result["ignored"] == 2
        assert result["total"] == 6

    def test_empty(self) -> None:
        assert compute_animal_contact(pd.DataFrame())["items"] == []


class TestVaccineManufacturers:
    def test_last_dose_wins_and_names_are_merged(self) -> None:
        df = pd.DataFrame(
            {
                "FAB_COV1": ["Pfizer", "ASTRAZENECA/FIOCRUZ", "coronavac", None, "9"],
                "FAB_COV2": ["PFIZER BIONTECH", None, None, None, None],
                "FAB_COVRF": [None, "Pfizer", None, None, None],
            }
        )
        counts = {m["label"]: m["count"] for m in compute_vaccine_manufacturers(df)}
        assert counts == {"Pfizer/BioNTech": 2, "Butantan/Sinovac": 1}

    def test_without_columns(self) -> None:
        assert compute_vaccine_manufacturers(pd.DataFrame({"X": [1]})) == []


class TestCovidDoseStage:
    def test_furthest_stage(self) -> None:
        df = pd.DataFrame(
            {
                "VACINA_COV": [1, 1, 1, 2, 9],
                "DOSE_1_COV": ["2022-01-01", "2022-01-01", None, None, None],
                "DOSE_2_COV": [None, "2022-02-01", None, None, None],
                "DOSE_REF": [None, None, None, None, None],
            }
        )
        counts = {s["label"]: s["count"] for s in compute_covid_dose_stage(df)}
        assert counts["Só a 1ª dose"] == 1
        assert counts["Esquema completo"] == 1
        assert counts["Não vacinado"] == 1
        # Vaccinated=1 with no dose date, and 9, are both unknown.
        assert counts["Ignorado"] == 2

    def test_keeps_all_stages_in_order(self) -> None:
        stages = [s["label"] for s in compute_covid_dose_stage(pd.DataFrame({"VACINA_COV": [1]}))]
        assert stages[0] == "Não vacinado"
        assert stages[-1] == "Ignorado"
        assert len(stages) == 7
