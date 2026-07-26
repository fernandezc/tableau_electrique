from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Circuit:
    nom: str
    type: str  # prise, eclairage, specialise
    section: float = 2.5
    puissance: Optional[int] = None
    emplacement: str = ""
    nb_max: int = 0
    nb_reel: int = 0
    dj_existant: Optional[int] = None  # calibre disjoncteur existant (0 = non renseigné)
    existant: bool = False
    id_diff: Optional[int] = None  # ligne / ID différentiel souhaité


@dataclass
class InterDiff:
    id: int
    type: str  # A ou AC
    circuits: List[Circuit] = field(default_factory=list)
