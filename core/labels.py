from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Spacer, Paragraph, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# === Chemins absolus vers les ressources ===
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_PATH = os.path.join(_BASE_DIR, "assets", "fonts", "DejaVuSans.ttf")
_ICONS_DIR = os.path.join(_BASE_DIR, "assets", "icons")

# Enregistrer la police (incluse dans le projet)
if os.path.exists(_FONT_PATH):
    pdfmetrics.registerFont(TTFont("DejaVu", _FONT_PATH))

LARGEUR_MODULE = 18 * mm
LARGEUR_ID = 35 * mm
HAUTEUR = 25 * mm
ICON_SIZE = 5 * mm


def _icone_circuit(type_circuit, nom=""):
    """Retourne le chemin absolu de l'icône selon le type de circuit."""
    nom_lower = nom.lower()
    if "plaque" in nom_lower or "cuisson" in nom_lower:
        fichier = "plaque.png"
    elif "lave" in nom_lower or "seche" in nom_lower:
        fichier = "lave.png"
    elif "chauffe" in nom_lower or "eau" in nom_lower:
        fichier = "eau.png"
    elif "clim" in nom_lower:
        fichier = "clim.png"
    elif type_circuit == "prise":
        fichier = "prise.png"
    elif type_circuit == "eclairage":
        fichier = "eclairage.png"
    else:
        fichier = "default.png"

    chemin = os.path.join(_ICONS_DIR, fichier)
    return chemin if os.path.exists(chemin) else None


def _cellule_inter(inter):
    font = "DejaVu" if os.path.exists(_FONT_PATH) else "Helvetica"
    txt = (
        u"<para align='center'>"
        u"<font name='{}' size='9'><b>ID {}</b></font>"
        u"<br/><font name='{}' size='7'>Type {}</font>"
        u"</para>"
    ).format(font, inter.id, font, inter.type)
    return Paragraph(
        txt,
        ParagraphStyle("id", alignment=TA_CENTER, fontSize=9, leading=10, fontName=font)
    )


def _cellule_circuit(c):
    """
    Crée le contenu d'une cellule circuit avec :
    - icône (image PNG) à gauche
    - nom (ligne 1) et emplacement (ligne 2) à droite
    """
    font = "DejaVu" if os.path.exists(_FONT_PATH) else "Helvetica"
    icon_path = _icone_circuit(c.type, c.nom)

    nom_court = c.nom[:14] if len(c.nom) > 14 else c.nom
    empl_court = (c.emplacement[:14] if c.emplacement and len(c.emplacement) > 14
                  else (c.emplacement or ""))

    # Texte : nom puis emplacement sur la ligne suivante
    lignes_texte = u"<font name='{}' size='8'>{}</font>".format(font, nom_court)
    if empl_court:
        lignes_texte += u"<br/><font name='{}' size='6'>{}</font>".format(font, empl_court)

    txt_para = Paragraph(
        lignes_texte,
        ParagraphStyle("circuit_txt", alignment=TA_CENTER, fontSize=8, leading=9, fontName=font)
    )

    if icon_path:
        img = Image(icon_path, width=ICON_SIZE, height=ICON_SIZE)
        # Table de 2 colonnes : icône | texte
        col1 = ICON_SIZE + 1 * mm
        col2 = LARGEUR_MODULE - col1 - 1 * mm
        inner = Table(
            [[img, txt_para]],
            colWidths=[col1, col2],
            rowHeights=[None]
        )
        inner.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return inner
    else:
        return txt_para


def generer_pdf_etiquettes(tableau, filename="etiquettes.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
    )

    elements = []

    for id_inter, inter in sorted(tableau.items()):
        if not inter.circuits:
            continue

        row_cells = [_cellule_inter(inter)]
        for c in inter.circuits:
            row_cells.append(_cellule_circuit(c))

        col_widths = [LARGEUR_ID] + [LARGEUR_MODULE] * len(inter.circuits)
        t = Table([row_cells], colWidths=col_widths, rowHeights=[HAUTEUR])
        t.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ])
        )
        elements.append(t)
        elements.append(Spacer(1, 3 * mm))

    doc.build(elements)
    return filename
