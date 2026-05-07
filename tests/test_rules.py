import pytest
from core.models import Circuit
from core.rules import (
    regles_circuit,
    validate_section_vs_breaker,
    validate_inter_type,
    type_inter_diff,
    check_circuit_omissions,
    verifier_section_circuit,
    verifier_dj_circuit,
    SECTION_MAX_DJ,
)
from tests.helpers import make_circuit


class TestReglesCircuit:
    def test_prise_1_5(self):
        r = regles_circuit(make_circuit("Test", "prise", 1.5))
        assert r["disj"] == 16
        assert r["max"] == 8
        assert r["puissance"] == 2000

    def test_prise_2_5(self):
        r = regles_circuit(make_circuit("Test", "prise", 2.5))
        assert r["disj"] == 20
        assert r["max"] == 12
        assert r["puissance"] == 3000

    def test_eclairage(self):
        r = regles_circuit(make_circuit("Test", "eclairage", 1.5))
        assert r["disj"] == 16
        assert r["puissance"] == 1000

    def test_plaque_cuisson(self):
        r = regles_circuit(make_circuit("Plaque cuisson", "specialise", 6.0))
        assert r["disj"] == 32
        assert r["puissance"] == 7000
        assert "Type A" in r["label"]

    def test_lave_linge(self):
        r = regles_circuit(make_circuit("Lave-linge", "specialise", 2.5))
        assert r["disj"] == 20
        assert r["puissance"] == 2500

    def test_borne_ve(self):
        r = regles_circuit(make_circuit("Borne VE", "specialise", 6.0))
        assert r["disj"] == 32
        assert r["puissance"] == 7400

    def test_dict_input(self):
        r = regles_circuit({"nom": "Test", "type": "prise", "section": 2.5})
        assert r["disj"] == 20


class TestSectionVersDJ:
    def test_section_compatible(self):
        for section, max_dj in SECTION_MAX_DJ.items():
            c = make_circuit("Test", "prise", section)
            alertes = validate_section_vs_breaker(c)
            assert len(alertes) == 0, f"section {section}mm² max {max_dj}A devrait être OK"

    @pytest.mark.parametrize("section,puiss,attendu", [
        (1.5, 7000, 32),
        (2.5, 7000, 32),
    ])
    def test_section_trop_faible_pour_plaque(self, section, puiss, attendu):
        c = make_circuit("Plaque cuisson", "specialise", section, puiss)
        alertes = validate_section_vs_breaker(c)
        if section < 6.0:
            assert any("Section" in a.get("message", "") for a in alertes)


class TestTypeInterDiff:
    @pytest.mark.parametrize("nom,attendu", [
        ("Plaque cuisson", "A"),
        ("Lave-linge", "A"),
        ("Lave-linge 2", "A"),
        ("IRVE 7kW", "A"),
        ("Borne VE", "A"),
        ("Four", "AC"),
        ("Lave-vaisselle", "AC"),
        ("Éclairage séjour", "AC"),
        ("Prise cuisine", "AC"),
    ])
    def test_type_requis(self, nom, attendu):
        c = make_circuit(nom, "specialise" if attendu else "prise")
        assert type_inter_diff(c) == attendu

    def test_type_a_mandatory(self):
        for nom in ["plaque", "lave_linge", "lave-linge", "irve", "borne"]:
            c = make_circuit(nom, "specialise")
            assert validate_inter_type(c) == "A", f"{nom} devrait être Type A"


class TestVerifications:
    def test_section_plaque_insuffisante(self):
        c = make_circuit("Plaque cuisson", "specialise", 4.0, 7000)
        alertes = verifier_section_circuit(c)
        assert any("❌" in a for a in alertes)

    def test_section_plaque_correcte(self):
        c = make_circuit("Plaque cuisson", "specialise", 6.0, 7000)
        alertes = verifier_section_circuit(c)
        assert not any("❌" in a for a in alertes)

    def test_dj_surdimensionne(self):
        c = make_circuit("Éclairage séjour", "eclairage", 1.5, dj_existant=20)
        alertes = verifier_dj_circuit(c)
        assert any("⚠️" in a for a in alertes)

    def test_dj_conforme(self):
        c = make_circuit("Éclairage séjour", "eclairage", 1.5, dj_existant=16)
        alertes = verifier_dj_circuit(c)
        assert len(alertes) == 0


class TestOmissions:
    def test_aucune_omission_maison_standard(self, standard_house):
        alertes = [a for a in check_circuit_omissions(standard_house) if a["niveau"] == "warning"]
        assert len(alertes) == 0

    def test_omission_plaque(self):
        circuits = [make_circuit("Éclairage", "eclairage")]
        alertes = check_circuit_omissions(circuits)
        assert any("plaque" in a["message"] for a in alertes)

    def test_omission_vmc(self):
        circuits = [make_circuit("Plaque cuisson", "specialise", 6.0)]
        alertes = check_circuit_omissions(circuits)
        assert any("VMC" in a["message"] for a in alertes)


class TestModulesDIN:
    def test_module_widths_constantes(self):
        from core.rules import MODULE_WIDTHS
        assert MODULE_WIDTHS["DJ_1P"] == 1
        assert MODULE_WIDTHS["ID_TYPE_A"] == 2
