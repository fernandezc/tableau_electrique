"""
Moteur heuristique de dimensionnement résidentiel.

Remplace l'approche additive (somme des puissances x coefficients) par
des règles métier réalistes terrain, avec une logique progressive
et nuancée adaptée aux pratiques résidentielles françaises.

Principes :
  - Dimensionnement progressif : base surface + ajustements modulaires
  - Chaque équipement a un poids différencié (petits bonus cumulés)
  - Monophasé par défaut, triphasé très conservateur
  - Calibre ID par règles métier, pas par calcul puissance / 230
  - Justifications lisibles pour chaque décision
"""

import re
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Profils habitat (pour affichage et classification, pas pour le calcul)
# ---------------------------------------------------------------------------

HOUSING_PROFILES = {
    "studio": {
        "label": "Studio / T1",
        "surface_max": 35,
        "chambres_max": 1,
        "description": "Petit logement : éclairage, prises, petit électroménager",
    },
    "t2": {
        "label": "T2",
        "surface_max": 55,
        "chambres_max": 2,
        "description": "Logement standard avec cuisson et électroménager",
    },
    "t3_t4": {
        "label": "T3 / T4 standard",
        "surface_max": 100,
        "chambres_max": 4,
        "description": "Logement familial avec équipements électriques complets",
    },
    "grande_maison": {
        "label": "Grande maison",
        "surface_max": 999,
        "chambres_max": 99,
        "description": "Grande maison, nombreux équipements et circuits",
    },
    "maison_pac": {
        "label": "Maison avec PAC",
        "surface_max": 200,
        "chambres_max": 6,
        "description": "Maison avec pompe à chaleur (chauffage + ECS)",
    },
    "maison_ve": {
        "label": "Maison avec borne VE",
        "surface_max": 999,
        "chambres_max": 99,
        "description": "Maison avec borne de recharge pour véhicule électrique",
    },
    "atelier": {
        "label": "Maison avec atelier",
        "surface_max": 999,
        "chambres_max": 99,
        "description": "Logement avec atelier équipé (machines-outils)",
    },
}


# ---------------------------------------------------------------------------
# Classification du profil (pour affichage uniquement)
# ---------------------------------------------------------------------------

