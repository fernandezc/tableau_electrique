import math
from core.models import InterDiff, Circuit
from core.rules import (
    type_inter_diff, regles_circuit,
    validate_section_vs_breaker, validate_inter_type,
    check_circuit_omissions,
    SIMULTANEITY_FACTORS,
)
# Lazy import for labels
# from core.labels import generer_pdf_etiquettes


# --- Calculs de puissance séparés ---

def compute_theoretical_power(inter: InterDiff):
    """Calcule la puissance théorique installée (somme brute)."""
    total = 0
    for c in inter.circuits:
        regle = regles_circuit(c)
        total += regle["puissance"]
    return total


def _get_circuit_factor(c: Circuit):
    """Retourne le coefficient de foisonnement pour un circuit."""
    nom = c.nom.lower()
    for key, factor in SIMULTANEITY_FACTORS.items():
        if key in nom:
            return factor
    if c.type == "prise":
        return SIMULTANEITY_FACTORS.get("prises", 0.2)
    if c.type == "eclairage":
        return SIMULTANEITY_FACTORS.get("eclairage", 0.8)
    return 0.5


def compute_estimated_load(inter: InterDiff):
    """
    Calcule la charge estimée réelle avec coefficients de foisonnement.
    """
    total = 0
    for c in inter.circuits:
        regle = regles_circuit(c)
        factor = _get_circuit_factor(c)
        total += regle["puissance"] * factor
    return int(total)


def compute_total_theoretical_power(tableau):
    """Puissance théorique totale du tableau."""
    return sum(compute_theoretical_power(inter) for inter in tableau.values())


def compute_total_estimated_load(tableau):
    """Charge estimée totale du tableau."""
    return sum(compute_estimated_load(inter) for inter in tableau.values())


def compute_subscription_estimate(total_estimated_va):
    """
    Estime l'abonnement EDF réaliste pour l'habitat résidentiel.
    """
    if total_estimated_va <= 6000:
        return "6 kVA (30A)"
    elif total_estimated_va <= 9000:
        return "9 kVA (45A)"
    elif total_estimated_va <= 12000:
        return "12 kVA (60A)"
    elif total_estimated_va <= 15000:
        return "15 kVA (75A)"
    else:
        return "18 kVA (80A) ou Triphasé"


def compute_inter_load(inter: InterDiff):
    """Alias pour compatibilité - utilise la charge estimée."""
    return compute_estimated_load(inter)


def get_load_level(puissance):
    """Retourne le niveau de charge : 'low', 'medium', 'high'."""
    if puissance < 5000:
        return "low"
    elif puissance < 8000:
        return "medium"
    else:
        return "high"


# --- Calibre interdifférentiel (heuristique réaliste) ---

def calibre_inter(inter: InterDiff):
    """
    Détermine le calibre de l'interdifférentiel (40A ou 63A).
    Logique métier basée sur les équipements, pas sur un calcul puissance/230.
    Délègue au moteur heuristique.
    """
    from core.heuristics import estimate_inter_caliber as _caliber
    return _caliber(inter.circuits)


def suggest_three_phase(total_estimated_va, tableau):
    """
    Détermine si le triphasé est justifié.
    Monophasé par défaut pour le résidentiel standard.
    Le paramètre total_estimated_va est conservé pour compatibilité
    mais n'est plus le critère principal.
    """
    # Collecte tous les noms de circuits
    all_noms = []
    for inter in tableau.values():
        all_noms.extend([c.nom.lower() for c in inter.circuits])

    has_atelier = any("atelier" in n for n in all_noms)
    has_pac_tri = any("pac" in n and "tri" in n for n in all_noms)
    has_pac = any("pac" in n or "pompe" in n for n in all_noms)
    has_ve = any("borne" in n or "irve" in n or "vehicule" in n for n in all_noms)

    # Triphasé justifié uniquement dans ces cas
    if has_atelier:
        return True
    if has_pac_tri:
        return True
    if has_ve and has_pac:
        return True
    if total_estimated_va > 18000:
        return True

    return False


# --- Génération warnings centralisée ---

