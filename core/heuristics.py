import re
from typing import Dict, List, Optional

from core.business_rules.subscription_rules import (
    SUBSCRIPTION_TIERS,
    SURFACE_BASE_RULES,
    SURFACE_REALISM_CAPS,
    PHASE_RULES,
)
from core.business_rules.equipment_rules import (
    EQUIPMENT_IMPACT,
    HEATING_RULES,
)
from core.business_rules.inter_rules import (
    INTER_CALIBER_RULES,
    INTER_HEAVY_EQUIPMENT,
    INTER_HEAVY_THRESHOLD,
    INTER_TYPE_A_MANDATORY,
)

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
        "description": "Maison équipée d'une pompe à chaleur",
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


def classify_housing_profile(
    surface: float,
    nb_chambres: int,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
) -> str:
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


def _compute_surface_base(surface: float) -> int:
    rules = SURFACE_BASE_RULES
    if surface <= rules["threshold_m2"]:
        return rules["min_kva"]
    extra = int((surface - rules["threshold_m2"]) / rules["step_m2"])
    return min(rules["min_kva"] + extra, rules["cap_kva"])


def _ve_modifier(ve_type: str):
    ve_data = EQUIPMENT_IMPACT["ve"].get(ve_type, EQUIPMENT_IMPACT["ve"]["standard"])
    return (ve_data["subscription_bonus"], ve_data["label"])


def _atelier_modifier(surface: float):
    atelier_data = EQUIPMENT_IMPACT["atelier"]
    for threshold, bonus, label in sorted(atelier_data["thresholds"], reverse=True):
        if surface > threshold:
            return (bonus, label)
    return (1, atelier_data["base_label"])


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
    if chauffage_principal is None:
        chauffage_principal = (chauffage_type == "electrique" and not has_pac)

    profile_key = classify_housing_profile(
        surface, nb_chambres, has_pac, has_ve, has_atelier,
    )
    profile = HOUSING_PROFILES[profile_key]

    base = _compute_surface_base(surface)

    parts = []
    total = base

    plaque_impact = EQUIPMENT_IMPACT["plaque_cuisson"]
    if presence_plaque:
        total += plaque_impact["subscription_bonus"]
        parts.append(plaque_impact["label"])

    if has_pac:
        pac_data = EQUIPMENT_IMPACT["pac"].get(pac_type, EQUIPMENT_IMPACT["pac"]["air_eau"])
        total += pac_data["subscription_bonus"]
        parts.append(pac_data["label"])
    elif chauffage_principal:
        h_rules = HEATING_RULES
        large = h_rules["large_house"]
        medium = h_rules["medium_house"]
        if surface > large["threshold"]:
            total += large["bonus"]
            parts.append(large["label"])
        elif surface >= medium["threshold"]:
            total += medium["bonus"]
            parts.append(medium["label"])

    if has_ve:
        ve_mod, ve_label = _ve_modifier(ve_type)
        total += ve_mod
        parts.append(ve_label)

    if has_atelier:
        at_mod, at_label = _atelier_modifier(surface)
        total += at_mod
        parts.append(at_label)

    for max_surface, max_kva in SURFACE_REALISM_CAPS:
        if surface <= max_surface:
            total = min(total, max_kva)
            break

    result_kva = _round_to_standard_subscription(total)

    phase = determine_phase_type(
        total_kva=total,
        has_pac=has_pac,
        has_ve=has_ve,
        has_atelier=has_atelier,
        pac_type=pac_type,
        ve_type=ve_type,
        surface=surface,
    )

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


def determine_phase_type(
    total_kva: int = 12,
    has_pac: bool = False,
    has_ve: bool = False,
    has_atelier: bool = False,
    pac_type: str = "standard",
    ve_type: str = "standard",
    surface: float = 0,
) -> str:
    if pac_type == "tri" and surface > 100:
        return "triphasé"
    if ve_type == "22kw":
        return "triphasé"
    if has_atelier and surface > 150 and total_kva > 15:
        return "triphasé"
    if total_kva > 18:
        return "triphasé"
    return PHASE_RULES["default"]


def estimate_inter_caliber(circuits: list) -> str:
    noms = [c.nom.lower() for c in circuits]

    for keyword, rule in INTER_CALIBER_RULES.items():
        if any(keyword in n for n in noms):
            return rule["caliber"]

    noms_norm = [n.replace("-", "_") for n in noms]
    heavy_count = sum(
        1 for eq in INTER_HEAVY_EQUIPMENT
        if any(eq in n for n in noms_norm)
    )
    if heavy_count >= INTER_HEAVY_THRESHOLD:
        return "63A"

    nb = len(circuits)
    if nb <= 3:
        return "40A"

    return "40A"


def extract_housing_params_from_circuits(circuits) -> Dict:
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
    return estimate_subscription_residential(
        surface=surface,
        nb_chambres=nb_chambres,
        has_pac=has_pac,
        has_ve=has_ve,
        has_atelier=has_atelier,
    )


def compute_installed_power(circuits: list) -> Dict:
    from core.business_rules.module_rules import SIMULTANEITY_FACTORS
    from core.rules import regles_circuit

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
    for key, factor in factors.items():
        if key in nom:
            return factor
    if type_c == "prise":
        return factors.get("prises", 0.2)
    if type_c == "eclairage":
        return factors.get("eclairage", 0.8)
    return 0.5


def _round_to_standard_subscription(kva: int) -> int:
    for tier_kva, _, _ in SUBSCRIPTION_TIERS:
        if kva <= tier_kva:
            return tier_kva
    return SUBSCRIPTION_TIERS[-1][0]


def _calibre_edf_from_kva(kva: int) -> str:
    for tier_kva, _, calibre in SUBSCRIPTION_TIERS:
        if kva <= tier_kva:
            return calibre
    return SUBSCRIPTION_TIERS[-1][2]


def _build_justification(
    profile: Dict,
    parts: list,
    chauffage_type: str,
    chauffage_principal: bool,
    result_kva: int,
    phase: str,
    surface: float,
) -> str:
    phrases = [profile["description"]]

    if parts:
        phrases.append("équipements : " + ", ".join(parts))

    if not parts and surface <= 35:
        phrases.append("abonnement minimum")

    phrases.append(f"abonnement conseillé {result_kva} kVA")

    if phase == "triphasé":
        phrases.append("alimentation triphasée recommandée")

    return " — ".join(phrases)
