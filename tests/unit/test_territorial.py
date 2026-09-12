import numpy as np
import pandas as pd

from srag.data.analytics.territorial import (
    compute_territory_distribution,
    compute_zone_distribution,
)


class TestTerritoryDistribution:
    def test_status_counts_are_aggregated(self) -> None:
        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["Centro", "Centro", "Centro", "Cidade Nova", "Cidade Nova"],
                "EVOLUCAO": [1, 2, 3, 1, 2],
            }
        )
        res = compute_territory_distribution(df, min_cases=1)
        rows = {row["bairro"]: row for _, row in res.iterrows()}

        assert rows["Centro"]["count"] == 3
        assert rows["Centro"]["curados"] == 1
        assert rows["Centro"]["obitos"] == 1
        assert rows["Centro"]["ignorados"] == 1

    def test_min_cases_boundary(self) -> None:
        df = pd.DataFrame(
            {"BAIRRO_REF": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "C", "C", "C", "D", "D"]}
        )
        res = compute_territory_distribution(df, min_cases=5)
        counts = dict(zip(res["bairro"], res["count"], strict=False))
        assert "A" in counts
        assert counts["A"] == 5
        assert "B" not in counts

    def test_min_cases_exact_4(self) -> None:
        df = pd.DataFrame({"BAIRRO_REF": ["A", "A", "A", "A", "B", "B", "B"]})
        res = compute_territory_distribution(df, min_cases=4)
        assert "A" in res["bairro"].values
        assert "B" not in res["bairro"].values

    def test_nao_informado_fill(self) -> None:
        df = pd.DataFrame({"BAIRRO_REF": [np.nan, np.nan, np.nan, "A", "A"]})
        res = compute_territory_distribution(df, min_cases=3)
        bairros = set(res["bairro"])
        assert "NAO INFORMADO" in bairros

    def test_empty_df(self) -> None:
        assert compute_territory_distribution(pd.DataFrame()).empty

    def test_missing_column(self) -> None:
        assert compute_territory_distribution(pd.DataFrame({"OUTRA": [1]})).empty


class TestZoneDistribution:
    def test_exact_zone_counts(self) -> None:
        df = pd.DataFrame({"ZONA": ["Urbana", "Urbana", "Rural", "Periurbana", np.nan]})
        res = compute_zone_distribution(df)
        assert len(res) == 4
        zonas = dict(zip(res["zona"], res["count"], strict=False))
        assert zonas.get("Urbana") == 2

    def test_nan_filled_nao_informado(self) -> None:
        df = pd.DataFrame({"ZONA": [np.nan, np.nan, "Urbana"]})
        res = compute_zone_distribution(df)
        zonas = set(res["zona"])
        assert "Nao informado" in zonas

    def test_empty_df(self) -> None:
        assert compute_zone_distribution(pd.DataFrame()).empty

    def test_missing_column(self) -> None:
        assert compute_zone_distribution(pd.DataFrame({"OUTRA": [1]})).empty




class TestNormalizeTerritoryLabels:
    def test_official_rural_zone_becomes_urban(self) -> None:
        import pandas as pd

        from srag.data.analytics.territorial import normalize_territory_labels

        df = pd.DataFrame(
            {"BAIRRO_REF": ["CENTRO", "SITIO X", "ZONA RURAL"], "ZONA": ["Rural", "Rural", "Rural"]}
        )
        out = normalize_territory_labels(df)
        assert out["BAIRRO_REF"].tolist() == [
            "CENTRO",
            "AREA RURAL DE MOSSORO",
            "AREA RURAL DE MOSSORO",
        ]
        assert out["ZONA"].tolist() == ["Urbana", "Rural", "Rural"]

    def test_sum_is_conserved(self) -> None:
        import pandas as pd

        from srag.data.analytics.territorial import normalize_territory_labels

        df = pd.DataFrame(
            {
                "BAIRRO_REF": ["CENTRO", "MAISA", "SITIO X", "ZONA RURAL"],
                "ZONA": ["Urbana", "Urbana", "Rural", "Rural"],
            }
        )
        assert len(normalize_territory_labels(df)) == 4


class TestMissingBairroRow:
    def test_missing_bairro_stays_nao_informado(self) -> None:
        import pandas as pd

        from srag.data.analytics.territorial import normalize_territory_labels

        df = pd.DataFrame(
            {"BAIRRO_REF": [None, "", "CENTRO"], "ZONA": ["Urbana", "Rural", "Urbana"]}
        )
        out = normalize_territory_labels(df)
        assert out["BAIRRO_REF"].tolist() == ["NAO INFORMADO", "NAO INFORMADO", "CENTRO"]
