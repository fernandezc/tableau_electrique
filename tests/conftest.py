import pytest
from tests.helpers import (
    small_apartment_circuits,
    standard_house_circuits,
    house_with_pac_circuits,
    house_with_ev_circuits,
    house_with_atelier_circuits,
    make_circuit,
    make_inter,
    make_tableau,
)


@pytest.fixture
def small_apartment():
    return small_apartment_circuits()


@pytest.fixture
def standard_house():
    return standard_house_circuits()


@pytest.fixture
def house_with_pac():
    return house_with_pac_circuits()


@pytest.fixture
def house_with_ev():
    return house_with_ev_circuits()


@pytest.fixture
def house_with_atelier():
    return house_with_atelier_circuits()


@pytest.fixture
def plaque_circuit():
    return make_circuit("Plaque cuisson", "specialise", 6.0, puissance=7000)


@pytest.fixture
def ev_circuit():
    return make_circuit("Borne VE", "specialise", 6.0, puissance=7400)


@pytest.fixture
def tableau_standard(standard_house):
    from core.engine import generer_tableau
    return generer_tableau(standard_house)
