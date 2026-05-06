import streamlit as st
import pandas as pd
from core.models import Circuit
from core.engine import (
    generer_tableau,
    puissance_inter,
    calibre_inter,
    generer_circuits_logement,
    analyser_inter,
)
from core.rules import regles_circuit, verifier_section_circuit, verifier_dj_circuit
from core.labels import generer_pdf_etiquettes
import json
import os

DEFAULT_FILE = "circuits.json"
STATE_FILE = ".last_file"


def sauver_circuits(circuits, fichier):
    data = [vars(c) for c in circuits]
    with open(fichier, "w") as f:
        json.dump(data, f, indent=2)


def charger_circuits(fichier):
    with open(fichier, "r") as f:
        data = json.load(f)
    return [Circuit(**c) for c in data]


def remember_file(fichier):
    with open(STATE_FILE, "w") as f:
        f.write(fichier)


def last_file():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    return DEFAULT_FILE


# ========================
# INIT
# ========================
st.set_page_config(page_title="⚡ Tableau électrique", layout="wide")

# Fichier courant
if "current_file" not in st.session_state:
    st.session_state.current_file = last_file()

# Chargement auto au démarrage
if "circuits" not in st.session_state:
    if os.path.exists(st.session_state.current_file):
        try:
            st.session_state.circuits = charger_circuits(st.session_state.current_file)
        except Exception:
            st.session_state.circuits = []
    else:
        st.session_state.circuits = []
if "tableau" not in st.session_state:
    st.session_state.tableau = None


def auto_save():
    """Sauvegarde automatique dans le fichier courant."""
    if st.session_state.circuits:
        sauver_circuits(st.session_state.circuits, st.session_state.current_file)
        remember_file(st.session_state.current_file)


# ========================
# SIDEBAR : gestion fichiers
# ========================
with st.sidebar:
    st.header("📁 Fichiers")

    fichier = st.text_input("Fichier", value=st.session_state.current_file, key="file_input")
    st.session_state.current_file = fichier

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🆕 New", use_container_width=True):
            st.session_state.circuits = []
            st.session_state.tableau = None
            st.session_state.current_file = DEFAULT_FILE
            st.rerun()
    with col_btn2:
        if st.button("📂 Open", use_container_width=True):
            if os.path.exists(fichier):
                try:
                    st.session_state.circuits = charger_circuits(fichier)
                    st.session_state.tableau = None
                    remember_file(fichier)
                    st.success(f"Chargé : {fichier}")
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                st.warning("Fichier introuvable")

    if st.button("💾 Save", use_container_width=True, type="primary"):
        sauver_circuits(st.session_state.circuits, fichier)
        remember_file(fichier)
        st.success(f"Sauvé : {fichier}")

    st.caption(f"Actif : {st.session_state.current_file}")

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
            id_diff = st.number_input("ID différentiel", min_value=1, step=1, key="form_id") if existant else None
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
                        existant=existant, id_diff=id_diff if existant else None,
                    )
                else:
                    nouveau = Circuit(
                        nom=nom, type=type_c, section=section,
                        puissance=puissance_custom,
                        emplacement=emplacement,
                        dj_existant=dj_existant if dj_existant > 0 else None,
                        existant=existant, id_diff=id_diff if existant else None,
                    )

                idx = next((i for i, c in enumerate(st.session_state.circuits) if c.nom.lower() == nom.lower()), None)
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
                    st.session_state.tableau = None

        # Confirmation doublon
        if st.session_state.get("show_confirm"):
            pending = st.session_state["pending_circuit"]
            st.warning(f"⚠️ '{pending.nom}' existe déjà. Remplacer ?")
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
                    st.session_state.tableau = None
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
        if st.button("🏠 Générer logement", type="primary", use_container_width=True):
            st.session_state.circuits = generer_circuits_logement(surface, nb_chambres)
            auto_save()
            st.session_state.tableau = None
            st.success(f"{len(st.session_state.circuits)} circuits générés")

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
                    e_id_diff = st.number_input("ID différentiel", min_value=1, value=c.id_diff or 1,
                                                disabled=not c.existant, key="edit_id_diff")
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
                                existant=e_existant, id_diff=e_id_diff if e_existant else None,
                            )
                        else:
                            st.session_state.circuits[edit_idx] = Circuit(
                                nom=e_nom, type=e_type, section=e_section,
                                puissance=e_puissance,
                                emplacement=e_emplacement,
                                dj_existant=e_dj if e_dj > 0 else None,
                                existant=e_existant, id_diff=e_id_diff if e_existant else None,
                            )
                        alertes = verifier_section_circuit(st.session_state.circuits[edit_idx]) + \
                                  verifier_dj_circuit(st.session_state.circuits[edit_idx])
                        for a in alertes:
                            if "❌" in a: st.error(a)
                            else: st.warning(a)
                        auto_save()
                        del st.session_state["edit_idx"]
                        st.session_state.tableau = None
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

            with st.expander(f"{statut} {c.nom} — DJ {regle['disj']}A | {regle['puissance']}VA{nb_label}"):
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.write(f"**Type :** {c.type}  |  **Section :** {c.section}mm²")
                    st.write(f"**DJ conseillé :** {regle['disj']}A{dj_label}")
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

                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️ Modifier", key=f"edit_{i}", use_container_width=True):
                        st.session_state["edit_idx"] = i
                        st.rerun()
                with col_del:
                    if st.button("🗑️ Supprimer", key=f"del_{i}", use_container_width=True):
                        st.session_state.circuits.pop(i)
                        auto_save()
                        st.session_state.tableau = None
                        st.rerun()

        if st.button("🗑️ Tout supprimer", type="primary", use_container_width=True):
            st.session_state.circuits = []
            auto_save()
            st.session_state.tableau = None
            st.rerun()

