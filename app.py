import streamlit as st
import pandas as pd
from html import escape
from core.models import Circuit
from core.engine import (
    generer_tableau,
    puissance_inter,
    calibre_inter,
    generer_circuits_logement,
    analyser_inter,
    generate_warnings,
    compute_reserve_info,
    compute_total_din_modules,
    compute_theoretical_power,
    compute_total_theoretical_power,
    compute_total_estimated_load,
    compute_subscription_estimate,
    suggest_three_phase,
    compute_sizing_decision,
)
from core.rules import regles_circuit, verifier_section_circuit, verifier_dj_circuit
from core.labels import generer_pdf_etiquettes_bytes
from core.database import (
    init_db, lister_projets, load_project, save_project,
    create_project, delete_project, rename_project,
)
from core.import_export import normalize_imported_projects
import json
import os

# ========================
# INIT
# ========================
st.set_page_config(page_title="⚡ Tableau électrique", layout="wide")

init_db()

# Projets existants
if "current_project_id" not in st.session_state:
    projects = lister_projets()
    if projects:
        st.session_state.current_project_id = projects[0][0]
    else:
        # Migrate circuits.json if exists
        legacy = "circuits.json"
        if os.path.exists(legacy):
            try:
                with open(legacy) as f:
                    imported_projects = normalize_imported_projects(
                        json.load(f),
                        default_name="circuits.json (importé)",
                    )
                if imported_projects:
                    project = imported_projects[0]
                    circuits = [Circuit(**c) for c in project["circuits"]]
                    pid = create_project(project["name"])
                    save_project(pid, circuits, metadata=project.get("metadata") or {})
                    st.session_state.current_project_id = pid
                    st.session_state.circuits = circuits
                    meta = project.get("metadata") or {}
                    for k in ("surface", "chambres"):
                        if k in meta:
                            st.session_state[f"last_{k}"] = meta[k]
                    for k in ("has_pac", "has_ve", "has_atelier"):
                        st.session_state[f"last_{k}"] = meta.get(k, False)
            except Exception:
                pass
        if "current_project_id" not in st.session_state:
            pid = create_project("Projet 1")
            st.session_state.current_project_id = pid

if "circuits" not in st.session_state:
    try:
        circuits, meta, name = load_project(st.session_state.current_project_id)
        st.session_state.circuits = circuits
        if meta.get("surface") is not None:
            st.session_state.last_surface = meta["surface"]
            st.session_state.last_chambres = meta["chambres"]
            st.session_state.last_has_pac = meta.get("has_pac", False)
            st.session_state.last_has_ve = meta.get("has_ve", False)
            st.session_state.last_has_atelier = meta.get("has_atelier", False)
    except Exception:
        st.session_state.circuits = []

if "tableau" not in st.session_state:
    st.session_state.tableau = None

if "import_uploader_key" not in st.session_state:
    st.session_state.import_uploader_key = 0

if "project_selector_key" not in st.session_state:
    st.session_state.project_selector_key = 0

if "project_name" not in st.session_state:
    projects = lister_projets()
    for p in projects:
        if p[0] == st.session_state.current_project_id:
            st.session_state.project_name = p[1]
            break


META_STATE_KEYS = ("last_surface", "last_chambres", "last_has_pac", "last_has_ve", "last_has_atelier")
PDF_STATE_KEYS = ("labels_pdf_bytes", "labels_pdf_name")


def clear_generated_pdf():
    for key in PDF_STATE_KEYS:
        st.session_state.pop(key, None)


def clear_caliber_state():
    for key in list(st.session_state.keys()):
        if key.startswith("caliber_"):
            del st.session_state[key]


def clear_project_metadata_state():
    for key in META_STATE_KEYS:
        st.session_state.pop(key, None)


def clear_derived_state():
    st.session_state.tableau = None
    clear_generated_pdf()
    clear_caliber_state()


def refresh_project_selector():
    st.session_state.project_selector_key += 1


def collect_project_metadata():
    meta = {}
    for k in META_STATE_KEYS:
        if k in st.session_state and st.session_state[k] is not None:
            meta[k.replace("last_", "", 1)] = st.session_state[k]

    calibres = {}
    types_id = {}
    for key, value in st.session_state.items():
        if key.startswith("caliber_") and value:
            calibres[key.removeprefix("caliber_")] = value
        if key.startswith("inter_type_") and value:
            types_id[key.removeprefix("inter_type_")] = value
    meta["calibres_id"] = calibres
    meta["types_id"] = types_id
    return meta


