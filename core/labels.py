from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Spacer, Paragraph, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

_FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "fonts", "DejaVuSans.ttf")
_ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "icons")

if os.path.exists(_FONT_PATH):
    pdfmetrics.registerFont(TTFont("DejaVu", _FONT_PATH))

LARGEUR_MODULE = 18 * mm
LARGEUR_ID = 35 * mm
HAUTEUR = 25 * mm
ICON_SIZE = 8 * mm

_FONT = "DejaVu" if os.path.exists(_FONT_PATH) else "Helvetica"

_STYLE_NOM = ParagraphStyle("nom", alignment=TA_CENTER, fontSize=7.5, leading=9,
                            fontName=_FONT, spaceAfter=0, spaceBefore=0)
_STYLE_EMPL = ParagraphStyle("empl", alignment=TA_CENTER, fontSize=5.5, leading=7,
                              fontName=_FONT, textColor=colors.HexColor("#555555"),
                              spaceAfter=0, spaceBefore=0)


def _get_icon_path(type_circuit, nom=""):
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


def _build_icon(icon_path):
    if not icon_path:
        return None
    return Image(icon_path, width=ICON_SIZE, height=ICON_SIZE)


def _wrap_text_lines(text, max_width_chars=18):
    if len(text) <= max_width_chars:
        return [text]
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if len(test) <= max_width_chars:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines[:2]


def _build_label_text(nom, emplacement):
    parts = []
    nom_upper = nom.upper()
    lines = _wrap_text_lines(nom_upper, max_width_chars=18)
    for line in lines:
        parts.append(Paragraph(line, _STYLE_NOM))
    if emplacement:
        empl_upper = emplacement.upper()
        lines2 = _wrap_text_lines(empl_upper, max_width_chars=22)
        for line in lines2:
            parts.append(Paragraph(line, _STYLE_EMPL))
    return parts


def _build_vertical_block(icon, text_flow):
    flow = []
    if icon:
        icon_table = Table([[icon]], colWidths=[LARGEUR_MODULE - 2*mm])
        icon_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1*mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        flow.append(icon_table)
    for item in text_flow:
        flow.append(item)
    col_w = (LARGEUR_MODULE - 2*mm) if icon else (LARGEUR_MODULE - 2*mm)
    rows = [[f] for f in flow]
    inner = Table(rows, colWidths=[col_w])
    inner.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    outer = Table([[inner]], colWidths=[LARGEUR_MODULE], rowHeights=[HAUTEUR])
    outer.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F8F8F8")),
    ]))
    return outer


def _cellule_inter(inter):
    txt = (
        u"<para align='center'>"
        u"<font name='{}' size='9'><b>ID {}</b></font>"
        u"<br/><font name='{}' size='7'>Type {}</font>"
        u"</para>"
    ).format(_FONT, inter.id, _FONT, inter.type)
    para = Paragraph(txt, ParagraphStyle("id", alignment=TA_CENTER, fontSize=9,
                                         leading=10, fontName=_FONT))
    outer = Table([[para]], colWidths=[LARGEUR_ID], rowHeights=[HAUTEUR])
    outer.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 1*mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1*mm),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EEEEEE")),
    ]))
    return outer


def _cellule_circuit(c):
    icon_path = _get_icon_path(c.type, c.nom)
    icon = _build_icon(icon_path)
    text_flow = _build_label_text(c.nom, c.emplacement)
    return _build_vertical_block(icon, text_flow)


def generer_pdf_etiquettes(tableau, filename="etiquettes.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        topMargin=10*mm,
        bottomMargin=10*mm,
        leftMargin=10*mm,
        rightMargin=10*mm,
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
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
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