def classify_housing_profile(
    surface: float,
    nb_chambres: int,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
) -> str:
    """Classifie le profil du logement pour l'affichage."""
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
# Estimation abonnement (kVA) — logique progressive
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
    ve_type: str = "standard",
    pac_type: str = "air_eau",
    chauffage_principal: Optional[bool] = None,
) -> Dict:
    """Estime l'abonnement conseillé selon une logique progressive.

    Le calcul suit le principe :
      base (progressive selon surface)
      + petit bonus équipements (poids différencié)
      + chauffage / PAC
      + VE (selon type)
      + atelier (selon importance)
      = total → arrondi à l'abonnement EDF standard

    Paramètres
    ----------
    surface : float — Surface habitable en m².
    nb_chambres : int — Nombre de chambres.
    has_pac : bool — Présence d'une pompe à chaleur.
    has_ve : bool — Présence d'une borne de recharge VE.
    has_atelier : bool — Présence d'un atelier.
    chauffage_type : str — "electrique" ou "autre".
    presence_plaque : bool — Présence plaque cuisson.
    presence_chauffe_eau : bool — Présence chauffe-eau électrique.
    ve_type : str — Type de VE : "lent" (3.7kW), "standard" (7kW),
                    "rapide" (11-14kW), "22kw" (triphasé).
    pac_type : str — Type PAC : "air_air", "air_eau", "tri".
    chauffage_principal : bool ou None — Chauffage électrique principal.
                          None = auto (True si électrique sans PAC).

    Retourne un dict structuré avec abonnement, phase, profil, justification.
    """
    if chauffage_principal is None:
        chauffage_principal = (chauffage_type == "electrique" and not has_pac)

    profile_key = classify_housing_profile(
        surface, nb_chambres, has_pac, has_ve, has_atelier
    )
    profile = HOUSING_PROFILES[profile_key]

    # Étape 1 : base progressive selon la surface
    base = _compute_surface_base(surface)

    # Étape 2 : ajustements modulaires (petits bonus cumulés)
    parts = []
    total = base

    # -- Équipements standard (poids léger) --
    if presence_plaque:
        total += 1
        parts.append("cuisson électrique")

    # -- Chauffage --
    if has_pac:
        # PAC remplace le chauffage électrique
        if pac_type == "air_air":
            total += 2
            parts.append("PAC air/air")
        elif pac_type == "air_eau":
            total += 2
            parts.append("PAC air/eau")
        elif pac_type == "tri":
            total += 3
            parts.append("PAC triphasée")
    elif chauffage_principal:
        if surface > 100:
            total += 2
            parts.append("chauffage électrique principal")
        elif surface >= 70:
            total += 1
            parts.append("chauffage électrique")

    # -- Véhicule électrique (poids selon type) --
    if has_ve:
        ve_mod, ve_label = _ve_modifier(ve_type)
        total += ve_mod
        parts.append(ve_label)

    # -- Atelier --
    if has_atelier:
        at_mod, at_label = _atelier_modifier(surface)
        total += at_mod
        parts.append(at_label)

    # Étape 3 : plafonds de réalisme
    if surface <= 50:
        total = min(total, 12)
    elif surface <= 100:
        total = min(total, 15)

    # Étape 4 : arrondi à l'abonnement standard
    result_kva = _round_to_standard_subscription(total)

    # Étape 5 : phase (très conservateur)
    phase = determine_phase_type(
        total_kva=total,
        has_pac=has_pac,
        has_ve=has_ve,
        has_atelier=has_atelier,
        pac_type=pac_type,
        ve_type=ve_type,
        surface=surface,
    )

    # Étape 6 : justification
    justification = _build_justification(
        profile, parts, chauffage_type, chauffage_principal,
        result_kva, phase, surface,
    )

    return {
        "subscription": f"{result_kva} kVA",
        "phase": phase,
        "profile": profile_key,
        "profile_label": profile["label"],
        "justification": justification,
        "calibre_edf": _calibre_edf_from_kva(result_kva),
        "details": {
            "surface": surface,
            "nb_chambres": nb_chambres,
            "has_pac": has_pac,
            "has_ve": has_ve,
            "has_atelier": has_atelier,
            "chauffage_type": chauffage_type,
            "presence_plaque": presence_plaque,
            "presence_chauffe_eau": presence_chauffe_eau,
            "ve_type": ve_type,
            "pac_type": pac_type,
            "chauffage_principal": chauffage_principal,
            "profile": profile_key,
            "base_kva": base,
            "modifiers": parts,
            "total_kva": total,
            "result_kva": result_kva,
        },
    }


# ---------------------------------------------------------------------------
# Base progressive selon la surface
# ---------------------------------------------------------------------------

def _compute_surface_base(surface: float) -> int:
    """Calcule une base d'abonnement progressive selon la surface.

    6 kVA minimum, puis +1 kVA par tranche de ~15 m² au-delà de 30 m²,
    plafonné à 12 kVA pour ne pas surdimensionner les très grandes surfaces.
    """
    if surface <= 30:
        return 6
    extra = int((surface - 30) / 15)
    return min(6 + extra, 12)


# ---------------------------------------------------------------------------
# Modulateurs par équipement
# ---------------------------------------------------------------------------

def _ve_modifier(ve_type: str):
    """Modifier VE selon le type de charge."""
    mapping = {
        "lent": (0, "VE charge lente 3.7kW"),
        "standard": (2, "borne VE 7kW"),
        "rapide": (4, "borne VE rapide 11kW"),
        "22kw": (5, "borne VE 22kW triphasée"),
    }
    return mapping.get(ve_type, (2, "borne VE"))


