"""
Règles d'abonnement EDF.

Définit les paliers, la base progressive selon la surface,
et les plafonds de réalisme.
"""

SUBSCRIPTION_TIERS = [
    (6,  "6 kVA",  "30A"),
    (9,  "9 kVA",  "45A"),
    (12, "12 kVA", "60A"),
    (15, "15 kVA", "75A"),
    (18, "18 kVA", "90A"),
]

SURFACE_BASE_RULES = {
    "min_kva": 6,
    "threshold_m2": 30,
    "step_m2": 15,
    "cap_kva": 12,
}

SURFACE_REALISM_CAPS = [
    (50, 12),
    (100, 15),
]

PHASE_RULES = {
    "default": "monophasé",
    "triphase_triggers": {
        "pac_tri_plus_grand_que_100": {
            "condition": "pac_type == 'tri' and surface > 100",
            "label": "PAC triphasée",
        },
        "ve_22kw": {
            "condition": "ve_type == '22kw'",
            "label": "borne VE 22kW triphasée",
        },
        "atelier_lourd": {
            "condition": "has_atelier and surface > 150 and total_kva > 15",
            "label": "atelier lourd",
        },
        "depassement_18kva": {
            "condition": "total_kva > 18",
            "label": "puissance > 18 kVA",
        },
    },
}
