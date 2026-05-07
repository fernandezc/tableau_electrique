"""
Règles NF C 15-100 pour sections, disjoncteurs, et circuits spécialisés.
"""

SECTION_MAX_DJ = {
    1.5: 16,
    2.5: 20,
    4.0: 25,
    6.0: 32,
    10.0: 40,
}

PRISE_RULES = {
    1.5: {"disj": 16, "max": 8, "puissance": 2000, "label": "Prises 1.5mm²"},
    2.5: {"disj": 20, "max": 12, "puissance": 3000, "label": "Prises 2.5mm²"},
}

ECLAIRAGE_RULES = {
    "disj": 16, "max": 8, "puissance": 1000, "label": "Éclairage",
}

SPECIALISE_REQUIREMENTS = {
    "plaque":       {"disj": 32, "max": 1, "puissance": 7000, "min_section": 6.0, "type": "A", "label": "Plaque cuisson (Type A)"},
    "lave_linge":   {"disj": 20, "max": 1, "puissance": 2500, "min_section": 2.5, "type": "A", "label": "Lave-linge (Type A)"},
    "lave-linge":   {"disj": 20, "max": 1, "puissance": 2500, "min_section": 2.5, "type": "A", "label": "Lave-linge (Type A)"},
    "irve":         {"disj": 32, "max": 1, "puissance": 7400, "min_section": 6.0, "type": "A", "label": "IRVE (Type A)"},
    "borne":        {"disj": 32, "max": 1, "puissance": 7400, "min_section": 6.0, "type": "A", "label": "Borne VE (Type A)"},
    "four":         {"disj": 20, "max": 1, "puissance": 2500, "min_section": 2.5, "label": "Four"},
    "lave_vaisselle": {"disj": 20, "max": 1, "puissance": 2500, "min_section": 2.5, "label": "Lave-vaisselle"},
    "chauffe_eau":  {"disj": 20, "max": 1, "puissance": 2000, "min_section": 2.5, "label": "Chauffe-eau"},
    "seche_linge":  {"disj": 20, "max": 1, "puissance": 2500, "min_section": 2.5, "label": "Sèche-linge"},
}
