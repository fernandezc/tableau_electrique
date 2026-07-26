from core import database
from core.engine import generer_tableau
from core.import_export import normalize_imported_projects
from core.labels import generer_pdf_etiquettes_bytes
from tests.helpers import make_circuit, make_inter, make_tableau


def test_normalize_imported_projects_accepts_backup_list():
    payload = [{
        "name": "Maison",
        "circuits": [{"nom": "Prises séjour", "type": "prise", "section": 2.5}],
        "metadata": {"surface": 90, "chambres": 3},
    }]

    projects = normalize_imported_projects(payload)

    assert len(projects) == 1
    assert projects[0]["name"] == "Maison"
    assert projects[0]["metadata"]["surface"] == 90


def test_normalize_imported_projects_accepts_legacy_formats():
    legacy_project = {
        "circuits": [{"nom": "Cuisine", "type": "prise", "section": 2.5}],
        "metadata": {"surface": 50},
    }
    legacy_circuits = [{"nom": "Éclairage", "type": "eclairage", "section": 1.5}]

    project_result = normalize_imported_projects(legacy_project, default_name="Ancien")
    circuits_result = normalize_imported_projects(legacy_circuits, default_name="Circuits")

    assert project_result[0]["name"] == "Ancien"
    assert project_result[0]["metadata"]["surface"] == 50
    assert circuits_result[0]["name"] == "Circuits"
    assert circuits_result[0]["circuits"] == legacy_circuits


def test_save_project_persists_empty_circuits_and_clears_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "tableau_elect.db"))
    database.init_db()

    pid = database.create_project("Projet test")
    database.save_project(
        pid,
        [make_circuit("Prises séjour", "prise", emplacement="Séjour")],
        metadata={
            "surface": 70,
            "chambres": 2,
            "has_pac": True,
            "has_ve": True,
            "has_atelier": True,
        },
    )

    database.save_project(pid, [], metadata={})

    circuits, metadata, name = database.load_project(pid)

    assert name == "Projet test"
    assert circuits == []
    assert metadata == {
        "surface": None,
        "chambres": None,
        "has_pac": False,
        "has_ve": False,
        "has_atelier": False,
        "calibres_id": {},
    }


def test_save_project_persists_id_calibers(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "tableau_elect.db"))
    database.init_db()

    pid = database.create_project("Projet calibres")
    database.save_project(
        pid,
        [make_circuit("Prises séjour", "prise", emplacement="Séjour")],
        metadata={
            "calibres_id": {"1": "63A", "2": "40A"},
        },
    )

    _, metadata, _ = database.load_project(pid)

    assert metadata["calibres_id"] == {"1": "63A", "2": "40A"}
    assert metadata["types_id"] == {}


def test_save_project_persists_id_types(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "tableau_elect.db"))
    database.init_db()

    pid = database.create_project("Projet types")
    database.save_project(
        pid,
        [make_circuit("Prises séjour", "prise", emplacement="Séjour")],
        metadata={
            "types_id": {"1": "A", "2": "AC"},
        },
    )

    _, metadata, _ = database.load_project(pid)

    assert metadata["types_id"] == {"1": "A", "2": "AC"}


def test_generer_pdf_etiquettes_bytes_returns_pdf_bytes():
    tableau = make_tableau([
        make_inter([make_circuit("Prises séjour", "prise", emplacement="Séjour")], id_inter=1),
    ])

    pdf_data = generer_pdf_etiquettes_bytes(tableau)

    assert pdf_data.startswith(b"%PDF")
    assert len(pdf_data) > 100


def test_normalize_imported_projects_preserves_multi_project_backup_order():
    payload = [
        {"name": "Projet vide", "circuits": [], "metadata": {}},
        {
            "name": "Maison",
            "circuits": [{"nom": "Prises séjour", "type": "prise", "section": 2.5}],
            "metadata": {"surface": 90},
        },
    ]

    projects = normalize_imported_projects(payload)

    assert [project["name"] for project in projects] == ["Projet vide", "Maison"]
    assert [len(project["circuits"]) for project in projects] == [0, 1]


def test_generer_tableau_preserves_manual_line_assignment_for_any_circuit():
    circuits = [
        make_circuit("Plaque cuisson", "specialise", 6.0, puissance=7000, id_diff=3),
        make_circuit("Éclairage séjour", "eclairage", 1.5, puissance=1000),
    ]

    tableau = generer_tableau(circuits)

    assert 3 in tableau
    assert any(c.nom == "Plaque cuisson" for c in tableau[3].circuits)