def generate_warnings(tableau):
    """Génère tous les warnings métier pour le tableau."""
    warnings = []

    # 1. Vérification sections / DJ par circuit
    for id_inter, inter in tableau.items():
        for c in inter.circuits:
            alertes = validate_section_vs_breaker(c)
            for a in alertes:
                if isinstance(a, dict):
                    a["inter"] = id_inter
                    warnings.append(a)
                else:
                    warnings.append({
                        "niveau": "warning",
                        "message": a,
                        "circuit": c.nom,
                        "inter": id_inter,
                    })

    # 2. Vérification type différentiel
    for id_inter, inter in tableau.items():
        for c in inter.circuits:
            required_type = validate_inter_type(c)
            if required_type == "A" and inter.type != "A":
                warnings.append({
                    "niveau": "error",
                    "message": f"Circuit '{c.nom}' nécessite Type A, ID {id_inter} est Type {inter.type}",
                    "circuit": c.nom,
                    "inter": id_inter,
                })

    # 3. Nombre max circuits par ID
    for id_inter, inter in tableau.items():
        if len(inter.circuits) > 8:
            warnings.append({
                "niveau": "warning",
                "message": f"ID {id_inter} a {len(inter.circuits)} circuits (max 8)",
                "circuit": None,
                "inter": id_inter,
            })

    # 4. Estimation charge ID
    for id_inter, inter in tableau.items():
        p = compute_estimated_load(inter)
        level = get_load_level(p)
        if level == "high":
            warnings.append({
                "niveau": "warning",
                "message": f"ID {id_inter} très chargé : {p} VA (estimé)",
                "circuit": None,
                "inter": id_inter,
            })

    # 5. Vérifications omissions
    all_circuits = []
    for inter in tableau.values():
        all_circuits.extend(inter.circuits)
    omissions = check_circuit_omissions(all_circuits)
    for o in omissions:
        warnings.append({**o, "inter": None})

    # 6. Vérifications existantes analyser_inter
    for id_inter, inter in tableau.items():
        alertes = analyser_inter(inter)
        for a in alertes:
            if "🚨" in a or "❌" in a:
                niveau = "error"
            elif "⚠️" in a or "⚡" in a:
                niveau = "warning"
            else:
                niveau = "info"
            warnings.append({
                "niveau": niveau,
                "message": a,
                "circuit": None,
                "inter": id_inter,
            })

    return warnings


# --- Réserve tableau ---

def compute_reserve_info(tableau, reserve_pct=0.20):
    """Calcule les infos de réserve du tableau."""
    total_used = compute_total_din_modules(tableau)
    max_modules = 36  # 1 rangée standard
    recommended_max = int(max_modules * (1 - reserve_pct))
    return {
        "used": total_used,
        "remaining": max(0, max_modules - total_used),
        "recommended_max": recommended_max,
        "reserve_ok": total_used <= recommended_max,
    }


# --- Modules DIN ---

def compute_din_modules(inter: InterDiff):
    """Calcule le nombre de modules DIN occupés par un interdifférentiel."""
    modules = 2  # L'interdifférentiel lui-même
    for c in inter.circuits:
        modules += 1  # DJ 1P = 1 module
    return modules


def compute_total_din_modules(tableau):
    """Calcule le total des modules DIN utilisés."""
    return sum(compute_din_modules(inter) for inter in tableau.values())


# --- Fonctions existantes (préservées) ---

