"""Testes dos filtros de tipo/subtipo de influenza (classi) e agentes numericos.

Cobre:
- infer_influenza_type / normalize_influenza_values (surveillance.py)
- apply_surveillance_filters com classi/agents/years (core.py)
- validacao de classi (dependencies.py) e o comportamento via API
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from srag.api.core import apply_surveillance_filters
from srag.api.dependencies import _validate_classi
from srag.api.main import app
from srag.data.analytics.surveillance import (
    infer_influenza_type,
    normalize_influenza_values,
)

NAN = np.nan
COLS = (
    "CLASSI_FIN",
    "POS_PCRFLU",
    "POS_AN_FLU",
    "TP_FLU_PCR",
    "TP_FLU_AN",
    "PCR_FLUASU",
    "PCR_FLUBLI",
)


def make_df(**cols: list[Any]) -> pd.DataFrame:
    """DataFrame com todas as colunas de influenza; o que nao for passado vira NaN."""
    n = len(next(iter(cols.values())))
    data = {c: [NAN] * n for c in COLS}
    data.update(cols)
    return pd.DataFrame(data)


@pytest.fixture()
def casos() -> pd.DataFrame:
    """10 casos, um de cada categoria relevante (indice = posicao)."""
    return make_df(
        CLASSI_FIN=[1, 1, 1, 1, 1, 1, 1, 5, 2, NAN],
        POS_PCRFLU=[1, 1, 1, 1, 1, 1, NAN, 2, 2, NAN],
        TP_FLU_PCR=[1, 1, 1, 1, 2, 2, NAN, NAN, NAN, NAN],
        PCR_FLUASU=[1, 2, 3, NAN, NAN, NAN, NAN, NAN, NAN, NAN],
        PCR_FLUBLI=[NAN, NAN, NAN, NAN, 1, NAN, NAN, NAN, NAN, NAN],
    ).assign(DT_SIN_PRI=pd.to_datetime(["2024-03-10"] * 5 + ["2025-03-09"] * 5))


class TestInferInfluenzaType:
    def test_empty_dataframe(self) -> None:
        assert infer_influenza_type(pd.DataFrame()).empty

    def test_sem_influenza_vira_nao_se_aplica(self) -> None:
        df = make_df(CLASSI_FIN=[5, 4, NAN])
        assert infer_influenza_type(df).tolist() == ["11", "11", "11"]

    def test_influenza_nao_tipada(self) -> None:
        assert infer_influenza_type(make_df(CLASSI_FIN=[1])).tolist() == ["10"]

    def test_tipo_a_e_b_genericos_por_pcr_ou_antigeno(self) -> None:
        df = make_df(CLASSI_FIN=[1, 1, 1], TP_FLU_PCR=[1, NAN, 2], TP_FLU_AN=[NAN, 1, NAN])
        assert infer_influenza_type(df).tolist() == ["2", "2", "3"]

    @pytest.mark.parametrize(
        ("fluasu", "esperado"),
        [(1, "4"), (2, "5"), (3, "6"), (4, "7"), (5, "2"), (6, "2")],
    )
    def test_subtipos_de_a(self, fluasu: int, esperado: str) -> None:
        df = make_df(CLASSI_FIN=[1], POS_PCRFLU=[1], TP_FLU_PCR=[1], PCR_FLUASU=[fluasu])
        assert infer_influenza_type(df).tolist() == [esperado]

    @pytest.mark.parametrize(("flubli", "esperado"), [(1, "8"), (2, "9"), (3, "3")])
    def test_linhagens_de_b(self, flubli: int, esperado: str) -> None:
        df = make_df(CLASSI_FIN=[1], POS_PCRFLU=[1], TP_FLU_PCR=[2], PCR_FLUBLI=[flubli])
        assert infer_influenza_type(df).tolist() == [esperado]

    def test_teste_positivo_com_classi_fin_de_outro_agente(self) -> None:
        df = make_df(CLASSI_FIN=[5], POS_PCRFLU=[1], TP_FLU_PCR=[1])
        assert infer_influenza_type(df).tolist() == ["2"]

    def test_colunas_ausentes_nao_quebram(self) -> None:
        df = pd.DataFrame({"CLASSI_FIN": [1, 5]})
        assert infer_influenza_type(df).tolist() == ["10", "11"]

    def test_valores_como_texto_sao_convertidos(self) -> None:
        df = make_df(CLASSI_FIN=["1"], TP_FLU_PCR=["1"], PCR_FLUASU=["1"])
        assert infer_influenza_type(df).tolist() == ["4"]

    def test_preserva_indice(self) -> None:
        df = make_df(CLASSI_FIN=[1, 5]).set_index(pd.Index([10, 20]))
        assert infer_influenza_type(df).index.tolist() == [10, 20]


class TestNormalizeInfluenzaValues:
    def test_vazio(self) -> None:
        assert normalize_influenza_values(None) == set()
        assert normalize_influenza_values([]) == set()

    def test_tipo_a_inclui_subtipos(self) -> None:
        assert normalize_influenza_values(["2"]) == {"2", "4", "5", "6", "7"}

    def test_tipo_b_inclui_linhagens(self) -> None:
        assert normalize_influenza_values([3]) == {"3", "8", "9"}

    def test_todas_cobre_2_a_10_sem_o_11(self) -> None:
        assert normalize_influenza_values(["1"]) == {str(i) for i in range(2, 11)}

    def test_valor_folha_nao_expande(self) -> None:
        assert normalize_influenza_values(["4"]) == {"4"}

    def test_uniao_e_strip(self) -> None:
        assert normalize_influenza_values([" 4 ", "8"]) == {"4", "8"}


class TestApplySurveillanceFiltersClassi:
    def _idx(self, df: pd.DataFrame) -> list[int]:
        return df.index.tolist()

    def test_sem_classi_nao_filtra(self, casos: pd.DataFrame) -> None:
        assert len(apply_surveillance_filters(casos)) == len(casos)

    def test_subtipo_h1n1(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[4])) == [0]

    def test_subtipo_h3n2(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[5])) == [1]

    def test_tipo_a_inclui_subtipos_e_generico(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[2])) == [0, 1, 2, 3]

    def test_tipo_b_inclui_linhagens_e_generico(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[3])) == [4, 5]

    def test_linhagem_victoria(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[8])) == [4]

    def test_linhagem_sem_casos_retorna_vazio(self, casos: pd.DataFrame) -> None:
        assert apply_surveillance_filters(casos, classi=[9]).empty

    def test_influenza_nao_tipada(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[10])) == [6]

    def test_todas_retorna_somente_influenza(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[1])) == list(range(7))

    def test_nao_se_aplica_nao_filtra(self, casos: pd.DataFrame) -> None:
        assert len(apply_surveillance_filters(casos, classi=[11])) == len(casos)

    def test_11_misturado_com_outros_nao_filtra(self, casos: pd.DataFrame) -> None:
        assert len(apply_surveillance_filters(casos, classi=[4, 11])) == len(casos)

    def test_varios_tipos_fazem_uniao(self, casos: pd.DataFrame) -> None:
        assert self._idx(apply_surveillance_filters(casos, classi=[4, 8])) == [0, 4]

    def test_dataframe_vazio(self) -> None:
        df = make_df(CLASSI_FIN=[1]).iloc[0:0]
        assert apply_surveillance_filters(df, classi=[4]).empty

    def test_nao_altera_dataframe_original(self, casos: pd.DataFrame) -> None:
        antes = casos.copy()
        apply_surveillance_filters(casos, classi=[4])
        pd.testing.assert_frame_equal(casos, antes)


class TestApplySurveillanceFiltersAgentsNumericos:
    @pytest.mark.parametrize(("agente", "esperado"), [("1", 7), ("2", 1), ("5", 1)])
    def test_agente_numerico_filtra_por_classi_fin(
        self, casos: pd.DataFrame, agente: str, esperado: int
    ) -> None:
        assert len(apply_surveillance_filters(casos, agents=[agente])) == esperado

    def test_varios_agentes_numericos(self, casos: pd.DataFrame) -> None:
        assert len(apply_surveillance_filters(casos, agents=["2", "5"])) == 2

    def test_agente_por_nome_continua_funcionando(
        self, monkeypatch: pytest.MonkeyPatch, casos: pd.DataFrame
    ) -> None:
        monkeypatch.setattr(
            "srag.api.core.infer_etiologic_agent",
            lambda d: pd.Series(["Influenza"] * 7 + ["COVID-19"] * 3, index=d.index),
        )
        assert len(apply_surveillance_filters(casos, agents=["Influenza"])) == 7


class TestApplySurveillanceFiltersCombinados:
    def test_ano_agente_e_classi(self, casos: pd.DataFrame) -> None:
        out = apply_surveillance_filters(casos, years=[2024], agents=["1"], classi=[2])
        assert out.index.tolist() == [0, 1, 2, 3]

    def test_ano_que_exclui_o_subtipo(self, casos: pd.DataFrame) -> None:
        # H1N1 (indice 0) e de 2024, entao 2025 nao tem
        assert apply_surveillance_filters(casos, years=[2025], classi=[4]).empty

    def test_agente_covid_com_classi_de_influenza_zera(self, casos: pd.DataFrame) -> None:
        assert apply_surveillance_filters(casos, agents=["5"], classi=[4]).empty


class TestValidateClassi:
    def test_none_e_aceito(self) -> None:
        _validate_classi(None)

    def test_lista_vazia_e_aceita(self) -> None:
        _validate_classi([])

    @pytest.mark.parametrize("valor", [1, 2, 9, 10, 11])
    def test_valores_validos(self, valor: int) -> None:
        _validate_classi([valor])

    @pytest.mark.parametrize("valor", [0, 12, -1, 99])
    def test_valores_invalidos(self, valor: int) -> None:
        with pytest.raises(HTTPException) as exc:
            _validate_classi([valor])
        assert exc.value.status_code == 422
        assert str(valor) in exc.value.detail

    def test_um_invalido_na_lista_rejeita_tudo(self) -> None:
        with pytest.raises(HTTPException):
            _validate_classi([4, 12])


class TestClassiViaApi:
    """Chama /summary de verdade, com get_df substituido por um DataFrame pequeno
    (assim os testes nao dependem do banco)."""

    client = TestClient(app)

    @pytest.fixture(autouse=True)
    def _fake_df(self, monkeypatch: pytest.MonkeyPatch, casos: pd.DataFrame) -> None:
        df = casos.assign(UTI=1, EVOLUCAO=1, HOSPITAL=1)
        monkeypatch.setattr("srag.api.routers_core.get_df", lambda: df)

    def _total(self, query: str) -> int:
        resp = self.client.get(f"/summary?{query}")
        assert resp.status_code == 200, resp.text
        return resp.json()["total"]

    def test_sem_classi_retorna_todos(self) -> None:
        assert self._total("") == 10

    def test_subtipo_h1n1(self) -> None:
        assert self._total("classi=4") == 1

    def test_tipo_a_inclui_subtipos(self) -> None:
        assert self._total("classi=2") == 4

    def test_todas_so_influenza(self) -> None:
        assert self._total("classi=1") == 7

    def test_nao_se_aplica_nao_filtra(self) -> None:
        assert self._total("classi=11") == 10

    def test_varios_classi(self) -> None:
        assert self._total("classi=4&classi=8") == 2

    def test_agente_numerico_mais_classi(self) -> None:
        assert self._total("agents=1&classi=3") == 2

    def test_classi_sem_casos_retorna_zero(self) -> None:
        assert self._total("classi=9") == 0

    @pytest.mark.parametrize("valor", [0, 12])
    def test_classi_fora_do_intervalo_da_422(self, valor: int) -> None:
        assert self.client.get(f"/summary?classi={valor}").status_code == 422

    def test_classi_nao_numerico_da_422(self) -> None:
        assert self.client.get("/summary?classi=abc").status_code == 422