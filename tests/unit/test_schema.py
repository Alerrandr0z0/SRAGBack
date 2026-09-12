from srag.data.references import DEATH_OUTCOMES, MOSSORO_IBGE_CODES
from srag.data.schema import SragCase, is_mossoro_case


def test_is_mossoro_case_by_code() -> None:
    # Standard code
    case1 = SragCase(
        DT_NOTIFIC="20/05/2024",
        ID_MUNICIP="2408003",
        ID_MN_RESI="2408003",
        SEM_NOT=21,
        SG_UF_NOT="RN",
        ID_UNIDADE="UPA",
        DT_SIN_PRI="15/05/2024",
        SEM_PRI=20,
        NU_IDADE_N=30,
        TP_IDADE=3,
        CS_SEXO="M",
        CS_GESTANT=9,
        SG_UF="RN",
    )
    assert is_mossoro_case(case1) is True

    # Legacy code with .0
    case2 = SragCase(
        DT_NOTIFIC="20/05/2024",
        ID_MUNICIP="240800.0",
        ID_MN_RESI="NATAL",
        SEM_NOT=21,
        SG_UF_NOT="RN",
        ID_UNIDADE="UPA",
        DT_SIN_PRI="15/05/2024",
        SEM_PRI=20,
        NU_IDADE_N=30,
        TP_IDADE=3,
        CS_SEXO="M",
        CS_GESTANT=9,
        SG_UF="RN",
    )
    assert is_mossoro_case(case2) is True


def test_is_mossoro_case_by_name() -> None:
    case = SragCase(
        DT_NOTIFIC="20/05/2024",
        ID_MUNICIP="MOSSORO",
        ID_MN_RESI="NATAL",
        SEM_NOT=21,
        SG_UF_NOT="RN",
        ID_UNIDADE="UPA",
        DT_SIN_PRI="15/05/2024",
        SEM_PRI=20,
        NU_IDADE_N=30,
        TP_IDADE=3,
        CS_SEXO="M",
        CS_GESTANT=9,
        SG_UF="RN",
    )
    assert is_mossoro_case(case) is True


def test_is_not_mossoro_case() -> None:
    case = SragCase(
        DT_NOTIFIC="20/05/2024",
        ID_MUNICIP="2408102",  # Natal
        ID_MN_RESI="2408102",
        SEM_NOT=21,
        SG_UF_NOT="RN",
        ID_UNIDADE="UPA",
        DT_SIN_PRI="15/05/2024",
        SEM_PRI=20,
        NU_IDADE_N=30,
        TP_IDADE=3,
        CS_SEXO="M",
        CS_GESTANT=9,
        SG_UF="RN",
    )
    assert is_mossoro_case(case) is False


def test_project_death_override_keeps_code_2_only() -> None:
    assert {2} == DEATH_OUTCOMES


def test_is_mossoro_case_by_residence() -> None:
    # Resident in Mossoró but notified elsewhere
    case = SragCase(
        DT_NOTIFIC="20/05/2024",
        ID_MUNICIP="2408102",  # Natal
        ID_MN_RESI="2408003",  # Mossoró
        SEM_NOT=21,
        SG_UF_NOT="RN",
        ID_UNIDADE="UPA",
        DT_SIN_PRI="15/05/2024",
        SEM_PRI=20,
        NU_IDADE_N=30,
        TP_IDADE=3,
        CS_SEXO="M",
        CS_GESTANT=9,
        SG_UF="RN",
    )
    assert is_mossoro_case(case) is True


def test_is_mossoro_case_empty_values() -> None:
    case = SragCase(
        DT_NOTIFIC="20/05/2024",
        ID_MUNICIP="",
        ID_MN_RESI="",
        SEM_NOT=21,
        SG_UF_NOT="RN",
        ID_UNIDADE="UPA",
        DT_SIN_PRI="15/05/2024",
        SEM_PRI=20,
        NU_IDADE_N=30,
        TP_IDADE=3,
        CS_SEXO="M",
        CS_GESTANT=9,
        SG_UF="RN",
    )
    assert is_mossoro_case(case) is False


def test_mossoro_reference_codes_include_ibge_primary_code() -> None:
    assert MOSSORO_IBGE_CODES[0] == "2408003"
