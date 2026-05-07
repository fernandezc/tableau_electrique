"""
Impacts des équipements sur l'abonnement et la phase.

Chaque entrée définit le bonus abonnement, le libellé,
et d'éventuels déclencheurs (triphasé, calibre ID imposé, type A).
"""

EQUIPMENT_IMPACT = {
    "plaque_cuisson": {
        "subscription_bonus": 1,
        "label": "cuisson électrique",
        "inter_caliber": "63A",
        "inter_type": "A",
    },
    "chauffe_eau": {
        "subscription_bonus": 0,
        "label": "chauffe-eau",
        "inter_type": "A",
    },
    "pac": {
        "air_air": {
            "subscription_bonus": 2,
            "label": "PAC air/air",
            "inter_caliber": "63A",
        },
        "air_eau": {
            "subscription_bonus": 2,
            "label": "PAC air/eau",
            "inter_caliber": "63A",
        },
        "tri": {
            "subscription_bonus": 3,
            "label": "PAC triphasée",
            "triggers_triphase": True,
            "inter_caliber": "63A",
        },
    },
    "ve": {
        "lent": {
            "subscription_bonus": 0,
            "label": "VE charge lente 3.7kW",
            "inter_caliber": "63A",
        },
        "standard": {
            "subscription_bonus": 2,
            "label": "borne VE 7kW",
            "inter_caliber": "63A",
        },
        "rapide": {
            "subscription_bonus": 4,
            "label": "borne VE rapide 11kW",
            "inter_caliber": "63A",
        },
        "22kw": {
            "subscription_bonus": 5,
            "label": "borne VE 22kW triphasée",
            "triggers_triphase": True,
            "inter_caliber": "63A",
        },
    },
    "atelier": {
        "base_label": "atelier",
        "thresholds": [
            (150, 3, "atelier important"),
            (80, 2, "atelier équipé"),
            (0, 1, "petit atelier"),
        ],
    },
}

HEATING_RULES = {
    "type": "electrique",
    "large_house": {
        "threshold": 100,
        "bonus": 2,
        "label": "chauffage électrique principal",
    },
    "medium_house": {
        "threshold": 70,
        "bonus": 1,
        "label": "chauffage électrique",
    },
}