def save_project_preferences():
    save_project(
        st.session_state.current_project_id,
        st.session_state.circuits,
        metadata=collect_project_metadata(),
    )


def auto_save():
    """Sauvegarde automatique dans le projet courant."""
    save_project_preferences()


def _load_project_into_state(pid):
    circuits, meta, name = load_project(pid)
    st.session_state.circuits = circuits
    st.session_state.current_project_id = pid
    st.session_state.project_name = name
    refresh_project_selector()
    clear_derived_state()
    clear_project_metadata_state()
    if meta.get("surface") is not None:
        st.session_state.last_surface = meta["surface"]
        st.session_state.last_chambres = meta["chambres"]
        st.session_state.last_has_pac = meta.get("has_pac", False)
        st.session_state.last_has_ve = meta.get("has_ve", False)
        st.session_state.last_has_atelier = meta.get("has_atelier", False)
    for id_inter, calibre in (meta.get("calibres_id") or {}).items():
        st.session_state[f"caliber_{id_inter}"] = calibre
    for id_inter, inter_type in (meta.get("types_id") or {}).items():
        st.session_state[f"inter_type_{id_inter}"] = inter_type


def apply_id_preferences_to_tableau(tableau):
    for id_inter, inter in tableau.items():
        preferred_type = st.session_state.get(f"inter_type_{id_inter}")
        if preferred_type in {"A", "AC"}:
            inter.type = preferred_type
    return tableau


def persist_tableau_line_assignments(tableau, renumber=False):
    id_map = {}
    sorted_ids = sorted(tableau)
    for idx, id_inter in enumerate(sorted_ids, start=1):
        id_map[id_inter] = idx if renumber else id_inter

    for id_inter, inter in tableau.items():
        target_id = id_map[id_inter]
        for circuit in inter.circuits:
            circuit.id_diff = target_id

    auto_save()
    clear_generated_pdf()
    st.session_state.tableau = generer_tableau(st.session_state.circuits)
    apply_id_preferences_to_tableau(st.session_state.tableau)


def recalculate_tableau_and_persist():
    clear_caliber_state()
    clear_generated_pdf()
    st.session_state.tableau = generer_tableau(st.session_state.circuits)
    apply_id_preferences_to_tableau(st.session_state.tableau)
    persist_tableau_line_assignments(st.session_state.tableau)


def persist_current_id_preferences():
    if st.session_state.tableau is not None:
        apply_id_preferences_to_tableau(st.session_state.tableau)
    save_project_preferences()


def render_labels_preview(tableau):
    rows = []
    for id_inter, inter in sorted(tableau.items()):
        if not inter.circuits:
            continue

        cells = [
            (
                '<div class="label-cell label-id">'
                f'<div class="label-id-title">ID {escape(str(inter.id))}</div>'
                f'<div class="label-id-type">TYPE {escape(inter.type.upper())}</div>'
                '</div>'
            )
        ]

        for circuit in inter.circuits:
            emplacement_html = ""
            if circuit.emplacement:
                emplacement_html = (
                    f'<div class="label-emplacement">{escape(circuit.emplacement.upper())}</div>'
                )

            cells.append(
                '<div class="label-cell label-circuit">'
                f'<div class="label-nom">{escape(circuit.nom.upper())}</div>'
                f'{emplacement_html}'
                '</div>'
            )

        rows.append(
            '<div class="label-row">' + "".join(cells) + '</div>'
        )

    preview_html = """
    <style>
    .labels-preview {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }
    .label-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0;
    }
    .label-cell {
        width: 110px;
        min-height: 86px;
        border: 1px solid #333;
        margin-right: -1px;
        margin-bottom: -1px;
        padding: 0.45rem 0.4rem;
        background: #fff;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }
    .label-id {
        width: 138px;
        background: #f3f3f3;
    }
    .label-id-title {
        font-weight: 700;
        font-size: 1rem;
        line-height: 1.2;
    }
    .label-id-type {
        margin-top: 0.3rem;
        color: #666;
        font-size: 0.78rem;
        line-height: 1.2;
    }
    .label-nom {
        font-weight: 700;
        font-size: 0.8rem;
        line-height: 1.2;
        word-break: break-word;
    }
    .label-emplacement {
        margin-top: 0.35rem;
        color: #666;
        font-size: 0.68rem;
        font-weight: 600;
        line-height: 1.2;
        word-break: break-word;
    }
    </style>
    """

    return preview_html + '<div class="labels-preview">' + "".join(rows) + '</div>'


