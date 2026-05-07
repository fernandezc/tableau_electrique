# Tableau Électrique

Application Streamlit pour la conception et le contrôle de tableaux électriques conformément à la norme NF C 15-100.

## Fonctionnalités

- Saisie manuelle ou génération auto des circuits
- Répartition intelligente par interdifférentiels
- Vérifications métier (sections, types, charges)
- Génération d'étiquettes DIN au format PDF
- Contrôles NF C 15-100

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

## Structure

- `app.py` : Interface Streamlit
- `core/models.py` : Modèles de données
- `core/engine.py` : Logique de calcul et génération
- `core/rules.py` : Règles NF C 15-100
- `core/labels.py` : Génération d'étiquettes PDF
- `assets/` : Polices et icônes
