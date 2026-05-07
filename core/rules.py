from core.models import Circuit

from core.business_rules.section_rules import (
    SECTION_MAX_DJ,
    PRISE_RULES,
    ECLAIRAGE_RULES,
    SPECIALISE_REQUIREMENTS,
)
from core.business_rules.module_rules import (
    MODULE_WIDTHS,
    SIMULTANEITY_FACTORS,
    MAX_CIRCUITS_PER_ID,
)
from core.business_rules.inter_rules import (
    INTER_TYPE_A_MANDATORY,
    INTER_TYPE_A_RECOMMENDED,
    INTER_SPECIALISES_A,
    INTER_SPECIALISES_AC,
    INTER_CALIBER_RULES,
)

TYPE_A_MANDATORY = INTER_TYPE_A_MANDATORY
TYPE_A_RECOMMENDED = INTER_TYPE_A_RECOMMENDED
SPECIALISES_A = INTER_SPECIALISES_A
SPECIALISES_AC = INTER_SPECIALISES_AC


def identifier_specialise(nom):
    n = nom.lower().replace(" ", "_")
    for s in SPECIALISES_A + SPECIALISES_AC:
        if s in n:
            return s
    return None


def regles_circuit(circuit):
    if isinstance(circuit, dict):
        circuit = Circuit(**circuit)

    if circuit.type == "prise":
        return dict(PRISE_RULES.get(circuit.section, PRISE_RULES[2.5]))

    if circuit.type == "eclairage":
        return dict(ECLAIRAGE_RULES)

    if circuit.type == "specialise":
        nom = circuit.nom.lower()
        for keyword, req in SPECIALISE_REQUIREMENTS.items():
            if keyword in nom:
                return {
                    "disj": req["disj"],
                    "max": req["max"],
                    "puissance": req["puissance"],
                    "label": req["label"],
                }
        return {"disj": 20, "max": 1, "puissance": circuit.puissance or 2000, "label": circuit.nom}

    return {"disj": 16, "max": 8, "puissance": 1000, "label": "Non défini"}


def validate_section_vs_breaker(circuit):
    alertes = []
    section = circuit.section
    regle = regles_circuit(circuit)
    dj_conseille = regle["disj"]

    if section in SECTION_MAX_DJ:
        max_dj = SECTION_MAX_DJ[section]
        if dj_conseille > max_dj:
            alertes.append({
                "niveau": "error",
                "message": f"Section {section}mm² incompatible avec DJ {dj_conseille}A (max {max_dj}A)",
                "circuit": circuit.nom,
            })
    else:
        alertes.append({
            "niveau": "warning",
            "message": f"Section {section}mm² non standard",
            "circuit": circuit.nom,
        })

    if circuit.dj_existant and circuit.dj_existant > 0:
        if circuit.dj_existant > dj_conseille:
            alertes.append({
                "niveau": "warning",
                "message": f"DJ surdimensionné : {circuit.dj_existant}A (conseillé {dj_conseille}A)",
                "circuit": circuit.nom,
            })
        elif circuit.dj_existant < dj_conseille:
            alertes.append({
                "niveau": "info",
                "message": f"DJ sous-dimensionné : {circuit.dj_existant}A (conseillé {dj_conseille}A)",
                "circuit": circuit.nom,
            })

    return alertes


def validate_inter_type(circuit):
    nom = circuit.nom.lower()
    for kw in TYPE_A_MANDATORY:
        if kw in nom:
            return "A"
    return "AC"


def type_inter_diff(circuit):
    nom = circuit.nom.lower()
    if any(x in nom for x in SPECIALISES_A):
        return "A"
    return "AC"


def check_circuit_omissions(circuits):
    alertes = []
    noms = [c.nom.lower() for c in circuits]

    has_cuisine_prises = any("cuisine" in n and "prise" in n for n in noms)
    has_plaque = any("plaque" in n for n in noms)
    has_four = any("four" in n for n in noms)

    if not has_cuisine_prises:
        alertes.append({"niveau": "warning", "message": "Aucune prise de cuisine détectée", "circuit": None})
    if not has_plaque:
        alertes.append({"niveau": "info", "message": "Pas de plaque cuisson détectée", "circuit": None})
    if not has_four:
        alertes.append({"niveau": "info", "message": "Pas de four détecté", "circuit": None})

    has_ext = any("ext" in n or "exterieur" in n for n in noms)
    if not has_ext:
        alertes.append({"niveau": "info", "message": "Pas d'éclairage extérieur détecté", "circuit": None})

    has_vmc = any("vmc" in n for n in noms)
    if not has_vmc:
        alertes.append({"niveau": "info", "message": "Pas de VMC détectée", "circuit": None})

    return alertes


def verifier_section_circuit(circuit):
    alertes = []
    nom = circuit.nom.lower()
    section = circuit.section

    if circuit.type == "prise":
        if section < 1.5:
            alertes.append(f"Section {section}mm² trop faible pour prises (min 1.5mm²)")
        elif section < 2.5:
            alertes.append("1.5mm² accepté pour prises mais limité à 8 circuits (2.5mm² recommandé)")

    if circuit.type == "eclairage":
        if section < 1.5:
            alertes.append(f"Section {section}mm² trop faible pour éclairage (min 1.5mm²)")

    if circuit.type == "specialise":
        for keyword, req in SPECIALISE_REQUIREMENTS.items():
            if keyword in nom:
                min_sec = req.get("min_section")
                if min_sec and section < min_sec:
                    prefix = "❌" if "type" in req and req["type"] == "A" else "⚠️"
                    alertes.append(
                        f"{prefix} {req['label']} : section {section}mm² non conforme — {min_sec}mm² minimum"
                    )
                break

    return alertes


def verifier_dj_circuit(circuit):
    alertes = []
    if circuit.dj_existant is None or circuit.dj_existant == 0:
        return alertes

    regle = regles_circuit(circuit)
    dj_conseille = regle["disj"]
    dj_actuel = circuit.dj_existant

    if dj_actuel > dj_conseille:
        alertes.append(f"⚠️ DJ surdimensionné : {dj_actuel}A (conseillé {dj_conseille}A)")
    elif dj_actuel < dj_conseille:
        alertes.append(f"ℹ️ DJ sous-dimensionné : {dj_actuel}A (conseillé {dj_conseille}A)")

    return alertes