# ========================
# SIDEBAR : gestion projets
# ========================
with st.sidebar:
    st.header("📁 Projets")

    projects = lister_projets()
    current_ids = [p[0] for p in projects]

    if st.session_state.current_project_id not in current_ids and current_ids:
        _load_project_into_state(current_ids[0])
        st.rerun()

    if projects:
        current_idx = current_ids.index(st.session_state.current_project_id)
        selected = st.selectbox(
            "Projet",
            projects,
            format_func=lambda p: p[1],
            index=current_idx,
            key=f"project_selector_{st.session_state.project_selector_key}",
        )
        if selected[0] != st.session_state.current_project_id:
            _load_project_into_state(selected[0])
            st.rerun()

    col_new, col_del = st.columns(2)
    with col_new:
        if st.button("🆕 Nouveau", use_container_width=True):
            pid = create_project("Nouveau projet")
            _load_project_into_state(pid)
            st.rerun()
    with col_del:
        if st.button("🗑️ Suppr.", use_container_width=True):
            if len(projects) > 1:
                st.session_state["confirm_delete"] = True
                st.rerun()

    if st.session_state.get("confirm_delete"):
        st.warning(f"Supprimer «{st.session_state.project_name}» ?")
        c_ok, c_no = st.columns(2)
        with c_ok:
            if st.button("✅ Oui", key="del_yes", use_container_width=True):
                delete_project(st.session_state.current_project_id)
                remaining = lister_projets()
                if remaining:
                    _load_project_into_state(remaining[0][0])
                else:
                    pid = create_project("Projet 1")
                    st.session_state.circuits = []
                    st.session_state.current_project_id = pid
                    st.session_state.project_name = "Projet 1"
                    clear_project_metadata_state()
                    clear_derived_state()
                del st.session_state["confirm_delete"]
                st.rerun()
        with c_no:
            if st.button("❌ Non", key="del_no", use_container_width=True):
                del st.session_state["confirm_delete"]
                st.rerun()

    if st.button("✏️ Renommer", use_container_width=True):
        st.session_state.show_rename = True
        st.rerun()

    if st.session_state.get("show_rename"):
        new_name = st.text_input("Nouveau nom", value=st.session_state.project_name, key="rename_input")
        c_ok, c_cancel = st.columns(2)
        with c_ok:
            if st.button("OK", key="rename_ok", use_container_width=True):
                if new_name.strip():
                    rename_project(st.session_state.current_project_id, new_name.strip())
                    st.session_state.project_name = new_name.strip()
                    refresh_project_selector()
                st.session_state.show_rename = False
                st.rerun()
        with c_cancel:
            if st.button("Annuler", key="rename_cancel", use_container_width=True):
                st.session_state.show_rename = False
                st.rerun()

    st.caption(f"ID #{st.session_state.current_project_id}")

    st.divider()
    st.caption("💾 Sauvegarde")

    # Export
    projects_data = []
    for pid, pname, _ in projects:
        circs, meta, _ = load_project(pid)
        projects_data.append({
            "id": pid,
            "name": pname,
            "circuits": [vars(c) for c in circs],
            "metadata": meta,
        })
    export_json = json.dumps(projects_data, ensure_ascii=False, indent=2, default=str)
    st.download_button(
        "📥 Exporter projets",
        data=export_json,
        file_name="tableau_elect_backup.json",
        mime="application/json",
        use_container_width=True,
    )

    # Import
    uploaded = st.file_uploader(
        "📥 Importer projets",
        type="json",
        label_visibility="collapsed",
        key=f"import_projects_{st.session_state.import_uploader_key}",
    )
    if uploaded is not None:
        try:
            imported = normalize_imported_projects(
                json.loads(uploaded.getvalue().decode("utf-8")),
                default_name=os.path.splitext(uploaded.name)[0] or "Projet importé",
            )
            if not imported:
                st.warning("Le fichier ne contient aucun projet à importer")
            else:
                created_projects = []
                total_circuits = 0
                for proj in imported:
                    circuits = [Circuit(**c) for c in proj["circuits"]]
                    pid = create_project(proj["name"])
                    save_project(pid, circuits, metadata=proj.get("metadata") or {})
                    created_projects.append({
                        "id": pid,
                        "name": proj["name"],
                        "count": len(circuits),
                    })
                    total_circuits += len(circuits)

                selected_project = max(created_projects, key=lambda project: (project["count"], project["id"]))
                _load_project_into_state(selected_project["id"])
                st.session_state.import_uploader_key += 1

                if total_circuits == 0:
                    st.warning(f"{len(created_projects)} projet(s) importé(s), mais aucun circuit n'a été trouvé dans le fichier.")
                else:
                    st.success(
                        f"{len(created_projects)} projet(s) importé(s), {total_circuits} circuit(s) chargés. "
                        f"Projet ouvert : {selected_project['name']} ({selected_project['count']} circuit(s))."
                    )
                st.rerun()
        except Exception as e:
            st.error(f"Erreur d'import : {e}")

