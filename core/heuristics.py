"""
Moteur heuristique de dimensionnement résidentiel.

Remplace l'approche additive (somme des puissances x coefficients) par
des règles métier réalistes terrain, reproduisant la logique d'un
électricien résidentiel expérimenté.

Principes :
  - Dimensionnement par profil habitat (surface, chambres, équipements)
  - Monophasé par défaut, triphasé uniquement si justifié
  - Calibre ID par règles métier, pas par calcul puissance / 230
  - Justifications lisibles pour chaque décision
"""

from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Profils habitat
# ---------------------------------------------------------------------------

HOUSING_PROFILES = {
    "studio": {
        "label": "Studio / T1",
        "surface_max": 35,
        "chambres_max": 1,
        "subscription_base": 6,
        "description": "Petit logement : éclairage, prises, petit électroménager",
    },
    "t2": {
        "label": "T2",
        "surface_max": 55,
        "chambres_max": 2,
        "subscription_base": 9,
        "description": "Logement standard avec cuisson et électroménager",
    },
    "t3_t4": {
        "label": "T3 / T4 standard",
        "surface_max": 100,
        "chambres_max": 4,
        "subscription_base": 12,
        "description": "Logement familial avec équipements électriques complets",
    },
    "grande_maison": {
        "label": "Grande maison",
        "surface_max": 999,
        "chambres_max": 99,
        "subscription_base": 12,
        "description": "Grande maison, nombreux équipements et circuits",
    },
    "maison_pac": {
        "label": "Maison avec PAC",
        "surface_max": 200,
        "chambres_max": 6,
        "subscription_base": 12,
        "description": "Maison avec pompe à chaleur (chauffage + ECS)",
    },
    "maison_ve": {
        "label": "Maison avec borne VE",
        "surface_max": 999,
        "chambres_max": 99,
        "subscription_base": 12,
        "description": "Maison avec borne de recharge pour véhicule électrique",
    },
    "atelier": {
        "label": "Maison avec atelier",
        "surface_max": 999,
        "chambres_max": 99,
        "subscription_base": 15,
        "description": "Logement avec atelier équipé (machines-outils)",
    },
}


# ---------------------------------------------------------------------------
# Classification du profil logement
# ---------------------------------------------------------------------------

def classify_housing_profile(
    surface: float,
    nb_chambres: int,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
) -> str:
    """Classifie le profil du logement selon ses caractéristiques.

    Retourne la clé du profil parmi :
      studio, t2, t3_t4, grande_maison, maison_pac, maison_ve, atelier
    """
    if has_atelier and surface > 80:
        return "atelier"
    if has_ve:
        return "maison_ve"
    if has_pac:
        return "maison_pac"
    if surface <= 35 or nb_chambres <= 1:
        return "studio"
    if surface <= 55 and nb_chambres <= 2:
        return "t2"
    if surface <= 100 and nb_chambres <= 4:
        return "t3_t4"
    return "grande_maison"


# ---------------------------------------------------------------------------
# Estimation abonnement (kVA) — moteur principal heuristique
# ---------------------------------------------------------------------------

