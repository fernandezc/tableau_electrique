from core.models import Circuit, InterDiff


def make_circuit(
    nom: str,
    type_c: str = "prise",
    section: float = 2.5,
    puissance: int | None = None,
    emplacement: str = "",
    nb_max: int = 0,
    nb_reel: int = 0,
    dj_existant: int | None = None,
    existant: bool = False,
    id_diff: int | None = None,
) -> Circuit:
    return Circuit(
        nom=nom, type=type_c, section=section,
        puissance=puissance, emplacement=emplacement,
        nb_max=nb_max, nb_reel=nb_reel,
        dj_existant=dj_existant, existant=existant,
        id_diff=id_diff,
    )


def make_inter(circuits: list, type_inter: str = "AC", id_inter: int = 1) -> InterDiff:
    return InterDiff(id=id_inter, type=type_inter, circuits=list(circuits))


def make_tableau(interdiff_list: list) -> dict:
    return {inter.id: inter for inter in interdiff_list}


def small_apartment_circuits() -> list:
    return [
        make_circuit("Séjour prises", "prise", 2.5, emplacement="Séjour", nb_max=12, nb_reel=5),
        make_circuit("Chambre 1 prises", "prise", 1.5, emplacement="Chambre 1", nb_max=8, nb_reel=3),
        make_circuit("Chambre 1 éclairage", "eclairage", 1.5, emplacement="Chambre 1", nb_max=8, nb_reel=1),
        make_circuit("Cuisine prises", "prise", 2.5, emplacement="Cuisine", nb_max=12, nb_reel=6),
        make_circuit("Plaque cuisson", "specialise", 6.0, puissance=7000, emplacement="Cuisine"),
        make_circuit("Four", "specialise", 2.5, puissance=2500, emplacement="Cuisine"),
        make_circuit("Lave-linge", "specialise", 2.5, puissance=2500, emplacement="Cuisine"),
        make_circuit("Lave-vaisselle", "specialise", 2.5, puissance=2500, emplacement="Cuisine"),
        make_circuit("Chauffe-eau", "specialise", 2.5, puissance=2000, emplacement="Local technique"),
        make_circuit("Éclairage général", "eclairage", 1.5, nb_max=8, nb_reel=3),
    ]


def standard_house_circuits() -> list:
    return [
        make_circuit("Séjour prises", "prise", 2.5, emplacement="Séjour", nb_max=12, nb_reel=7),
        make_circuit("Chambre 1 prises", "prise", 1.5, emplacement="Chambre 1", nb_max=8, nb_reel=3),
        make_circuit("Chambre 1 éclairage", "eclairage", 1.5, emplacement="Chambre 1", nb_max=8, nb_reel=1),
        make_circuit("Chambre 2 prises", "prise", 1.5, emplacement="Chambre 2", nb_max=8, nb_reel=3),
        make_circuit("Chambre 2 éclairage", "eclairage", 1.5, emplacement="Chambre 2", nb_max=8, nb_reel=1),
        make_circuit("Chambre 3 prises", "prise", 1.5, emplacement="Chambre 3", nb_max=8, nb_reel=3),
        make_circuit("Chambre 3 éclairage", "eclairage", 1.5, emplacement="Chambre 3", nb_max=8, nb_reel=1),
        make_circuit("Cuisine prises", "prise", 2.5, emplacement="Cuisine", nb_max=12, nb_reel=6),
        make_circuit("Plaque cuisson", "specialise", 6.0, puissance=7000, emplacement="Cuisine"),
        make_circuit("Four", "specialise", 2.5, puissance=2500, emplacement="Cuisine"),
        make_circuit("Lave-linge", "specialise", 2.5, puissance=2500, emplacement="Cuisine"),
        make_circuit("Lave-vaisselle", "specialise", 2.5, puissance=2500, emplacement="Cuisine"),
        make_circuit("Chauffe-eau", "specialise", 2.5, puissance=2000, emplacement="Local technique"),
        make_circuit("Éclairage général 1", "eclairage", 1.5, nb_max=8, nb_reel=4),
    ]


def house_with_pac_circuits() -> list:
    c = standard_house_circuits()
    c.append(make_circuit("PAC air/eau", "specialise", 4.0, puissance=3000, emplacement="Local technique"))
    return c


def house_with_ev_circuits(ev_name: str = "Borne VE", ev_power: int = 7400) -> list:
    c = standard_house_circuits()
    c.append(make_circuit(ev_name, "specialise", 6.0, puissance=ev_power, emplacement="Extérieur"))
    return c


def house_with_atelier_circuits() -> list:
    c = standard_house_circuits()
    c.append(make_circuit("Atelier prises", "prise", 2.5, puissance=3000, emplacement="Atelier", nb_max=12, nb_reel=4))
    c.append(make_circuit("Atelier éclairage", "eclairage", 1.5, emplacement="Atelier", nb_max=8, nb_reel=2))
    return c
