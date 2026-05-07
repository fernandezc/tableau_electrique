import pytest
from core.heuristics import determine_phase_type


class TestMonophaseParDefaut:
    def test_petit_logement(self):
        assert determine_phase_type(total_kva=6) == "monophasé"

    def test_maison_standard(self):
        assert determine_phase_type(total_kva=9) == "monophasé"
        assert determine_phase_type(total_kva=12) == "monophasé"
        assert determine_phase_type(total_kva=15) == "monophasé"

    def test_juste_en_dessous_du_seuil(self):
        assert determine_phase_type(total_kva=18) == "monophasé"


class TestTriphaseJustifie:
    def test_depasse_18_kva(self):
        assert determine_phase_type(total_kva=19) == "triphasé"
        assert determine_phase_type(total_kva=25) == "triphasé"

    def test_ve_22kw(self):
        assert determine_phase_type(total_kva=15, ve_type="22kw") == "triphasé"

    def test_pac_triphasee_grande_maison(self):
        assert determine_phase_type(
            total_kva=15, pac_type="tri", surface=120,
        ) == "triphasé"

    def test_atelier_lourd(self):
        assert determine_phase_type(
            total_kva=18, has_atelier=True, surface=200,
        ) == "triphasé"


class TestTriphaseNonJustifie:
    def test_ve_lent_seul(self):
        assert determine_phase_type(
            total_kva=12, has_ve=True, ve_type="lent",
        ) == "monophasé"

    def test_ve_standard_seul(self):
        assert determine_phase_type(
            total_kva=12, has_ve=True, ve_type="standard",
        ) == "monophasé"

    def test_ve_rapide_seul(self):
        assert determine_phase_type(
            total_kva=12, has_ve=True, ve_type="rapide",
        ) == "monophasé"

    def test_petit_atelier(self):
        assert determine_phase_type(
            total_kva=12, has_atelier=True, surface=70,
        ) == "monophasé"

    def test_pac_non_triphasee(self):
        assert determine_phase_type(
            total_kva=15, has_pac=True, pac_type="air_eau",
        ) == "monophasé"


class TestParametresDefaut:
    def test_defaut_monophase(self):
        assert determine_phase_type() == "monophasé"