def estimate_subscription_residential(
    surface: float,
    nb_chambres: int,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
    chauffage_type: str = "electrique",
    presence_plaque: bool = True,
    presence_chauffe_eau: bool = True,
) -> Dict:
    """Estime l'abonnement conseillé selon des heuristiques terrain.

    Paramètres
    ----------
    surface : float
        Surface habitable en m².
    nb_chambres : int
        Nombre de chambres.
    has_pac : bool
        Présence d'une pompe à chaleur.
    has_ve : bool
        Présence d'une borne de recharge véhicule électrique.
    has_atelier : bool
        Présence d'un atelier équipé.
    chauffage_type : str
        "electrique" ou "autre".
    presence_plaque : bool
        Présence d'une plaque de cuisson.
    presence_chauffe_eau : bool
        Présence d'un chauffe-eau électrique.

    Retourne un dict structuré :
      - subscription : str (ex: "12 kVA")
      - phase : str ("monophasé" ou "triphasé")
      - profile : str (clé du profil)
      - profile_label : str (libellé lisible)
      - justification : str (explication métier)
      - calibre_edf : str (calibre disjoncteur EDF)
      - details : dict (paramètres d'entrée et calcul)
    """
    profile_key = classify_housing_profile(
        surface, nb_chambres, has_pac, has_ve, has_atelier
    )
    profile = HOUSING_PROFILES[profile_key]
    base_kva = profile["subscription_base"]

    boost = 0
    boost_reasons = []

    if has_pac:
        pac_boost = 6 if surface > 150 else 3
        boost += pac_boost
        boost_reasons.append(f"PAC (+{pac_boost} kVA)")

    if has_ve:
        boost += 6
        boost_reasons.append("borne VE (+6 kVA)")

    # Pas de boost atelier : le profil atelier a déjà une base à 15 kVA

    if has_atelier:
        boost_reasons.append("atelier équipé")

    if chauffage_type == "electrique" and surface > 50:
        if presence_chauffe_eau and presence_plaque:
            total_avant = base_kva + boost
            if total_avant < 12:
                boost_reasons.append("tout électrique")
            boost = max(boost, 12 - base_kva)

    total_kva = base_kva + boost

    # Plafonds de réalisme terrain

    # Petite surface (< 50 m²) : jamais plus de 12 kVA
    if surface <= 50:
        total_kva = min(total_kva, 12)

    # Surface moyenne (50-100 m²) : jamais plus de 15 kVA
    if 50 < surface <= 100:
        total_kva = min(total_kva, 15)

    # Maison VE sans PAC : 12 kVA max (gestion de charge supposée)
    if profile_key == "maison_ve" and not has_pac:
        total_kva = min(total_kva, 12)

    result_kva = _round_to_standard_subscription(total_kva)

    phase = determine_phase_type(
        surface, nb_chambres, has_pac, has_ve, has_atelier, result_kva
    )

    calibre_edf = _calibre_edf_from_kva(result_kva)

    justification = _build_subscription_justification(
        profile_key, profile, has_pac, has_ve, has_atelier,
        chauffage_type, result_kva, boost_reasons
    )

    return {
        "subscription": f"{result_kva} kVA",
        "phase": phase,
        "profile": profile_key,
        "profile_label": profile["label"],
        "justification": justification,
        "calibre_edf": calibre_edf,
        "details": {
            "surface": surface,
            "nb_chambres": nb_chambres,
            "has_pac": has_pac,
            "has_ve": has_ve,
            "has_atelier": has_atelier,
            "chauffage_type": chauffage_type,
            "presence_plaque": presence_plaque,
            "presence_chauffe_eau": presence_chauffe_eau,
            "profile": profile_key,
            "base_kva": base_kva,
            "boost": boost,
            "total_kva": total_kva,
            "result_kva": result_kva,
        },
    }


# ---------------------------------------------------------------------------
# Détermination phase
# ---------------------------------------------------------------------------

def determine_phase_type(
    surface: float,
    nb_chambres: int,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
    total_kva: int = 12,
) -> str:
    """Détermine le type d'alimentation.

    Monophasé par défaut pour tout logement standard.
    Triphasé uniquement si réellement justifié.
    """
    if has_atelier:
        return "triphasé"

    if total_kva > 15:
        return "triphasé"

    if has_ve and has_pac and surface > 150:
        return "triphasé"

    return "monophasé"


# ---------------------------------------------------------------------------
# Calibre interdifférentiel
# ---------------------------------------------------------------------------

def estimate_inter_caliber(circuits: list) -> str:
    """Détermine le calibre d'un interdifférentiel (40A ou 63A).

    Logique métier basée sur les équipements présents sur l'ID,
    pas sur un calcul de puissance.
    """
    noms = [c.nom.lower() for c in circuits]

    has_plaque = any("plaque" in n for n in noms)
    has_pac = any(("pac" in n or "pompe" in n) for n in noms)
    has_ve = any(("borne" in n or "irve" in n or "vehicule" in n) for n in noms)
    has_chauffe_eau = any("chauffe" in n for n in noms)
    has_four = any("four" in n for n in noms)
    has_lv = any("lave_vaisselle" in n for n in noms)
    has_ll = any("lave_linge" in n or "lave-linge" in n for n in noms)

    nb = len(circuits)

    if nb <= 3 and not any([has_plaque, has_pac, has_ve, has_chauffe_eau]):
        return "40A"

    if has_plaque:
        return "63A"

    if has_pac or has_ve:
        return "63A"

    heavy_count = sum([has_chauffe_eau, has_four, has_lv, has_ll])
    if heavy_count >= 3:
        return "63A"

    return "40A"


# ---------------------------------------------------------------------------
# Extraction paramètres depuis circuits
# ---------------------------------------------------------------------------

