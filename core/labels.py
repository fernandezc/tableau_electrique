from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_PATH = os.path.join(_BASE_DIR, "assets", "fonts", "DejaVuSans.ttf")
_ICONS_DIR = os.path.join(_BASE_DIR, "assets", "icons")

if os.path.exists(_FONT_PATH):
    pdfmetrics.registerFont(TTFont("DejaVu", _FONT_PATH))
    _FONT = "DejaVu"
else:
    _FONT = "Helvetica"

LARGEUR_MODULE = 18 * mm
LARGEUR_ID = 35 * mm
HAUTEUR = 25 * mm
ICON_SIZE = 8 * mm

_ZONE_ICON = 8 * mm
_ZONE_NOM = 10 * mm
_ZONE_EMPL = 5 * mm
_PAD_H = 1.5 * mm


def _icon_path(type_circuit, nom=""):
    nom_lower = nom.lower()
    if "plaque" in nom_lower or "cuisson" in nom_lower:
        f = "plaque.png"
    elif "lave" in nom_lower or "seche" in nom_lower:
        f = "lave.png"
    elif "chauffe" in nom_lower or "eau" in nom_lower:
        f = "eau.png"
    elif "clim" in nom_lower:
        f = "clim.png"
    elif type_circuit == "prise":
        f = "prise.png"
    elif type_circuit == "eclairage":
        f = "eclairage.png"
    else:
        f = "default.png"
    p = os.path.join(_ICONS_DIR, f)
    return p if os.path.exists(p) else None


def wrap_text_by_width(text, font_name, font_size, max_width):
    words = []
    for token in text.split():
        if '-' in token:
            parts = token.split('-')
            for i, part in enumerate(parts):
                if part:
                    words.append(part + '-' if i < len(parts) - 1 else part)
        else:
            words.append(token)

    lines, current = [], ""
    for w in words:
        if current:
            if current.endswith('-'):
                test = current + w
            else:
                test = current + " " + w
        else:
            test = w
        if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
            if len(lines) >= 2:
                break
    if current and len(lines) < 2:
        lines.append(current)
    return lines[:2]


def _circuit_cell(c):
    avail = LARGEUR_MODULE - 2 * _PAD_H

    icon = _icon_path(c.type, c.nom)
    if icon:
        img = Image(icon, width=ICON_SIZE, height=ICON_SIZE)
        img.hAlign = "CENTER"
        icon_content = img
    else:
        icon_content = ""

    style_nom = ParagraphStyle("n", alignment=TA_CENTER, fontSize=7, leading=8,
                               fontName=_FONT)
    nom_lines = wrap_text_by_width(c.nom.upper(), _FONT, 7, avail)
    nom_content = Paragraph("<b>" + "<br/>".join(nom_lines) + "</b>", style_nom)

    if c.emplacement:
        style_empl = ParagraphStyle("e", alignment=TA_CENTER, fontSize=5.2, leading=6,
                                    fontName=_FONT, textColor=colors.HexColor("#777777"))
        empl_lines = wrap_text_by_width(c.emplacement.upper(), _FONT, 5.2, avail)
        empl_content = Paragraph("<br/>".join(empl_lines), style_empl)
    else:
        empl_content = ""

    cell = Table(
        [[icon_content], [nom_content], [empl_content]],
        colWidths=[LARGEUR_MODULE],
        rowHeights=[_ZONE_ICON, _ZONE_NOM, _ZONE_EMPL]
    )
    cell.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), _PAD_H),
        ("RIGHTPADDING", (0, 0), (-1, -1), _PAD_H),
    ]))
    return cell


def _inter_cell(inter):
    avail = LARGEUR_ID - 2 * _PAD_H

    s_id = ParagraphStyle("id", alignment=TA_CENTER, fontSize=11, leading=13,
                          fontName=_FONT)
    id_lines = wrap_text_by_width("ID %s" % inter.id, _FONT, 11, avail)
    id_content = Paragraph("<b>" + "<br/>".join(id_lines) + "</b>", s_id)

    s_type = ParagraphStyle("tp", alignment=TA_CENTER, fontSize=7, leading=8.5,
                            fontName=_FONT, textColor=colors.HexColor("#555555"))
    type_lines = wrap_text_by_width("TYPE %s" % inter.type.upper(), _FONT, 7, avail)
    type_content = Paragraph("<br/>".join(type_lines), s_type)

    h_id = 14 * mm
    h_type = HAUTEUR - h_id
    cell = Table(
        [[id_content], [type_content]],
        colWidths=[LARGEUR_ID],
        rowHeights=[h_id, h_type]
    )
    cell.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), _PAD_H),
        ("RIGHTPADDING", (0, 0), (-1, -1), _PAD_H),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F0F0F0")),
    ]))
    return cell


def generer_pdf_etiquettes(tableau, filename="etiquettes.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            topMargin=10*mm, bottomMargin=10*mm,
                            leftMargin=10*mm, rightMargin=10*mm)
    elements = []

    for id_inter, inter in sorted(tableau.items()):
        if not inter.circuits:
            continue

        row = [_inter_cell(inter)]
        for c in inter.circuits:
            row.append(_circuit_cell(c))

        cols = [LARGEUR_ID] + [LARGEUR_MODULE] * len(inter.circuits)
        t = Table([row], colWidths=cols, rowHeights=[HAUTEUR])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#333333")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 2*mm))

    doc.build(elements)
    return filename