# ========================
# ONGLET 3 : RÉSULTAT
# ========================
with tab_resultat:
    if not st.session_state.circuits:
        st.info("Ajoutez des circuits d'abord")
    else:
        if st.button("⚡ Calculer", type="primary", use_container_width=True):
            st.session_state.tableau = generer_tableau(st.session_state.circuits)

        tableau = st.session_state.tableau
        if tableau is None:
            st.info("Appuyez sur Calculer pour générer le tableau")
        else:
            # Synthèse en haut
            p_tot = sum(puissance_inter(inter) for inter in tableau.values())
            courant_tot = p_tot / 230

            st.subheader("Synthèse")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.metric("ID", len(tableau))
            with col_s2:
                st.metric("Puissance", f"{p_tot} VA")
            st.write(f"Courant total : {courant_tot:.1f} A")

            if courant_tot <= 30:
                st.success("✅ Abonnement 6 kVA (30A)")
            elif courant_tot <= 45:
                st.info("ℹ️ Abonnement 9 kVA (45A)")
            elif courant_tot <= 60:
                st.warning("⚡ Abonnement 12 kVA (60A)")
            else:
                st.error("🔌 Triphasé recommandé")

            st.divider()

            # Liste des IDs avec expanders
            st.subheader("Détail des ID")
            for id_inter, inter in sorted(tableau.items()):
                cal = calibre_inter(inter)
                p = puissance_inter(inter)

                with st.expander(f"ID {id_inter} — Type {inter.type} — {cal} — {p}VA"):
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
            # GÉNÉRATION ÉTIQUETTES PDF
            # ========================
            st.divider()
            st.subheader("🏷️ Étiquettes")
            if st.button("🖨️ Générer étiquettes PDF", use_container_width=True):
                try:
                    pdf_file = generer_pdf_etiquettes(tableau)
                    with open(pdf_file, "rb") as f:
                        st.download_button(
                            label="📥 Télécharger le PDF",
                            data=f,
                            file_name=pdf_file,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    st.success("PDF généré avec succès")
                except ImportError:
                    st.error("reportlab requis : pip install reportlab")
                except Exception as e:
                    st.error(f"Erreur : {e}")