def extract_housing_params_from_circuits(circuits) -> Dict:
    """Extrait les paramètres logement depuis la liste de circuits.

    Utilisé en mode manuel (saisie libre par l'utilisateur)
    pour alimenter les heuristiques quand surface/chambres ne sont pas
    directement renseignés.
    """
    noms = [c.nom.lower() for c in circuits]

    has_pac = any("pac" in n or "pompe" in n for n in noms)
    has_ve = any("borne" in n or "irve" in n or "vehicule" in n for n in noms)
    has_atelier = any("atelier" in n for n in noms)
    presence_plaque = any("plaque" in n for n in noms)
    presence_chauffe_eau = any("chauffe" in n for n in noms)

    eclairage_count = sum(1 for c in circuits if c.type == "eclairage")
    estimated_surface = eclairage_count * 50
    if estimated_surface < 20:
        estimated_surface = 50

    chambre_count = sum(1 for n in noms if "chambre" in n)
    estimated_chambres = max(chambre_count, 2)

    return {
        "surface": estimated_surface,
        "nb_chambres": estimated_chambres,
        "has_pac": has_pac,
        "has_ve": has_ve,
        "has_atelier": has_atelier,
        "presence_plaque": presence_plaque,
        "presence_chauffe_eau": presence_chauffe_eau,
    }


def heuristic_sizing_from_circuits(circuits) -> Dict:
    """Point d'entrée : dimensionnement heuristique depuis une liste de circuits."""
    params = extract_housing_params_from_circuits(circuits)
    return estimate_subscription_residential(
        surface=params["surface"],
        nb_chambres=params["nb_chambres"],
        has_pac=params["has_pac"],
        has_ve=params["has_ve"],
        has_atelier=params["has_atelier"],
        presence_plaque=params["presence_plaque"],
        presence_chauffe_eau=params["presence_chauffe_eau"],
    )


def heuristic_sizing_from_params(
    surface: float,
    nb_chambres: int,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
) -> Dict:
    """Point d'entrée : dimensionnement heuristique depuis paramètres logement."""
    return estimate_subscription_residential(
        surface=surface,
        nb_chambres=nb_chambres,
        has_pac=has_pac,
        has_ve=has_ve,
        has_atelier=has_atelier,
    )


# ---------------------------------------------------------------------------
# Calcul de puissance (informatif, non décisionnel)
# ---------------------------------------------------------------------------

def compute_installed_power(circuits: list) -> Dict:
    """Calcule les puissances installées à titre informatif uniquement.

    Retourne un dict avec les valeurs théoriques et estimées.
    Ce résultat n'est pas utilisé pour les décisions de dimensionnement.
    """
    from core.rules import regles_circuit, SIMULTANEITY_FACTORS

    theoretical = 0
    estimated = 0
    details = []

    for c in circuits:
        rule = regles_circuit(c)
        p = rule["puissance"]
        theoretical += p

        nom = c.nom.lower()
        coeff = _get_simultaneity_factor(nom, c.type, SIMULTANEITY_FACTORS)
        estimated += p * coeff

        details.append({
            "nom": c.nom,
            "puissance": p,
            "coeff": coeff,
            "contribution": int(p * coeff),
        })

    return {
        "total_theoretical": int(theoretical),
        "total_estimated": int(estimated),
        "details": details,
    }


def _get_simultaneity_factor(nom: str, type_c: str, factors: Dict) -> float:
    """Coefficient de foisonnement pour un circuit donné."""
    for key, factor in factors.items():
        if key in nom:
            return factor
    if type_c == "prise":
        return factors.get("prises", 0.2)
    if type_c == "eclairage":
        return factors.get("eclairage", 0.8)
    return 0.5


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _round_to_standard_subscription(kva: int) -> int:
    """Arrondit aux valeurs d'abonnement EDF standard."""
    if kva <= 6:
        return 6
    elif kva <= 9:
        return 9
    elif kva <= 12:
        return 12
    elif kva <= 15:
        return 15
    else:
        return 18


def _calibre_edf_from_kva(kva: int) -> str:
    """Retourne le calibre du disjoncteur EDF."""
    mapping = {6: "30A", 9: "45A", 12: "60A", 15: "75A", 18: "90A"}
    return mapping.get(kva, "90A")


def _build_subscription_justification(
    profile_key: str,
    profile: Dict,
    has_pac: bool,
    has_ve: bool,
    has_atelier: bool,
    chauffage_type: str,
    result_kva: int,
    boost_reasons: list,
) -> str:
    """Construit une justification lisible pour l'abonnement conseillé."""
    phrases = [profile["description"]]

    if profile_key == "studio":
        phrases.append("abonnement minimum")

    if boost_reasons:
        phrases.append("équipements : " + ", ".join(boost_reasons))

    if chauffage_type == "electrique" and profile_key in ("t3_t4", "grande_maison"):
        phrases.append("chauffage électrique")

    phrases.append(f"abonnement conseillé {result_kva} kVA")

    if profile_key == "atelier":
        phrases.append("triphasé recommandé pour atelier")

    return " — ".join(phrases)
