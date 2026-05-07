import pytest
from core.heuristics import (
    estimate_subscription_residential,
    heuristic_sizing_from_circuits,
    estimate_inter_caliber,
)
from core.engine import generer_circuits_logement, compute_sizing_decision
from tests.helpers import (
    make_circuit, make_inter, make_tableau,
    small_apartment_circuits,
)


class TestPasAberrant:
    def test_petit_logement_pas_surdimensionne(self):
        """50m²/2ch ne doit jamais dépasser 12 kVA ni être triphasé"""
        result = estimate_subscription_residential(50, 2)
        assert int(result["subscription"].split()[0]) <= 12
        assert result["phase"] == "monophasé"

    def test_petit_logement_avec_options(self):
        """50m²/2ch avec PAC+VE+atelier ne doit pas dépasser 12 kVA ni être triphasé"""
        result = estimate_subscription_residential(
            50, 2,
            has_pac=True, has_ve=True, has_atelier=True,
            ve_type="standard", pac_type="air_eau",
        )
        assert int(result["subscription"].split()[0]) <= 12
        assert result["phase"] == "monophasé"

    def test_appartement_pas_128A(self):
        """Un appartement ne doit jamais donner 128A ou un calibre aberrant"""
        for surface in [25, 35, 50, 70]:
            for ch in [1, 2, 3]:
                result = estimate_subscription_residential(surface, ch)
                calibre = result.get("calibre_edf", "")
                if calibre:
                    val = int(calibre.replace("A", ""))
                    assert val <= 90, f"{surface}m²/{ch}ch donne {calibre}"

    def test_maison_standard_pas_triphase_sans_raison(self):
        """Maison standard 90m² sans équipement lourd ne doit pas être triphasé"""
        result = estimate_subscription_residential(90, 3)
        assert result["phase"] == "monophasé"


class TestGenerationAuto:
    def test_auto_petit_logement_monophase(self):
        circuits = generer_circuits_logement(50, 2)
        result = heuristic_sizing_from_circuits(circuits)
        assert result["phase"] == "monophasé"
        assert int(result["subscription"].split()[0]) <= 12

    def test_auto_grand_logement_coherent(self):
        circuits = generer_circuits_logement(120, 4)
        result = heuristic_sizing_from_circuits(circuits)
        # Le sizing depuis circuits est approximatif mais doit rester réaliste
        assert result["phase"] in ("monophasé", "triphasé")
        sub_kva = int(result["subscription"].split()[0])
        assert 6 <= sub_kva <= 18

    def test_sizing_decision_sans_metadata(self):
        circuits = generer_circuits_logement(50, 2)
        from core.engine import generer_tableau
        tableau = generer_tableau(circuits)
        decision = compute_sizing_decision(tableau)
        assert decision["phase"] == "monophasé"
        assert int(decision["subscription"].split()[0]) <= 12


class TestCalibreID:
    def test_plaque_toujours_63A(self):
        assert estimate_inter_caliber([
            make_circuit("Plaque cuisson", "specialise", 6.0),
        ]) == "63A"

    def test_petits_circuits_toujours_40A(self):
        assert estimate_inter_caliber([
            make_circuit("Éclairage 1", "eclairage"),
            make_circuit("Éclairage 2", "eclairage"),
        ]) == "40A"

    def test_jamais_calibre_invalide(self):
        for n in range(1, 6):
            circuits = [make_circuit(f"Circuit {i}", "eclairage") for i in range(n)]
            cal = estimate_inter_caliber(circuits)
            assert cal in ("40A", "63A"), f"Calibre invalide: {cal}"


class TestProfileClassification:
    def test_profile_toujours_defini(self):
        for surface in [20, 50, 90, 150]:
            for ch in [1, 2, 3, 4]:
                result = estimate_subscription_residential(surface, ch)
                assert result["profile"] is not None
                assert result["profile_label"] != ""


class TestDeterminisme:
    def test_resultat_deterministe(self):
        """Deux appels avec les mêmes paramètres donnent le même résultat"""
        params = dict(surface=90, nb_chambres=3, has_pac=True)
        r1 = estimate_subscription_residential(**params)
        r2 = estimate_subscription_residential(**params)
        assert r1["subscription"] == r2["subscription"]
        assert r1["phase"] == r2["phase"]
        assert r1["justification"] == r2["justification"]
