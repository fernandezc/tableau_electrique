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
    _compute_surface_base,
)
from core.engine import generer_circuits_logement


# =========================================================================
# CAS 1 : 50 m² / 2 chambres / électroménager standard
# =========================================================================
def test_cas1_petit_logement_standard():
    """50 m², 2 chambres, standard => 9 kVA monophasé"""
    result = estimate_subscription_residential(
        surface=50, nb_chambres=2,
    )
    print(f"[CAS 1] 50m²/2ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] == "9 kVA", (
        f"Attendu 9 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé", (
        f"Attendu monophasé, obtenu {result['phase']}"
    )
    assert result["profile"] == "t2"
    return result


# =========================================================================
# CAS 2 : 90 m² / famille standard / chauffe-eau / cuisson
# =========================================================================
def test_cas2_maison_familiale():
    """90 m², chauffe-eau, cuisson => 12 kVA monophasé"""
    result = estimate_subscription_residential(
        surface=90, nb_chambres=3,
        presence_plaque=True,
        presence_chauffe_eau=True,
    )
    print(f"[CAS 2] 90m²/3ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] == "12 kVA", (
        f"Attendu 12 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé"
    return result


# =========================================================================
# CAS 3 : 120 m² / PAC air/eau
# =========================================================================
def test_cas3_maison_avec_pac():
    """120 m² avec PAC air/eau => 12 ou 15 kVA monophasé"""
    result = estimate_subscription_residential(
        surface=120, nb_chambres=4,
        has_pac=True, pac_type="air_eau",
    )
    print(f"[CAS 3] 120m²/4ch+PAC: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] in ("12 kVA", "15 kVA"), (
        f"Attendu 12 ou 15 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé"
    return result


# =========================================================================
# CAS 4 : VE lent => pas triphasé
# =========================================================================
def test_cas4_ve_lent_pas_triphase():
    """VE lent (3.7kW) seul => pas de triphasé automatique"""
    result = estimate_subscription_residential(
        surface=80, nb_chambres=3,
        has_ve=True, ve_type="lent",
    )
    print(f"[CAS 4] 80m²/3ch+VE lent: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["phase"] == "monophasé", (
        f"VE lent ne doit pas imposer triphasé, obtenu {result['phase']}"
    )
    return result


# =========================================================================
# CAS 5 : VE 22 kW => triphasé possible
# =========================================================================
def test_cas5_ve_22kw():
    """Borne VE 22 kW triphasée => triphasé possible"""
    result = estimate_subscription_residential(
        surface=120, nb_chambres=4,
        has_ve=True, ve_type="22kw",
    )
    print(f"[CAS 5] 120m²/4ch+VE22kW: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["phase"] == "triphasé", (
        f"VE 22kW devrait proposer triphasé, obtenu {result['phase']}"
    )
    return result


# =========================================================================
# CAS 6 : Studio
# =========================================================================
def test_cas6_studio():
    """Studio < 30m² => 6 kVA monophasé"""
    result = estimate_subscription_residential(
        surface=25, nb_chambres=1,
        presence_plaque=False,
        presence_chauffe_eau=False,
    )
    print(f"[CAS 6] 25m²/1ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["subscription"] == "6 kVA"
    assert result["phase"] == "monophasé"
    assert result["profile"] == "studio"
    return result


# =========================================================================
# CAS 7 : Atelier
# =========================================================================
def test_cas7_atelier():
    """Maison avec atelier (>150m²) => triphasé"""
    result = estimate_subscription_residential(
        surface=160, nb_chambres=3,
        has_atelier=True,
    )
    print(f"[CAS 7] 160m²+atelier: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["phase"] == "triphasé", (
        f"Atelier lourd devrait être triphasé, obtenu {result['phase']}"
    )
    assert result["profile"] == "atelier"
    return result


# =========================================================================
# CAS 8 : Petit atelier => monophasé (pas assez important)
# =========================================================================
def test_cas8_petit_atelier_mono():
    """Petit atelier (< 80m²) => monophasé"""
    result = estimate_subscription_residential(
        surface=70, nb_chambres=2,
        has_atelier=True,
    )
    print(f"[CAS 8] 70m²+atelier: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    assert result["phase"] == "monophasé", (
        f"Petit atelier reste monophasé, obtenu {result['phase']}"
    )
    return result


# =========================================================================
# CAS 9 : Calibre ID heuristique
# =========================================================================
def test_cas9_calibre_id():
    """Test des calibres ID par règles métier"""
    from core.models import Circuit

    assert estimate_inter_caliber([Circuit(nom="Plaque cuisson", type="specialise")]) == "63A"
    assert estimate_inter_caliber([
        Circuit(nom="Éclairage séjour", type="eclairage"),
        Circuit(nom="Éclairage cuisine", type="eclairage"),
    ]) == "40A"
    assert estimate_inter_caliber([Circuit(nom="PAC", type="specialise")]) == "63A"
    assert estimate_inter_caliber([Circuit(nom="Borne VE", type="specialise")]) == "63A"
    assert estimate_inter_caliber([
        Circuit(nom="Chauffe-eau", type="specialise"),
        Circuit(nom="Four", type="specialise"),
        Circuit(nom="Lave-vaisselle", type="specialise"),
        Circuit(nom="Lave-linge", type="specialise"),
    ]) == "63A"

    print("[CAS 9] Tous les calibres ID sont corrects")
    return True


# =========================================================================
# CAS 10 : Génération automatique
# =========================================================================
def test_cas10_generation_auto():
    """Génération circuits + dimensionnement heuristique"""
    circuits = generer_circuits_logement(50, 2)
    result = heuristic_sizing_from_circuits(circuits)
    print(f"[CAS 10] Auto 50m²/2ch: {result['subscription']} {result['phase']}")
    print(f"  Profil: {result['profile_label']}")
    print(f"  Raison: {result['justification']}")
    # L'estimation depuis circuits est approximative
    assert result["phase"] == "monophasé"
    return result


# =========================================================================
# CAS 11 : Non-régression — cas concrets terrain
# =========================================================================
def test_cas11_profils_terrain():
    """Vérifie que tous les profils terrain donnent des résultats réalistes"""
    tests = [
        # (surface, ch, pac, ve, atelier, ve_type, pac_type, plaque, sub, phase)
        (25, 1, False, False, False, "standard", "air_eau", False, "6 kVA", "monophasé"),
        (50, 2, False, False, False, "standard", "air_eau", True, "9 kVA", "monophasé"),
        (70, 2, False, False, False, "standard", "air_eau", True, "12 kVA", "monophasé"),
        (90, 3, False, False, False, "standard", "air_eau", True, "12 kVA", "monophasé"),
        (120, 4, True, False, False, "standard", "air_eau", True, "15 kVA", "monophasé"),
        (120, 4, False, True, False, "lent", "air_eau", True, "15 kVA", "monophasé"),
        (120, 4, False, True, False, "22kw", "air_eau", True, "18 kVA", "triphasé"),
        (70, 2, False, False, True, "standard", "air_eau", True, "12 kVA", "monophasé"),
        (160, 3, False, False, True, "standard", "air_eau", True, "18 kVA", "triphasé"),
        (50, 2, True, True, False, "standard", "air_eau", True, "12 kVA", "monophasé"),
    ]
    for surface, ch, pac, ve, atelier, ve_type, pac_type, plaque, exp_sub, exp_phase in tests:
        result = estimate_subscription_residential(
            surface, ch,
            has_pac=pac, has_ve=ve, has_atelier=atelier,
            ve_type=ve_type, pac_type=pac_type,
            presence_plaque=plaque,
        )
        msg = (f"{surface}m²/{ch}ch PAC={pac} VE={ve}({ve_type}) atelier={atelier}: "
               f"attendu {exp_sub} {exp_phase}, obtenu {result['subscription']} {result['phase']}")
        assert result["subscription"] == exp_sub, msg
        assert result["phase"] == exp_phase, msg
        print(f"  ✅ {surface}m²/{ch}ch => {result['subscription']} {result['phase']}")
    print("[CAS 11] Tous les profils terrain sont corrects")
    return True


# =========================================================================
# CAS 12 : Phase — monophasé par défaut
# =========================================================================
def test_cas12_monophase_defaut():
    """Vérifie que le monophasé est le défaut sauf cas exceptionnels"""
    assert determine_phase_type(total_kva=9) == "monophasé"
    assert determine_phase_type(total_kva=12) == "monophasé"
    assert determine_phase_type(total_kva=15) == "monophasé"
    assert determine_phase_type(total_kva=18) == "monophasé"  # 18 n'est pas > 18
    assert determine_phase_type(total_kva=19) == "triphasé"   # > 18 => tri
    assert determine_phase_type(total_kva=15, ve_type="22kw") == "triphasé"
    assert determine_phase_type(total_kva=15, pac_type="tri", surface=120) == "triphasé"
    assert determine_phase_type(total_kva=18, has_atelier=True, surface=200) == "triphasé"
    print("[CAS 12] Phase par défaut OK")
    return True


# =========================================================================
# CAS 13 : Base progressive
# =========================================================================
def test_cas13_base_progressive():
    """Vérifie la progressivité de la base"""
    assert _compute_surface_base(25) == 6
    assert _compute_surface_base(30) == 6
    assert _compute_surface_base(35) == 6
    assert _compute_surface_base(50) == 7
    assert _compute_surface_base(60) == 8
    assert _compute_surface_base(75) == 9
    assert _compute_surface_base(90) == 10
    assert _compute_surface_base(105) == 11
    assert _compute_surface_base(120) == 12
    assert _compute_surface_base(200) == 12  # cap
    print("[CAS 13] Base progressive OK")
    return True


# =========================================================================
# CAS 14 : Non-régression — pas de surdimensionnement aberrant
# =========================================================================
def test_cas14_pas_aberrant():
    """Vérifie qu'un 50m²/2ch ne donne jamais un résultat aberrant"""
    result = estimate_subscription_residential(50, 2)
    assert result["subscription"] in ("6 kVA", "9 kVA", "12 kVA"), (
        f"50m²/2ch ne devrait pas dépasser 12 kVA, obtenu {result['subscription']}"
    )
    assert result["phase"] == "monophasé"
    print(f"[CAS 14] 50m²/2ch => {result['subscription']} {result['phase']} (aberrant éliminé)")
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
        ("CAS 4 - VE lent pas triphasé", test_cas4_ve_lent_pas_triphase),
        ("CAS 5 - VE 22kW triphasé", test_cas5_ve_22kw),
        ("CAS 6 - Studio", test_cas6_studio),
        ("CAS 7 - Atelier lourd", test_cas7_atelier),
        ("CAS 8 - Petit atelier mono", test_cas8_petit_atelier_mono),
        ("CAS 9 - Calibre ID", test_cas9_calibre_id),
        ("CAS 10 - Génération auto", test_cas10_generation_auto),
        ("CAS 11 - Profils terrain", test_cas11_profils_terrain),
        ("CAS 12 - Monophasé défaut", test_cas12_monophase_defaut),
        ("CAS 13 - Base progressive", test_cas13_base_progressive),
        ("CAS 14 - Pas aberrant", test_cas14_pas_aberrant),
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
            print(f"  ❌ ERREUR: {type(e).__name__}: {e}")
    print(f"\n{'=' * 60}")
    print(f"Résultat : {ok}/{len(tests)} tests OK")
    print(f"{'=' * 60}")