def _atelier_modifier(surface: float):
    """Modifier atelier selon la surface (proxy de l'importance)."""
    if surface > 150:
        return (3, "atelier important")
    elif surface > 80:
        return (2, "atelier équipé")
    return (1, "petit atelier")


# ---------------------------------------------------------------------------
# Phase — très conservateur
# ---------------------------------------------------------------------------

def determine_phase_type(
    total_kva: int = 12,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
    pac_type: str = "standard",
    ve_type: str = "standard",
    surface: float = 0,
) -> str:
    """Détermine le type d'alimentation.

    Monophasé par défaut pour tout logement résidentiel.
    Triphasé uniquement dans les cas vraiment justifiés :
      - PAC triphasée
      - Borne VE 22 kW
      - Atelier lourd (> 150 m²)
      - Puissance totale > 18 kVA (cas exceptionnel)
    """
    if pac_type == "tri" and surface > 100:
        return "triphasé"

    if ve_type == "22kw":
        return "triphasé"

    if has_atelier and surface > 150 and total_kva > 15:
        return "triphasé"

    if total_kva > 18:
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
# Extraction paramètres depuis circuits (fallback mode manuel)
# ---------------------------------------------------------------------------

def extract_housing_params_from_circuits(circuits) -> Dict:
    """Extrait les paramètres logement depuis la liste de circuits.

    Utilise les noms de circuits pour inférer la surface et le nombre de
    chambres de manière réaliste. Fonction de secours quand les paramètres
    explicites (surface, nb_chambres) ne sont pas disponibles.
    """
    noms = [c.nom.lower() for c in circuits]

    has_pac = any("pac" in n or "pompe" in n for n in noms)
    has_ve = any("borne" in n or "irve" in n or "vehicule" in n for n in noms)
    has_atelier = any("atelier" in n for n in noms)
    presence_plaque = any("plaque" in n for n in noms)
    presence_chauffe_eau = any("chauffe" in n for n in noms)

    has_sejour = any("séjour" in n or "sejour" in n or "salon" in n for n in noms)
    has_cuisine = any("cuisine" in n for n in noms)

    chambre_nums = set()
    for n in noms:
        m = re.search(r'chambre\s*(\d+)', n)
        if m:
            chambre_nums.add(int(m.group(1)))
    nb_estimated_chambres = max(len(chambre_nums), 1 if has_sejour else 0, 1)

    estimated_surface = 0
    if has_sejour:
        estimated_surface += 25
    if has_cuisine:
        estimated_surface += 10
    estimated_surface += nb_estimated_chambres * 12

    if estimated_surface < 30:
        estimated_surface = 50

    return {
        "surface": estimated_surface,
        "nb_chambres": nb_estimated_chambres,
        "has_pac": has_pac,
        "has_ve": has_ve,
        "has_atelier": has_atelier,
        "presence_plaque": presence_plaque,
        "presence_chauffe_eau": presence_chauffe_eau,
    }


def heuristic_sizing_from_circuits(circuits) -> Dict:
    """Dimensionnement heuristique depuis une liste de circuits (mode manuel)."""
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
    """Dimensionnement heuristique depuis paramètres logement."""
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
    """Calcule les puissances installées à titre informatif uniquement."""
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
    mapping = {6: "30A", 9: "45A", 12: "60A", 15: "75A", 18: "90A"}
    return mapping.get(kva, "90A")


def _build_justification(
    profile: Dict,
    parts: list,
    chauffage_type: str,
    chauffage_principal: bool,
    result_kva: int,
    phase: str,
    surface: float,
) -> str:
    """Construit une justification lisible."""
    phrases = [profile["description"]]

    if parts:
        phrases.append("équipements : " + ", ".join(parts))

    if not parts and surface <= 35:
        phrases.append("abonnement minimum")

    phrases.append(f"abonnement conseillé {result_kva} kVA")

    if phase == "triphasé":
        phrases.append("alimentation triphasée recommandée")

    return " — ".join(phrases)