st.title("⚡ Tableau électrique NF C 15-100")

# ========================
# 3 ONGLETS PRINCIPAUX
# ========================
tab_saisie, tab_circuits, tab_resultat = st.tabs(["🔧 Saisie", "📋 Circuits", "📊 Résultat"])

# ========================
# ONGLET 1 : SAISIE
# ========================
with tab_saisie:
    st.subheader("Mode")
    mode = st.radio("Mode", ["Manuel", "Automatique"], horizontal=True, label_visibility="collapsed")

    if mode == "Manuel":
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            nom = st.text_input("Nom", key="form_nom")
            type_c = st.selectbox("Type", ["prise", "eclairage", "specialise"], key="form_type")
            section = st.selectbox("Section (mm²)", [1.5, 2.5, 4.0, 6.0, 10.0], key="form_section")
        with col_f2:
            emplacement = st.text_input("Emplacement", placeholder="ex: Cuisine, Chambre 1…", key="form_emplacement")
            existant = st.checkbox("Circuit existant", key="form_existant")
            affecter_ligne = st.checkbox("Affecter à une ligne", key="form_assign_line")
            id_diff = st.number_input(
                "Ligne / ID différentiel",
                min_value=1,
                step=1,
                value=1,
                disabled=not affecter_ligne,
                key="form_id",
            )
            dj_existant = st.number_input("DJ existant (A)", min_value=0, value=0, step=1,
                                          help="0 = inconnu / non applicable")
            if type_c == "specialise":
                puissance_custom = st.number_input("Puissance (VA)", min_value=0, value=2000, step=100, key="form_puissance")
            else:
                puissance_custom = None
            if type_c in ("prise", "eclairage"):
                regle_ref = regles_circuit(Circuit(nom="", type=type_c, section=section))
                nb_max_ref = regle_ref["max"]
                nb_reel = st.number_input("Nb prises/points", min_value=0, max_value=20, value=nb_max_ref, step=1, key="form_nb")
            else:
                nb_max_ref = 0
                nb_reel = 0

        if st.button("➕ Ajouter", type="primary", use_container_width=True):
            if not nom:
                st.warning("Nom obligatoire")
            else:
                if type_c in ("prise", "eclairage"):
                    regle_ref = regles_circuit(Circuit(nom="", type=type_c, section=section))
                    nouveau = Circuit(
                        nom=nom, type=type_c, section=section,
                        puissance=regle_ref["puissance"],
                        emplacement=emplacement,
                        nb_max=nb_max_ref, nb_reel=nb_reel,
                        dj_existant=dj_existant if dj_existant > 0 else None,
                        existant=existant, id_diff=id_diff if affecter_ligne else None,
                    )
                else:
                    nouveau = Circuit(
                        nom=nom, type=type_c, section=section,
                        puissance=puissance_custom,
                        emplacement=emplacement,
                        dj_existant=dj_existant if dj_existant > 0 else None,
                        existant=existant, id_diff=id_diff if affecter_ligne else None,
                    )

                idx = next((i for i, c in enumerate(st.session_state.circuits) if c.nom.lower() == nom.lower() and c.emplacement == emplacement), None)
                if idx is not None:
                    st.session_state["pending_circuit"] = nouveau
                    st.session_state["pending_idx"] = idx
                    st.session_state["show_confirm"] = True
                else:
                    alertes = verifier_section_circuit(nouveau) + verifier_dj_circuit(nouveau)
                    for a in alertes:
                        if "❌" in a: st.error(a)
                        else: st.warning(a)
                    st.session_state.circuits.append(nouveau)
                    auto_save()
                    st.success(f"'{nom}' ajouté")
                    clear_derived_state()

        # Confirmation doublon
        if st.session_state.get("show_confirm"):
            pending = st.session_state["pending_circuit"]
            st.warning(f"⚠️ '{pending.nom}' [{pending.emplacement}] existe déjà. Remplacer ?")
            col_ok, col_ann = st.columns(2)
            with col_ok:
                if st.button("✅ Oui", key="btn_replace", use_container_width=True):
                    for a in verifier_section_circuit(pending) + verifier_dj_circuit(pending):
                        if "❌" in a: st.error(a)
                        else: st.warning(a)
                    st.session_state.circuits[st.session_state["pending_idx"]] = pending
                    auto_save()
                    st.success("Remplacé")
                    del st.session_state["pending_circuit"]; del st.session_state["pending_idx"]
                    del st.session_state["show_confirm"]
                    clear_derived_state()
                    st.rerun()
            with col_ann:
                if st.button("❌ Non", key="btn_cancel", use_container_width=True):
                    del st.session_state["pending_circuit"]; del st.session_state["pending_idx"]
                    del st.session_state["show_confirm"]
                    st.rerun()

    else:  # Automatique
        col_a, col_b = st.columns(2)
        with col_a:
            surface = st.number_input("Surface (m²)", min_value=9, value=50, step=1)
        with col_b:
            nb_chambres = st.number_input("Chambres", min_value=0, value=2, step=1)
        col_c, col_d, col_e = st.columns(3)
        with col_c:
            has_pac = st.checkbox("PAC (pompe à chaleur)")
        with col_d:
            has_ve = st.checkbox("Borne de recharge VE")
        with col_e:
            has_atelier = st.checkbox("Atelier / machines")
        if st.button("🏠 Générer logement", type="primary", use_container_width=True):
            circuits = generer_circuits_logement(surface, nb_chambres)
            if has_pac:
                circuits.append(Circuit(
                    nom="PAC", type="specialise",
                    section=4.0, puissance=3000,
                    emplacement="Local technique"
                ))
            if has_ve:
                circuits.append(Circuit(
                    nom="Borne VE", type="specialise",
                    section=6.0, puissance=7400,
                    emplacement="Extérieur"
                ))
            if has_atelier:
                circuits.append(Circuit(
                    nom="Atelier prises", type="prise",
                    section=2.5, puissance=3000,
                    emplacement="Atelier"
                ))
            st.session_state.circuits = circuits
            st.session_state.last_surface = surface
            st.session_state.last_chambres = nb_chambres
            st.session_state.last_has_pac = has_pac
            st.session_state.last_has_ve = has_ve
            st.session_state.last_has_atelier = has_atelier
            auto_save()
            clear_derived_state()
            st.success(f"{len(circuits)} circuits générés")