def generer_circuits_logement(surface, nb_chambres):
    """Génère automatiquement les circuits d'un logement selon NF C 15-100 simplifié."""
    circuits = []

    # --- Séjour ---
    nb_prises_sejour = 5 if surface < 28 else 7
    max_prises_25 = 12
    if nb_prises_sejour <= max_prises_25:
        circuits.append(Circuit(
            nom=f"Séjour prises ({nb_prises_sejour} prises)",
            type="prise",
            section=2.5,
            puissance=nb_prises_sejour * 250,
            emplacement="Séjour",
            nb_max=max_prises_25,
            nb_reel=nb_prises_sejour
        ))
    else:
        circuits.append(Circuit(
            nom="Séjour prises 1",
            type="prise",
            section=2.5,
            puissance=8 * 250,
            emplacement="Séjour",
            nb_max=max_prises_25,
            nb_reel=8
        ))
        circuits.append(Circuit(
            nom="Séjour prises 2",
            type="prise",
            section=2.5,
            puissance=(nb_prises_sejour - 8) * 250,
            emplacement="Séjour",
            nb_max=max_prises_25,
            nb_reel=nb_prises_sejour - 8
        ))

    # --- Chambres ---
    for i in range(1, nb_chambres + 1):
        circuits.append(Circuit(
            nom=f"Chambre {i} prises (3 prises)",
            type="prise",
            section=1.5,
            puissance=3 * 250,
            emplacement=f"Chambre {i}",
            nb_max=8,
            nb_reel=3
        ))
        circuits.append(Circuit(
            nom=f"Chambre {i} éclairage",
            type="eclairage",
            section=1.5,
            puissance=500,
            emplacement=f"Chambre {i}",
            nb_max=8,
            nb_reel=1
        ))

    # --- Cuisine ---
    circuits.append(Circuit(
        nom="Cuisine prises (6 prises)",
        type="prise",
        section=2.5,
        puissance=6 * 250,
        emplacement="Cuisine",
        nb_max=12,
        nb_reel=6
    ))
    circuits.append(Circuit(
        nom="Plaque cuisson",
        type="specialise",
        section=6.0,
        puissance=7000,
        emplacement="Cuisine"
    ))
    circuits.append(Circuit(
        nom="Four",
        type="specialise",
        section=2.5,
        puissance=2500,
        emplacement="Cuisine"
    ))
    circuits.append(Circuit(
        nom="Lave-linge",
        type="specialise",
        section=2.5,
        puissance=2500,
        emplacement="Cuisine"
    ))
    circuits.append(Circuit(
        nom="Lave-vaisselle",
        type="specialise",
        section=2.5,
        puissance=2500,
        emplacement="Cuisine"
    ))

    # --- Circuits spécialisés hors cuisine ---
    circuits.append(Circuit(
        nom="Chauffe-eau",
        type="specialise",
        section=2.5,
        puissance=2000,
        emplacement="Local technique"
    ))

    # --- Éclairage ---
    nb_circuits_ecl = max(1, math.ceil(surface / 100))
    points_ecl = max(1, math.ceil(surface / 20))
    for i in range(1, nb_circuits_ecl + 1):
        points_circuit = min(8, points_ecl // nb_circuits_ecl)
        circuits.append(Circuit(
            nom=f"Éclairage général {i}",
            type="eclairage",
            section=1.5,
            puissance=1000,
            nb_max=8,
            nb_reel=points_circuit
        ))

    return circuits


def reconstruire_tableau(circuits):
    """Reconstruit le tableau à partir des circuits existants."""
    tableau = {}
    for c in circuits:
        if c.existant and c.id_diff is not None:
            if c.id_diff not in tableau:
                tableau[c.id_diff] = InterDiff(
                    id=c.id_diff,
                    type=type_inter_diff(c)
                )
            tableau[c.id_diff].circuits.append(c)
    return tableau


def analyser_inter(inter: InterDiff):
    """Analyse un interdifférentiel et retourne une liste d'alertes."""
    alertes = []

    # Nombre de circuits > 8
    if len(inter.circuits) > 8:
        alertes.append("⚠️ Trop de circuits ({len(inter.circuits)}/8 max)")

    # Puissance estimée
    p_totale = compute_estimated_load(inter)
    if p_totale > 9000:
        alertes.append(f"⚡ Puissance estimée élevée : {p_totale} VA")

    # Type A avec seulement des circuits non-A
    if inter.type == "A":
        has_a_circuit = any(type_inter_diff(c) == "A" for c in inter.circuits)
        if not has_a_circuit:
            alertes.append("ℹ️ Type A utilisé sans circuit nécessitant Type A")

    # Vérifier si un circuit Type A est sur un ID AC
    if inter.type == "AC":
        has_a_circuit = any(type_inter_diff(c) == "A" for c in inter.circuits)
        if has_a_circuit:
            alertes.append("🚨 Circuit Type A sur ID AC — incompatible !")

    return alertes


def verifier_interdiff(inter: InterDiff):
    """Vérifie la conformité d'un interdifférentiel."""
    erreurs = []
    if len(inter.circuits) > 8:
        erreurs.append("Trop de circuits")
    p = compute_estimated_load(inter)
    if p > 11000:
        erreurs.append("Puissance excessive (> 11000 VA)")
    return "OK" if not erreurs else " / ".join(erreurs)


def ajouter_circuit(tableau, circuit):
    """Ajoute un circuit au tableau existant en respectant le type."""
    t = type_inter_diff(circuit)
    for inter in tableau.values():
        if inter.type == t and len(inter.circuits) < 8:
            inter.circuits.append(circuit)
            return tableau
    new_id = max(tableau.keys(), default=0) + 1
    tableau[new_id] = InterDiff(id=new_id, type=t, circuits=[circuit])
    return tableau


def generer_tableau(circuits):
    """Génère le tableau électrique avec répartition intelligente."""
    tableau = reconstruire_tableau(circuits)
    nouveaux = sorted(
        [c for c in circuits if not c.existant],
        key=lambda c: regles_circuit(c)["puissance"],
        reverse=True
    )
    for c in nouveaux:
        t = type_inter_diff(c)
        regle = regles_circuit(c)
        meilleur_id = None
        meilleur_score = float("inf")
        for id_inter, inter in tableau.items():
            if inter.type == t and len(inter.circuits) < 8:
                score = compute_estimated_load(inter)
                if score < meilleur_score:
                    meilleur_score = score
                    meilleur_id = id_inter
        if meilleur_id is not None:
            tableau[meilleur_id].circuits.append(c)
        else:
            new_id = max(tableau.keys(), default=0) + 1
            tableau[new_id] = InterDiff(id=new_id, type=t, circuits=[c])
    return tableau


def puissance_inter(inter: InterDiff):
    """Calcule la puissance totale d'un interdifférentiel (pour compatibilité)."""
    return compute_estimated_load(inter)


# ---------------------------------------------------------------------------
# Point d'entrée principal du dimensionnement heuristique
# ---------------------------------------------------------------------------

def compute_sizing_decision(tableau, surface=None, nb_chambres=None):
    """
    Point d'entrée unique pour le dimensionnement complet.

    Retourne un dict structuré avec :
      - subscription : str (abonnement conseillé)
      - phase : str (monophasé/triphasé)
      - profile : str (profil logement)
      - profile_label : str
      - justification : str
      - ids : dict des calibres par ID
      - power_diagnostic : dict (informatif)
    """
    from core.heuristics import (
        estimate_subscription_residential,
        extract_housing_params_from_circuits,
        heuristic_sizing_from_circuits,
        heuristic_sizing_from_params,
        estimate_inter_caliber as _caliber,
        compute_installed_power,
    )

    all_circuits = []
    for inter in tableau.values():
        all_circuits.extend(inter.circuits)

    if surface is not None and nb_chambres is not None:
        params = extract_housing_params_from_circuits(all_circuits)
        heuristic = estimate_subscription_residential(
            surface=surface,
            nb_chambres=nb_chambres,
            has_pac=params["has_pac"],
            has_ve=params["has_ve"],
            has_atelier=params["has_atelier"],
            presence_plaque=params["presence_plaque"],
            presence_chauffe_eau=params["presence_chauffe_eau"],
        )
    else:
        heuristic = heuristic_sizing_from_circuits(all_circuits)

    ids = {}
    for id_inter, inter in tableau.items():
        ids[id_inter] = {
            "calibre": _caliber(inter.circuits),
            "type": inter.type,
            "nb_circuits": len(inter.circuits),
        }

    power = compute_installed_power(all_circuits)

    return {
        "subscription": heuristic["subscription"],
        "phase": heuristic["phase"],
        "profile": heuristic["profile"],
        "profile_label": heuristic["profile_label"],
        "justification": heuristic["justification"],
        "calibre_edf": heuristic["calibre_edf"],
        "ids": ids,
        "power_diagnostic": power,
        "details": heuristic["details"],
    }
