SCENARIOS = {
    "studio": {
        "surface": 25,
        "nb_chambres": 1,
        "presence_plaque": False,
        "presence_chauffe_eau": False,
        "attendu": {"subscription": "6 kVA", "phase": "monophasé", "profile": "studio"},
    },
    "t2_standard": {
        "surface": 50,
        "nb_chambres": 2,
        "attendu": {"subscription": "9 kVA", "phase": "monophasé", "profile": "t2"},
    },
    "t2_equipe": {
        "surface": 50,
        "nb_chambres": 2,
        "has_pac": True,
        "has_ve": True,
        "has_atelier": True,
        "attendu": {"subscription": "12 kVA", "phase": "monophasé"},
    },
    "maison_familiale": {
        "surface": 90,
        "nb_chambres": 3,
        "attendu": {"subscription": "12 kVA", "phase": "monophasé", "profile": "t3_t4"},
    },
    "maison_grande": {
        "surface": 120,
        "nb_chambres": 4,
        "attendu": {"subscription": "15 kVA", "phase": "monophasé"},
    },
    "maison_pac": {
        "surface": 120,
        "nb_chambres": 4,
        "has_pac": True,
        "pac_type": "air_eau",
        "attendu": {"subscription": "15 kVA", "phase": "monophasé"},
    },
    "ve_lent": {
        "surface": 80,
        "nb_chambres": 3,
        "has_ve": True,
        "ve_type": "lent",
        "attendu": {"phase": "monophasé"},
    },
    "ve_22kw": {
        "surface": 120,
        "nb_chambres": 4,
        "has_ve": True,
        "ve_type": "22kw",
        "attendu": {"subscription": "18 kVA", "phase": "triphasé"},
    },
    "atelier_leger": {
        "surface": 70,
        "nb_chambres": 2,
        "has_atelier": True,
        "attendu": {"subscription": "12 kVA", "phase": "monophasé"},
    },
    "atelier_lourd": {
        "surface": 160,
        "nb_chambres": 3,
        "has_atelier": True,
        "attendu": {"subscription": "18 kVA", "phase": "triphasé"},
    },
    "pac_ve_standard": {
        "surface": 120,
        "nb_chambres": 4,
        "has_pac": True,
        "has_ve": True,
        "ve_type": "standard",
        "pac_type": "air_eau",
        "attendu": {"phase": "monophasé"},
    },
}


SCENARIOS_PARAMETRIQUES = [
    (25, 1, False, False, False, "standard", "air_eau", False, "6 kVA", "monophasé"),
    (50, 2, False, False, False, "standard", "air_eau", True, "9 kVA", "monophasé"),
    (70, 2, False, False, False, "standard", "air_eau", True, "12 kVA", "monophasé"),
    (90, 3, False, False, False, "standard", "air_eau", True, "12 kVA", "monophasé"),
    (120, 4, True, False, False, "standard", "air_eau", True, "15 kVA", "monophasé"),
    (120, 4, False, True, False, "lent", "air_eau", True, "15 kVA", "monophasé"),
    (120, 4, False, True, False, "22kw", "air_eau", True, "18 kVA", "triphasé"),
    (70, 2, False, False, True, "standard", "air_eau", True, "12 kVA", "monophasé"),
    (160, 3, False, False, True, "standard", "air_eau", True, "18 kVA", "triphasé"),
    (50, 2, True, True, False, "standard", "air_eau", True, "12 kVA", "monophasé"),
]