# ========================
# ONGLET 2 : CIRCUITS
# ========================
with tab_circuits:
    nb = len(st.session_state.circuits)
    if nb == 0:
        st.info("Aucun circuit ajouté")
    else:
        st.subheader(f"Circuits ({nb})")

        # Mode édition
        if "edit_idx" in st.session_state:
            edit_idx = st.session_state["edit_idx"]
            if 0 <= edit_idx < nb:
                c = st.session_state.circuits[edit_idx]
                st.subheader(f"✏️ Modifier : {c.nom}")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e_nom = st.text_input("Nom", value=c.nom, key="edit_nom")
                    e_type = st.selectbox("Type", ["prise", "eclairage", "specialise"],
                                          index=["prise", "eclairage", "specialise"].index(c.type), key="edit_type")
                    e_section = st.selectbox("Section (mm²)", [1.5, 2.5, 4.0, 6.0, 10.0],
                                             index=[1.5, 2.5, 4.0, 6.0, 10.0].index(c.section) if c.section in [1.5, 2.5, 4.0, 6.0, 10.0] else 1,
                                             key="edit_section")
                with col_e2:
                    e_emplacement = st.text_input("Emplacement", value=c.emplacement, key="edit_emplacement")
                    e_existant = st.checkbox("Circuit existant", value=c.existant, key="edit_existant")
                    e_affecter_ligne = st.checkbox(
                        "Affecter à une ligne",
                        value=c.id_diff is not None,
                        key="edit_assign_line",
                    )
                    e_id_diff = st.number_input(
                        "Ligne / ID différentiel",
                        min_value=1,
                        value=c.id_diff or 1,
                        disabled=not e_affecter_ligne,
                        key="edit_id_diff",
                    )
                    e_dj = st.number_input("DJ existant (A)", min_value=0, value=c.dj_existant or 0,
                                           key="edit_dj")
                    if e_type in ("prise", "eclairage"):
                        r_ref = regles_circuit(Circuit(nom="", type=e_type, section=e_section))
                        e_nb_reel = st.number_input("Nb prises/points", min_value=0, max_value=20,
                                                    value=c.nb_reel or r_ref["max"], key="edit_nb")
                    else:
                        e_puissance = st.number_input("Puissance (VA)", min_value=0, value=c.puissance or 2000, key="edit_puiss")
                        e_nb_reel = 0
                    r_ref = regles_circuit(Circuit(nom="", type=e_type, section=e_section))
                    e_nb_max = r_ref["max"]

                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Enregistrer", type="primary", use_container_width=True):
                        if e_type in ("prise", "eclairage"):
                            r_ref = regles_circuit(Circuit(nom="", type=e_type, section=e_section))
                            st.session_state.circuits[edit_idx] = Circuit(
                                nom=e_nom, type=e_type, section=e_section,
                                puissance=r_ref["puissance"],
                                emplacement=e_emplacement,
                                nb_max=e_nb_max, nb_reel=e_nb_reel,
                                dj_existant=e_dj if e_dj > 0 else None,
                                existant=e_existant, id_diff=e_id_diff if e_affecter_ligne else None,
                            )
                        else:
                            st.session_state.circuits[edit_idx] = Circuit(
                                nom=e_nom, type=e_type, section=e_section,
                                puissance=e_puissance,
                                emplacement=e_emplacement,
                                dj_existant=e_dj if e_dj > 0 else None,
                                existant=e_existant, id_diff=e_id_diff if e_affecter_ligne else None,
                            )
                        alertes = verifier_section_circuit(st.session_state.circuits[edit_idx]) + \
                                  verifier_dj_circuit(st.session_state.circuits[edit_idx])
                        for a in alertes:
                            if "❌" in a: st.error(a)
                            else: st.warning(a)
                        auto_save()
                        del st.session_state["edit_idx"]
                        clear_derived_state()
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Annuler", use_container_width=True):
                        del st.session_state["edit_idx"]
                        st.rerun()

                st.divider()

        # Liste des circuits
        for i, c in enumerate(st.session_state.circuits):
            if "edit_idx" in st.session_state and st.session_state["edit_idx"] == i:
                continue  # skip celui qu'on édite

            regle = regles_circuit(c)
            alertes = verifier_section_circuit(c) + verifier_dj_circuit(c)

            nb_label = ""
            if c.type in ("prise", "eclairage"):
                nb_label = f" | {c.nb_reel}/{c.nb_max} pts"
                if c.nb_reel > c.nb_max:
                    alertes.append(f"❌ Trop de points : {c.nb_reel}/{c.nb_max}")

            dj_label = f" | DJ {c.dj_existant}A" if c.dj_existant else f" | DJ {regle['disj']}A"
            if c.dj_existant and c.dj_existant != regle["disj"]:
                dj_label = f" | ⚠️DJ {c.dj_existant}A"

            statut = "✅" if not alertes else ("❌" if any("❌" in a for a in alertes) else "⚠️")

            loc = f" [{c.emplacement}]" if c.emplacement else ""
            with st.expander(f"{statut} {c.nom}{loc} — DJ {regle['disj']}A | {regle['puissance']}VA{nb_label}"):
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.write(f"**Type :** {c.type}  |  **Section :** {c.section}mm²")
                    st.write(f"**DJ conseillé :** {regle['disj']}A{dj_label}")
                    if c.id_diff is not None:
                        st.write(f"**Ligne souhaitée :** ID {c.id_diff}")
                    if c.emplacement:
                        st.write(f"**Emplacement :** {c.emplacement}")
                    st.write(f"**Puissance :** {regle['puissance']}VA")
                    if nb_label:
                        st.write(f"**Points :** {c.nb_reel}/{c.nb_max}")
                with col_d2:
                    st.write(f"**Existant :** {'Oui' if c.existant else 'Non'}")
                    if c.existant:
                        st.write(f"**ID diff :** {c.id_diff}")
                    for a in alertes:
                        if "❌" in a: st.error(a)
                        else: st.warning(a)

                col_edit, col_move, col_del = st.columns(3)
                with col_edit:
                    if st.button("✏️ Modifier", key=f"edit_{i}", use_container_width=True):
                        st.session_state["edit_idx"] = i
                        st.rerun()
                with col_move:
                    if st.button("↪️ Nouvelle ligne", key=f"new_line_{i}", use_container_width=True):
                        next_id = max(
                            (circuit.id_diff or 0 for circuit in st.session_state.circuits),
                            default=0,
                        ) + 1
                        st.session_state.circuits[i].id_diff = next_id
                        auto_save()
                        recalculate_tableau_and_persist()
                        st.success(f"'{c.nom}' déplacé vers la ligne {next_id}.")
                        st.rerun()
                with col_del:
                    if st.button("🗑️ Supprimer", key=f"del_{i}", use_container_width=True):
                        st.session_state.circuits.pop(i)
                        auto_save()
                        clear_derived_state()
                        st.rerun()

        if st.button("🗑️ Tout supprimer", type="primary", use_container_width=True):
            st.session_state.circuits = []
            auto_save()
            clear_derived_state()
            st.rerun()

