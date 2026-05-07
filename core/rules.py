from core.models import Circuit

# --- Constantes métier centralisées ---

# Section (mm²) -> Calibre max DJ (A)
SECTION_MAX_DJ = {
    1.5: 16,
    2.5: 20,
    4.0: 25,
    6.0: 32,
    10.0: 40,
}

# Coefficients de foisonnement (simultanéité)
SIMULTANEITY_FACTORS = {
    "plaque": 0.7,
    "four": 0.5,
    "lave_linge": 0.4,
    "lave_vaisselle": 0.4,
    "chauffe_eau": 0.5,
    "prises": 0.2,
    "eclairage": 0.8,
    "vmc": 1.0,
    "clim": 0.7,
    "pac": 0.8,
    "borne_ve": 1.0,
}

# Largeur modules DIN par équipement
MODULE_WIDTHS = {
    "DJ_1P": 1,      # Disjoncteur 1 pôle
    "DJ_2P": 2,      # Disjoncteur 2 pôles
    "ID_TYPE_A": 2,   # Interdifférentiel Type A (36mm -> 2 modules)
    "ID_TYPE_AC": 2,  # Interdifférentiel Type AC
    "PARAFOUDRE": 2,
    "TELErupteur": 1,
    "CONTACTEUR": 2,
}

# Circuits nécessitant obligatoirement un Type A
TYPE_A_MANDATORY = ["plaque", "lave_linge", "lave-linge", "irve", "borne_irve", "borne", "vehicule electrique", "chauffe_eau"]

# Circuits recommandant un Type A (sensibles)
TYPE_A_RECOMMENDED = ["four", "lave_vaisselle", "seche_linge"]

# Détection de type de circuit spécialisé à partir du nom (obsolète, remplacée par validateurs)
SPECIALISES_A = ["plaque", "lave_linge", "lave-linge", "irve", "borne_irve"]
SPECIALISES_AC = ["four", "lave_vaisselle", "seche_linge", "chauffe_eau"]


def identifier_specialise(nom):
    """Identifie le type de circuit spécialisé à partir du nom."""
    n = nom.lower().replace(" ", "_")
    for s in SPECIALISES_A + SPECIALISES_AC:
        if s in n:
            return s
    return None


def regles_circuit(circuit):
    """Règles NF C 15-100 simplifiées par type de circuit."""
    if isinstance(circuit, dict):
        circuit = Circuit(**circuit)
    if circuit.type == "prise":
        if circuit.section == 1.5:
            return {"disj": 16, "max": 8, "puissance": 2000, "label": "Prises 1.5mm²"}
        return {"disj": 20, "max": 12, "puissance": 3000, "label": "Prises 2.5mm²"}

    if circuit.type == "eclairage":
        return {"disj": 16, "max": 8, "puissance": 1000, "label": "Éclairage"}

    if circuit.type == "specialise":
        nom = circuit.nom.lower()

        # Circuits spécialisés avec type A obligatoire
        if any(x in nom for x in ["plaque"]):
            return {"disj": 32, "max": 1, "puissance": 7000, "label": "Plaque cuisson (Type A)"}
        if any(x in nom for x in ["lave_linge", "lave-linge"]):
            return {"disj": 20, "max": 1, "puissance": 2500, "label": "Lave-linge (Type A)"}
        if any(x in nom for x in ["irve", "borne"]):
            return {"disj": 32, "max": 1, "puissance": 7400, "label": "IRVE (Type A)"}

        # Circuits spécialisés type AC
        if any(x in nom for x in ["four"]):
            return {"disj": 20, "max": 1, "puissance": 2500, "label": "Four"}
        if any(x in nom for x in ["lave_vaisselle"]):
            return {"disj": 20, "max": 1, "puissance": 2500, "label": "Lave-vaisselle"}
        if any(x in nom for x in ["chauffe_eau"]):
            return {"disj": 20, "max": 1, "puissance": 2000, "label": "Chauffe-eau"}
        if any(x in nom for x in ["seche_linge"]):
            return {"disj": 20, "max": 1, "puissance": 2500, "label": "Sèche-linge"}

        # Spécialisé générique
        return {"disj": 20, "max": 1, "puissance": circuit.puissance or 2000, "label": circuit.nom}

    return {"disj": 16, "max": 8, "puissance": 1000, "label": "Non défini"}


