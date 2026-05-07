"""
Tests de non-régression pour le moteur heuristique de dimensionnement.

Vérifie que les cas concrets produisent des résultats réalistes
et cohérents avec les pratiques résidentielles françaises.
"""

from core.heuristics import (
    estimate_subscription_residential,
    classify_housing_profile,
    determine_phase_type,
    estimate_inter_caliber,
    heuristic_sizing_from_circuits,
    extract_housing_params_from_circuits,
)
from core.engine import generer_circuits_logement


# =========================================================================
# CAS 1 : 50 m² / 2 chambres / électroménager standard
# =========================================================================
def test_cas1_petit_logement_standard():
    """50 m², 2 chambres, standard => 9 ou 12 kVA monophasé"""
    result = estimate_subscription_residential(
        surface=50, nb_chambres=2,
    )
    print(f"[CAS 1] 50m²/2ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] in ("9 kVA", "12 kVA"), (
        f"Attendu 9 ou 12 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé", (
        f"Attendu monophasé, obtenu {result['phase']}"
    )
    assert result["profile"] == "t2"
    return result


# =========================================================================
# CAS 2 : 100 m² / chauffe-eau / cuisson
# =========================================================================
def test_cas2_maison_familiale():
    """100 m², chauffe-eau, cuisson => 12 kVA monophasé"""
    result = estimate_subscription_residential(
        surface=100, nb_chambres=3,
        presence_plaque=True,
        presence_chauffe_eau=True,
    )
    print(f"[CAS 2] 100m²/3ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] == "12 kVA", (
        f"Attendu 12 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé"
    assert result["profile"] == "t3_t4"
    return result


# =========================================================================
# CAS 3 : PAC importante
# =========================================================================
def test_cas3_maison_avec_pac():
    """Grande maison avec PAC => 12 kVA monophasé (ou 15 si grosse PAC)"""
    result = estimate_subscription_residential(
        surface=150, nb_chambres=4,
        has_pac=True,
    )
    print(f"[CAS 3] 150m²/4ch+PAC: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] in ("12 kVA", "15 kVA"), (
        f"Attendu 12 ou 15 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé"
    assert result["profile"] == "maison_pac"
    return result


# =========================================================================
# CAS 4 : borne VE + PAC
# =========================================================================
def test_cas4_maison_ve_et_pac():
    """Grande maison avec VE + PAC => 15-18 kVA, possible triphasé"""
    result = estimate_subscription_residential(
        surface=180, nb_chambres=5,
        has_pac=True,
        has_ve=True,
    )
    print(f"[CAS 4] 180m²/5ch+PAC+VE: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] in ("12 kVA", "15 kVA", "18 kVA"), (
        f"Attendu 12-18 kVA, obtenu {result['subscription']}"
    )
    assert result["profile"] == "maison_ve"
    return result


# =========================================================================
# CAS 5 : Studio
# =========================================================================
def test_cas5_studio():
    """Studio < 30m² => 6 kVA monophasé"""
    result = estimate_subscription_residential(
        surface=25, nb_chambres=1,
        presence_plaque=False,
        presence_chauffe_eau=False,
    )
    print(f"[CAS 5] 25m²/1ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] == "6 kVA"
    assert result["phase"] == "monophasé"
    assert result["profile"] == "studio"
    return result


# =========================================================================
# CAS 6 : Atelier
# =========================================================================
def test_cas6_atelier():
    """Maison avec atelier => triphasé recommandé"""
    result = estimate_subscription_residential(
        surface=120, nb_chambres=3,
        has_atelier=True,
    )
    print(f"[CAS 6] 120m²+atelier: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["phase"] == "triphasé"
    assert result["profile"] == "atelier"
    return result


# =========================================================================
# CAS 7 : Génération automatique (50m², 2ch) via engine
# =========================================================================
def test_cas7_generation_auto():
    """Génération circuits 50m²/2ch + dimensionnement heuristique"""
    circuits = generer_circuits_logement(50, 2)
    result = heuristic_sizing_from_circuits(circuits)
    print(f"[CAS 7] Auto 50m²/2ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    # Avec plaque+four+chauffe-eau, on attend 12 kVA
    assert result["subscription"] in ("9 kVA", "12 kVA")
    assert result["phase"] == "monophasé"
    return result


# =========================================================================
# CAS 8 : Extraction paramètres depuis circuits
# =========================================================================
def test_cas8_extraction_circuits():
    """Extraction des paramètres depuis circuits"""
    circuits = generer_circuits_logement(80, 3)
    params = extract_housing_params_from_circuits(circuits)
    print(f"[CAS 8] Paramètres extraits: {params}")
    assert params["presence_plaque"] is True
    assert params["presence_chauffe_eau"] is True
    assert params["has_pac"] is False
    assert params["has_ve"] is False
    return params


# =========================================================================
# CAS 9 : Calibre ID heuristique
# =========================================================================
def test_cas9_calibre_id():
    """Test des calibres ID par règles métier"""
    from core.models import Circuit

    # ID avec plaque => 63A
    circuits_plaque = [Circuit(nom="Plaque cuisson", type="specialise")]
    assert estimate_inter_caliber(circuits_plaque) == "63A"

    # ID avec petits circuits => 40A
    circuits_eclairage = [
        Circuit(nom="Éclairage séjour", type="eclairage"),
        Circuit(nom="Éclairage cuisine", type="eclairage"),
    ]
    assert estimate_inter_caliber(circuits_eclairage) == "40A"

    # ID avec PAC => 63A
    circuits_pac = [Circuit(nom="PAC", type="specialise")]
    assert estimate_inter_caliber(circuits_pac) == "63A"

    # ID avec VE => 63A
    circuits_ve = [Circuit(nom="Borne VE", type="specialise")]
    assert estimate_inter_caliber(circuits_ve) == "63A"

    # ID mixte (chauffe-eau + four + LV + LL) => 63A (heavy_count >= 3)
    circuits_lourds = [
        Circuit(nom="Chauffe-eau", type="specialise"),
        Circuit(nom="Four", type="specialise"),
        Circuit(nom="Lave-vaisselle", type="specialise"),
        Circuit(nom="Lave-linge", type="specialise"),
    ]
    assert estimate_inter_caliber(circuits_lourds) == "63A"

    print("[CAS 9] Tous les calibres ID sont corrects")
    return True


# =========================================================================
# CAS 10 : Non-régression — calibration de base
# =========================================================================
def test_cas10_profils_standards():
    """Vérifie que les profils standards n'ont jamais de résultats absurdes"""
    test_cases = [
        (25, 1, False, False, False, "6 kVA", "monophasé"),
        (50, 2, False, False, False, "9 kVA", "monophasé"),
        (80, 3, False, False, False, "12 kVA", "monophasé"),
        (120, 4, True, False, False, "15 kVA", "monophasé"),
        (120, 4, False, True, False, "12 kVA", "monophasé"),
        (120, 3, False, False, True, "15 kVA", "triphasé"),
    ]
    for surface, ch, pac, ve, atelier, exp_sub, exp_phase in test_cases:
        result = estimate_subscription_residential(surface, ch, pac, ve, atelier)
        print(f"  {surface}m²/{ch}ch PAC={pac} VE={ve} Atelier={atelier} => "
              f"{result['subscription']} {result['phase']} "
              f"(attendu: {exp_sub} {exp_phase})")
        assert result["subscription"] == exp_sub, (
            f"{surface}m²/{ch}ch: attendu {exp_sub}, obtenu {result['subscription']}"
        )
        assert result["phase"] == exp_phase, (
            f"{surface}m²/{ch}ch: attendu {exp_phase}, obtenu {result['phase']}"
        )
    print("[CAS 10] Tous les profils standards sont corrects")
    return True


# =========================================================================
# CAS 11 : Phase — monophasé par défaut
# =========================================================================
def test_cas11_monophase_defaut():
    """Vérifie que le monophasé est toujours le défaut sauf cas justifiés"""
    # Standard => mono
    assert determine_phase_type(50, 2) == "monophasé"
    assert determine_phase_type(80, 3) == "monophasé"
    assert determine_phase_type(120, 4, has_pac=True) == "monophasé"
    # Atelier => tri
    assert determine_phase_type(80, 2, has_atelier=True) == "triphasé"
    # VE + PAC grande maison => tri
    assert determine_phase_type(180, 5, has_pac=True, has_ve=True) == "triphasé"
    print("[CAS 11] Phase par défaut OK")
    return True


# =========================================================================
# CAS 12 : Non-régression — le cas aberrant 50m² ne donne plus 128A tri
# =========================================================================
def test_cas12_pas_aberrant():
    """Vérifie qu'un 50m²/2ch ne donne jamais un résultat aberrant"""
    result = estimate_subscription_residential(50, 2)
    assert result["subscription"] in ("6 kVA", "9 kVA", "12 kVA"), (
        f"50m²/2ch ne devrait pas dépasser 12 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé", (
        f"50m²/2ch doit être monophasé, obtenu {result['phase']}"
    )
    print(f"[CAS 12] 50m²/2ch => {result['subscription']} {result['phase']} (aberrant éliminé)")
    return True


# =========================================================================
# Exécution
# =========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("TESTS HEURISTIQUES DE DIMENSIONNEMENT")
    print("=" * 60)
    tests = [
        ("CAS 1 - Petit logement standard", test_cas1_petit_logement_standard),
        ("CAS 2 - Maison familiale", test_cas2_maison_familiale),
        ("CAS 3 - Maison avec PAC", test_cas3_maison_avec_pac),
        ("CAS 4 - Maison VE + PAC", test_cas4_maison_ve_et_pac),
        ("CAS 5 - Studio", test_cas5_studio),
        ("CAS 6 - Atelier", test_cas6_atelier),
        ("CAS 7 - Génération auto", test_cas7_generation_auto),
        ("CAS 8 - Extraction circuits", test_cas8_extraction_circuits),
        ("CAS 9 - Calibre ID", test_cas9_calibre_id),
        ("CAS 10 - Profils standards", test_cas10_profils_standards),
        ("CAS 11 - Monophasé défaut", test_cas11_monophase_defaut),
        ("CAS 12 - Pas aberrant", test_cas12_pas_aberrant),
    ]
    ok = 0
    for name, fn in tests:
        print(f"\n--- {name} ---")
        try:
            fn()
            print(f"  ✅ OK")
            ok += 1
        except AssertionError as e:
            print(f"  ❌ ÉCHEC: {e}")
        except Exception as e:
            print(f"  ❌ ERREUR: {e}")
    print(f"\n{'=' * 60}")
    print(f"Résultat : {ok}/{len(tests)} tests OK")
    print(f"{'=' * 60}")
