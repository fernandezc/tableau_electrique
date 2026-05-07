import pytest
from core.heuristics import estimate_inter_caliber
from tests.helpers import make_circuit


class TestCalibrePlaque:
    def test_plaque_seule(self):
        assert estimate_inter_caliber([
            make_circuit("Plaque cuisson", "specialise", 6.0),
        ]) == "63A"

    def test_plaque_avec_eclairage(self):
        assert estimate_inter_caliber([
            make_circuit("Plaque cuisson", "specialise"),
            make_circuit("Éclairage cuisine", "eclairage"),
        ]) == "63A"


class TestCalibrePAC:
    def test_pac_seule(self):
        assert estimate_inter_caliber([
            make_circuit("PAC air/eau", "specialise"),
        ]) == "63A"

    def test_pompe_chaleur(self):
        assert estimate_inter_caliber([
            make_circuit("Pompe à chaleur", "specialise"),
        ]) == "63A"


class TestCalibreVE:
    def test_borne_seule(self):
        assert estimate_inter_caliber([
            make_circuit("Borne VE", "specialise"),
        ]) == "63A"

    def test_irve_seule(self):
        assert estimate_inter_caliber([
            make_circuit("IRVE 7kW", "specialise"),
        ]) == "63A"


class TestCalibre40A:
    def test_eclairages_seuls(self):
        assert estimate_inter_caliber([
            make_circuit("Éclairage séjour", "eclairage"),
            make_circuit("Éclairage cuisine", "eclairage"),
        ]) == "40A"

    def test_prises_seules(self):
        assert estimate_inter_caliber([
            make_circuit("Séjour prises", "prise"),
            make_circuit("Cuisine prises", "prise"),
        ]) == "40A"

    def test_trois_petits_circuits(self):
        assert estimate_inter_caliber([
            make_circuit("Éclairage 1", "eclairage"),
            make_circuit("Éclairage 2", "eclairage"),
            make_circuit("Prise salon", "prise"),
        ]) == "40A"


class TestCalibreLourds:
    def test_trois_equipements_lourds(self):
        assert estimate_inter_caliber([
            make_circuit("Chauffe-eau", "specialise"),
            make_circuit("Four", "specialise"),
            make_circuit("Lave-vaisselle", "specialise"),
            make_circuit("Lave-linge", "specialise"),
        ]) == "63A"

    def test_chauffe_eau_et_four(self):
        assert estimate_inter_caliber([
            make_circuit("Chauffe-eau", "specialise"),
            make_circuit("Four", "specialise"),
        ]) == "40A"