# ========================
# ONGLET 3 : RÉSULTAT
# ========================
with tab_resultat:
    if not st.session_state.circuits:
        st.info("Ajoutez des circuits d'abord")
    else:
        if st.button("⚡ Calculer", type="primary", use_container_width=True):
            recalculate_tableau_and_persist()

        tableau = st.session_state.tableau
        if tableau is None:
            st.info("Appuyez sur Calculer pour générer le tableau")
        else:
            # ========================
            # DIMENSIONNEMENT HEURISTIQUE (décisionnel)
            # ========================
            surface = st.session_state.get("last_surface")
            nb_chambres = st.session_state.get("last_chambres")

            sizing = compute_sizing_decision(
                tableau,
                surface=surface,
                nb_chambres=nb_chambres,
            )

            st.subheader("Dimensionnement conseillé")
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                st.metric("Abonnement", f"{sizing['subscription']} {sizing['phase']}")
            with col_h2:
                st.metric("Profil", sizing["profile_label"])
            with col_h3:
                st.metric("Disjoncteur EDF", sizing["calibre_edf"])

            st.info(f"Raison : {sizing['justification']}")

            if sizing["phase"] == "triphasé":
                st.warning("🔌 Alimentation triphasée recommandée")
            else:
                st.success(f"✅ Alimentation monophasée ({sizing['subscription']})")

            # ========================
            # DÉTAILS PUISSANCE (informatif)
            # ========================
            with st.expander("Détails puissance (informatif — non décisionnel)"):
                p_diag = sizing["power_diagnostic"]
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.metric("Puissance théorique installée", f"{p_diag['total_theoretical']} VA")
                with col_p2:
                    st.metric("Charge estimée (foisonnement)", f"{p_diag['total_estimated']} VA")

                if p_diag["details"]:
                    st.dataframe(
                        pd.DataFrame(p_diag["details"]),
                        column_config={
                            "nom": "Circuit",
                            "puissance": "Puissance (VA)",
                            "coeff": "Coeff",
                            "contribution": "Estimé (VA)",
                        },
                        width="stretch",
                        hide_index=True,
                    )

                st.caption("Ces valeurs sont fournies à titre indicatif. "
                           "Le dimensionnement réel est basé sur les heuristiques métier ci-dessus.")

            st.divider()

            # ========================
            # LISTE DES ID
            # ========================
            st.subheader("Détail des ID")
            col_line_1, col_line_2 = st.columns(2)
            with col_line_1:
                if st.button("🔢 Renuméroter les lignes", use_container_width=True):
                    persist_tableau_line_assignments(tableau, renumber=True)
                    st.success("Les lignes ont été renumérotées.")
                    st.rerun()
            with col_line_2:
                if st.button("🧷 Figer la répartition actuelle", use_container_width=True):
                    persist_tableau_line_assignments(tableau)
                    st.success("La répartition actuelle a été conservée.")
                    st.rerun()
            CALIBRES_ID = ["25A", "40A", "63A", "80A", "100A"]
            TYPES_ID = ["AC", "A"]
            for id_inter, inter in sorted(tableau.items()):
                auto_cal = sizing["ids"][id_inter]["calibre"]
                cal_key = f"caliber_{id_inter}"
                type_key = f"inter_type_{id_inter}"
                if cal_key not in st.session_state:
                    st.session_state[cal_key] = auto_cal
                if type_key not in st.session_state:
                    st.session_state[type_key] = inter.type
                idx = CALIBRES_ID.index(st.session_state[cal_key]) if st.session_state[cal_key] in CALIBRES_ID else CALIBRES_ID.index(auto_cal)
                type_idx = TYPES_ID.index(st.session_state[type_key]) if st.session_state[type_key] in TYPES_ID else TYPES_ID.index(inter.type)
                p = puissance_inter(inter)

                with st.expander(f"ID {id_inter} — Type {inter.type} — {st.session_state[cal_key]} — {p}VA"):
                    col_type, col_cal, _ = st.columns([1, 1, 3])
                    with col_type:
                        st.selectbox(
                            "Type",
                            TYPES_ID,
                            index=type_idx,
                            key=type_key,
                            on_change=persist_current_id_preferences,
                        )
                    with col_cal:
                        st.selectbox(
                            "Calibre",
                            CALIBRES_ID,
                            index=idx,
                            key=cal_key,
                            on_change=persist_current_id_preferences,
                        )
                    alertes = analyser_inter(inter)
                    for a in alertes:
                        if "🚨" in a: st.error(a)
                        elif "⚠️" in a or "⚡" in a: st.warning(a)
                        else: st.info(a)

                    lines = []
                    for c in inter.circuits:
                        r = regles_circuit(c)
                        dj = f"{c.dj_existant}A" if c.dj_existant else f"{r['disj']}A"
                        lines.append({"Circuit": c.nom, "Empl.": c.emplacement, "Disj.": dj, "Conseillé": f"{r['disj']}A", "VA": r["puissance"]})
                    if lines:
                        st.dataframe(pd.DataFrame(lines), width="stretch", hide_index=True)
                    else:
                        st.write("Aucun circuit")

            # ========================
            # CONTRÔLES MÉTIER
            # ========================
            st.divider()
            st.subheader("🔍 Contrôles métier")

            warnings = generate_warnings(tableau)
            reserve_info = compute_reserve_info(tableau)

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Modules DIN utilisés", reserve_info["used"])
            with col_r2:
                st.metric("Modules restants", reserve_info["remaining"])
            with col_r3:
                status_res = "✅" if reserve_info["reserve_ok"] else "⚠️"
                st.metric("Réserve", f"{status_res} {'OK' if reserve_info['reserve_ok'] else 'Faible'}")

            if not warnings:
                st.success("✅ Aucune alerte métier")
            else:
                errors = [w for w in warnings if w["niveau"] == "error"]
                warns = [w for w in warnings if w["niveau"] == "warning"]
                infos = [w for w in warnings if w["niveau"] == "info"]

                if errors:
                    st.error("**Erreurs**")
                    for w in errors:
                        ctx = f"[ID {w['inter']}] " if w['inter'] else ""
                        ctx += f"({w['circuit']})" if w['circuit'] else ""
                        st.error(f"🚨 {ctx} {w['message']}")
                if warns:
                    st.warning("**Avertissements**")
                    for w in warns:
                        ctx = f"[ID {w['inter']}] " if w['inter'] else ""
                        ctx += f"({w['circuit']})" if w['circuit'] else ""
                        st.warning(f"⚠️ {ctx} {w['message']}")
                if infos:
                    st.info("**Informations**")
                    for w in infos:
                        ctx = f"[ID {w['inter']}] " if w['inter'] else ""
                        ctx += f"({w['circuit']})" if w['circuit'] else ""
                        st.info(f"ℹ️ {ctx} {w['message']}")

            # ========================
            # GÉNÉRATION ÉTIQUETTES PDF
            # ========================
            st.divider()
            st.subheader("🏷️ Étiquettes")
            tab_preview, tab_pdf = st.tabs(["👁️ Aperçu HTML", "📄 PDF"])

            with tab_preview:
                st.caption("Aperçu rapide des étiquettes sans téléchargement.")
                st.markdown(render_labels_preview(tableau), unsafe_allow_html=True)

            with tab_pdf:
                if st.button("🖨️ Générer étiquettes PDF", use_container_width=True):
                    try:
                        safe_name = "_".join(st.session_state.project_name.split()) or "projet"
                        st.session_state.labels_pdf_bytes = generer_pdf_etiquettes_bytes(tableau)
                        st.session_state.labels_pdf_name = f"etiquettes_{safe_name}.pdf"
                        st.success("PDF généré avec succès")
                    except ImportError:
                        st.error("reportlab requis : pip install reportlab")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

                if st.session_state.get("labels_pdf_bytes"):
                    st.download_button(
                        label="📥 Télécharger le PDF",
                        data=st.session_state["labels_pdf_bytes"],
                        file_name=st.session_state.get("labels_pdf_name", "etiquettes.pdf"),
                        mime="application/pdf",
                        use_container_width=True,
                    )