def validate_section_vs_breaker(circuit: Circuit):
    """
    Vérifie la cohérence Section / Disjoncteur.
    Retourne une liste d'alertes.
    """
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

    # Vérification DJ existant spécifique
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


def validate_inter_type(circuit: Circuit):
    """
    Vérifie si un circuit nécessite un Type A.
    Retourne 'A' si requis, 'AC' sinon.
    """
    nom = circuit.nom.lower()
    for kw in TYPE_A_MANDATORY:
        if kw in nom:
            return "A"
    return "AC"


def type_inter_diff(circuit: Circuit):
    """Détermine le type d'interdifférentiel requis pour un circuit."""
    nom = circuit.nom.lower()
    if any(x in nom for x in SPECIALISES_A):
        return "A"
    return "AC"


def check_circuit_omissions(circuits):
    """
    Détecte les oublis fréquents dans la conception.
    Retourne une liste d'alertes.
    """
    alertes = []
    noms = [c.nom.lower() for c in circuits]

    # Cuisine
    has_cuisine_prises = any("cuisine" in n and "prise" in n for n in noms)
    has_plaque = any("plaque" in n for n in noms)
    has_four = any("four" in n for n in noms)

    if not has_cuisine_prises:
        alertes.append({"niveau": "warning", "message": "Aucune prise de cuisine détectée", "circuit": None})
    if not has_plaque:
        alertes.append({"niveau": "info", "message": "Pas de plaque cuisson détectée", "circuit": None})
    if not has_four:
        alertes.append({"niveau": "info", "message": "Pas de four détecté", "circuit": None})

    # Éclairage extérieur
    has_ext = any("ext" in n or "exterieur" in n for n in noms)
    if not has_ext:
        alertes.append({"niveau": "info", "message": "Pas d'éclairage extérieur détecté", "circuit": None})

    # VMC
    has_vmc = any("vmc" in n for n in noms)
    if not has_vmc:
        alertes.append({"niveau": "warning", "message": "Pas de VMC détectée", "circuit": None})

    return alertes


def verifier_section_circuit(circuit: Circuit):
    """Vérifie la cohérence entre le type de circuit et la section du conducteur."""
    alertes = []
    nom = circuit.nom.lower()
    section = circuit.section

    if circuit.type == "prise":
        if section < 1.5:
            alertes.append(f"Section {section}mm² trop faible pour prises (min 1.5mm²)")
        elif section < 2.5 and circuit.section == 1.5:
            alertes.append("1.5mm² accepté pour prises mais limité à 8 circuits (2.5mm² recommandé)")

    if circuit.type == "eclairage":
        if section < 1.5:
            alertes.append(f"Section {section}mm² trop faible pour éclairage (min 1.5mm²)")

    if circuit.type == "specialise":
        if "plaque" in nom:
            if section < 6.0:
                alertes.append(f"❌ Plaque : section {section}mm² non conforme — 6mm² obligatoire (32A)")
        elif "irve" in nom or "borne" in nom:
            if section < 6.0:
                alertes.append(f"❌ IRVE : section {section}mm² non conforme — 6mm² minimum")
        elif "lave_linge" in nom or "lave-linge" in nom:
            if section < 2.5:
                alertes.append(f"❌ Lave-linge : section {section}mm² non conforme — 2.5mm² minimum")
        elif "four" in nom:
            if section < 2.5:
                alertes.append(f"⚠️ Four : section {section}mm² faible — 2.5mm² recommandé")
        elif "chauffe_eau" in nom:
            if section < 2.5:
                alertes.append(f"⚠️ Chauffe-eau : section {section}mm² faible — 2.5mm² recommandé")
        elif "lave_vaisselle" in nom:
            if section < 2.5:
                alertes.append(f"⚠️ Lave-vaisselle : section {section}mm² faible — 2.5mm² recommandé")

    return alertes


def verifier_dj_circuit(circuit: Circuit):
    """Compare le disjoncteur existant avec le calibre recommandé."""
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
