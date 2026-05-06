from core.models import Circuit


# Détection de type de circuit spécialisé à partir du nom
SPECIALISES_A = ["plaque", "lave_linge", "lave-linge", "irve", "borne_irve"]
SPECIALISES_AC = ["four", "lave_vaisselle", "seche_linge", "chauffe_eau"]


def identifier_specialise(nom):
    """Identifie le type de circuit spécialisé à partir du nom."""
    n = nom.lower().replace(" ", "_")
    for s in SPECIALISES_A + SPECIALISES_AC:
        if s in n:
            return s
    return None


def regles_circuit(circuit: Circuit):
    """Règles NF C 15-100 simplifiées par type de circuit."""

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


def verifier_section_circuit(circuit: Circuit):
    """Vérifie la cohérence entre le type de circuit et la section du conducteur.

    Retourne une liste d'alertes si la section n'est pas conforme NF C 15-100.
    """
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
    """Compare le disjoncteur existant avec le calibre recommandé.

    Retourne une liste d'alertes si le DJ existant est sous/sur-dimensionné.
    """
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


def type_inter_diff(circuit: Circuit):
    """Détermine le type d'interdifférentiel requis pour un circuit.

    Type A obligatoire pour : plaque, lave-linge, IRVE
    Tout le reste → AC
    """
    nom = circuit.nom.lower()

    if any(x in nom for x in ["plaque", "lave_linge", "lave-linge", "irve", "borne_irve"]):
        return "A"

    return "AC"
