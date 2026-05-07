"""
Règles de dimensionnement des interdifférentiels.

Calibre ID (40A / 63A) et type requis (A / AC).
"""

INTER_CALIBER_RULES = {
    "plaque": {"caliber": "63A"},
    "pac": {"caliber": "63A"},
    "pompe": {"caliber": "63A"},
    "borne": {"caliber": "63A"},
    "irve": {"caliber": "63A"},
    "vehicule": {"caliber": "63A"},
}

INTER_HEAVY_EQUIPMENT = [
    "chauffe_eau", "four", "lave_vaisselle", "lave_linge",
]

INTER_HEAVY_THRESHOLD = 3

INTER_TYPE_A_MANDATORY = [
    "plaque", "lave_linge", "lave-linge",
    "irve", "borne_irve", "borne",
    "vehicule electrique", "chauffe_eau",
]

INTER_TYPE_A_RECOMMENDED = [
    "four", "lave_vaisselle", "seche_linge",
]

INTER_SPECIALISES_A = [
    "plaque", "lave_linge", "lave-linge", "irve", "borne_irve", "borne",
]

INTER_SPECIALISES_AC = [
    "four", "lave_vaisselle", "seche_linge", "chauffe_eau",
]
