import math
from core.models import InterDiff, Circuit
from core.rules import type_inter_diff, regles_circuit


def generer_circuits_logement(surface, nb_chambres):
    """Génère automatiquement les circuits d'un logement selon NF C 15-100 simplifié.

    Règles :
    - Séjour : ≥ 5 prises (< 28m²) ou ≥ 7 prises (≥ 28m²)
    - Chambres : 3 prises min par chambre
    - Cuisine : 6 prises min + circuits spécialisés obligatoires
    - Éclairage : 1 circuit par 100m² (arrondi supérieur)
    """
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
    # Circuits spécialisés cuisine obligatoires
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
    points_ecl = max(1, math.ceil(surface / 20))  # estimation: 1 point tous les 20m²
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
    """Analyse un interdifférentiel et retourne une liste d'alertes.

    Vérifie :
    - > 8 circuits (NF C 15-100)
    - puissance > 9000 VA (risque surcharge)
    - type A utilisé pour circuits non concernés
    """
    alertes = []

    # Nombre de circuits > 8
    if len(inter.circuits) > 8:
        alertes.append(f"⚠️ Trop de circuits ({len(inter.circuits)}/8 max)")

    # Puissance totale
    p_totale = puissance_inter(inter)
    if p_totale > 9000:
        alertes.append(f"⚡ Puissance élevée : {p_totale} VA (> 9000 VA)")

    # Type A avec seulement des circuits non-A (sous-utilisation)
    if inter.type == "A":
        has_a_circuit = any(type_inter_diff(c) == "A" for c in inter.circuits)
        if not has_a_circuit:
            alertes.append("ℹ️ Type A utilisé sans circuit nécessitant Type A")

    # Vérifier si un circuit Type A est sur un ID AC (incohérence)
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

    # Chercher un ID compatible de même type avec place disponible
    for inter in tableau.values():
        if inter.type == t and len(inter.circuits) < 8:
            inter.circuits.append(circuit)
            return tableau

    # Créer un nouvel ID
    new_id = max(tableau.keys(), default=0) + 1
    tableau[new_id] = InterDiff(id=new_id, type=t, circuits=[circuit])
    return tableau


def generer_tableau(circuits):
    """Génère le tableau électrique avec répartition intelligente.

    Stratégie :
    1. Reconstruire les circuits existants
    2. Trier les nouveaux circuits par puissance décroissante
    3. Répartir en équilibrant la puissance entre IDs
    """
    tableau = reconstruire_tableau(circuits)

    # Nouveaux circuits triés par puissance décroissante
    nouveaux = sorted(
        [c for c in circuits if not c.existant],
        key=lambda c: regles_circuit(c)["puissance"],
        reverse=True
    )

    for c in nouveaux:
        t = type_inter_diff(c)
        regle = regles_circuit(c)

        # Chercher le meilleur ID compatible (celui avec le moins de puissance)
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
            # Créer un nouvel ID
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
    """Détermine le calibre de l'interdifférentiel selon la puissance.

    ≤ 40A → 40A
    > 40A → 63A
    """
    p = puissance_inter(inter)
    courant = p / 230

    if courant <= 40:
        return "40A"
    else:
        return "63A"
