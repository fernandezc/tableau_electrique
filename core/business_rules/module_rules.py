"""
Règles de modules DIN et limites du tableau.
"""

MODULE_WIDTHS = {
    "DJ_1P": 1,
    "DJ_2P": 2,
    "ID_TYPE_A": 2,
    "ID_TYPE_AC": 2,
    "PARAFOUDRE": 2,
    "TELErupteur": 1,
    "CONTACTEUR": 2,
}

MAX_CIRCUITS_PER_ID = 8
RESERVE_PERCENTAGE = 0.20
MAX_MODULES_PER_RANGEE = 36

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
