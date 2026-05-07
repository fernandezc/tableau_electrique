import pytest
from core.heuristics import classify_housing_profile


class TestStudio:
    def test_tres_petit(self):
        assert classify_housing_profile(20, 1) == "studio"

    def test_petit_avec_chambres(self):
        assert classify_housing_profile(30, 1) == "studio"

    def test_surface_limite(self):
        assert classify_housing_profile(35, 1) == "studio"


class TestT2:
    def test_standard(self):
        assert classify_housing_profile(50, 2) == "t2"

    def test_surface_max(self):
        assert classify_housing_profile(55, 2) == "t2"


class TestT3T4:
    def test_moyen(self):
        assert classify_housing_profile(70, 3) == "t3_t4"

    def test_grand(self):
        assert classify_housing_profile(90, 4) == "t3_t4"

    def test_surface_max(self):
        assert classify_housing_profile(100, 4) == "t3_t4"


class TestGrandeMaison:
    def test_tres_grande(self):
        assert classify_housing_profile(150, 5) == "grande_maison"


class TestAvecEquipements:
    def test_avec_pac(self):
        assert classify_housing_profile(100, 3, has_pac=True) == "maison_pac"

    def test_avec_ve(self):
        assert classify_housing_profile(80, 3, has_ve=True) == "maison_ve"

    def test_atelier_prioritaire(self):
        assert classify_housing_profile(
            100, 3, has_atelier=True,
        ) == "atelier"

    def test_atelier_petit_pas_prioritaire(self):
        assert classify_housing_profile(
            50, 2, has_atelier=True,
        ) == "t2"
