import math
from core.models import InterDiff, Circuit
from core.rules import (
    type_inter_diff, regles_circuit,
    validate_section_vs_breaker, validate_inter_type,
    check_circuit_omissions,
)
# from core.labels import generer_pdf_etiquettes  # Lazy import below if needed


# --- Calcul modules DIN ---

def compute_din_modules(inter: InterDiff):
    """
    Calcule le nombre de modules DIN occupés par un interdifférentiel.
    - ID = 2 modules (36mm)
    - DJ standard = 1 module (18mm) par circuit
    """
    modules = 2  # L'interdifférentiel lui-même
    for c in inter.circuits:
        modules += 1  # DJ 1P = 1 module
    return modules


def compute_total_din_modules(tableau):
    """Calcule le total des modules DIN utilisés."""
    return sum(compute_din_modules(inter) for inter in tableau.values())


def compute_din_remaining(modules_used, max_per_row=36):
    """
    Calcule les modules restants par rangée.
    Par défaut : 36 modules par rangée (630mm).
    """
    return max(0, max_per_row - modules_used)


# --- Estimation charge ID ---

def estimate_inter_load(inter: InterDiff):
    """
    Estime la charge d'un interdifférentiel.
    Retourne un score :
    - < 5000 : légère
    - < 8000 : modérée
    - >= 8000 : forte
    """
    return puissance_inter(inter)


def get_load_level(puissance):
    """Retourne le niveau de charge : 'low', 'medium', 'high'."""
    if puissance < 5000:
        return "low"
    elif puissance < 8000:
        return "medium"
    else:
        return "high"


# --- Génération warnings centralisée ---

def generate_warnings(tableau):
    """
    Génère tous les warnings métier pour le tableau.
    Retourne une liste de dicts avec : niveau, message, circuit, inter.
    """
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
        p = estimate_inter_load(inter)
        level = get_load_level(p)
        if level == "high":
            warnings.append({
                "niveau": "warning",
                "message": f"ID {id_inter} très chargé : {p} VA",
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
            # Déterminer le niveau
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
    """
    Calcule les infos de réserve du tableau.
    Par défaut : 20% de réserve recommandée.
    """
    total_used = compute_total_din_modules(tableau)
    max_modules = 36  # 1 rangée standard
    recommended_max = int(max_modules * (1 - reserve_pct))
    return {
        "used": total_used,
        "remaining": max(0, max_modules - total_used),
        "recommended_max": recommended_max,
        "reserve_ok": total_used <= recommended_max,
    }


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

    # Puissance totale
    p_totale = puissance_inter(inter)
    if p_totale > 9000:
        alertes.append(f"⚡ Puissance élevée : {p_totale} VA (> 9000 VA)")

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
    p = puissance_inter(inter)
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
                score = puissance_inter(inter)
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
    """Calcule la puissance totale d'un interdifférentiel."""
    total = 0
    for c in inter.circuits:
        regle = regles_circuit(c)
        total += regle["puissance"]
    return total


def calibre_inter(inter: InterDiff):
    """Détermine le calibre de l'interdifférentiel selon la puissance."""
    p = puissance_inter(inter)
    courant = p / 230
    if courant <= 40:
        return "40A"
    else:
        return "63A"
