from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from perurecetas_core import catalogar_dataset


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = OUTPUT_DIR / "assets"
DOCX_PATH = OUTPUT_DIR / "informe_perurecetas.docx"
PDF_PATH = OUTPUT_DIR / "informe_perurecetas.pdf"
ARCH_PATH = ASSETS_DIR / "arquitectura_perurecetas.png"


PROJECT_TITLE = "Agente de Recetas y Nutricion Peruana con RAG, FAISS y API externa"
PROJECT_NAME = "PeruRecetas"
INTEGRANTES = [
    "GIOVANNI FRANCO LUCA BARCENA ALDAVE",
    "DIEGO ALONSO MERINO CASTAÑEDA",
]
DOCENTE = "EDUARDO YAURI LOZANO"
CURSO = "Redes Neuronales Artificiales"
FECHA = "04/07/2026"


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def crear_diagrama() -> None:
    ensure_dirs()
    width, height = 1400, 760
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 34)
        font_box = ImageFont.truetype("arial.ttf", 22)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_title = ImageFont.load_default()
        font_box = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((50, 35), "Arquitectura de PeruRecetas", fill=(15, 37, 69), font=font_title)

    boxes = [
        ((70, 140, 330, 260), "Usuario\nNotebook / Streamlit"),
        ((430, 90, 710, 210), "Agente\nMemoria + Orquestacion"),
        ((830, 80, 1220, 200), "Gemini LLM\nRespuesta final"),
        ((430, 300, 710, 430), "Tools Python\nRecetas y sustituciones"),
        ((830, 290, 1220, 420), "API externa\nComida peruana por region"),
        ((430, 520, 710, 660), "TXT etiquetados\nDataset RAG"),
        ((830, 520, 1220, 660), "FAISS + Embeddings\nRecuperacion semantica"),
    ]
    for rect, label in boxes:
        draw.rounded_rectangle(rect, radius=18, outline=(46, 116, 181), width=3, fill=(242, 246, 249))
        lines = label.split("\n")
        y = rect[1] + 28
        for line in lines:
            draw.text((rect[0] + 24, y), line, fill=(20, 30, 40), font=font_box if y == rect[1] + 28 else font_small)
            y += 32

    arrows = [
        ((330, 200), (430, 150)),
        ((710, 150), (830, 140)),
        ((570, 210), (570, 300)),
        ((710, 365), (830, 355)),
        ((570, 520), (570, 430)),
        ((710, 590), (830, 590)),
        ((1025, 520), (1025, 420)),
        ((1025, 290), (1025, 200)),
    ]
    for start, end in arrows:
        draw.line([start, end], fill=(31, 78, 121), width=4)
        x, y = end
        draw.polygon([(x, y), (x - 12, y - 8), (x - 8, y + 12)], fill=(31, 78, 121))

    img.save(ARCH_PATH)


def set_run(run, size=None, bold=None, color=None):
    run.font.name = "Calibri"
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_heading(doc: Document, text: str, level: int = 1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        set_run(run, color="2E74B5" if level <= 2 else "1F4D78")
    return p


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item)


def crear_docx() -> None:
    crear_diagrama()
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(11)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(PROJECT_TITLE)
    set_run(run, size=20, bold=True, color="0B2545")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(PROJECT_NAME)
    set_run(run, size=16, bold=True, color="2E74B5")

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Curso: {CURSO}\n").bold = True
    meta.add_run(f"Docente: {DOCENTE}\n")
    meta.add_run("Integrantes:\n")
    for integrante in INTEGRANTES:
        meta.add_run(f"- {integrante}\n")
    meta.add_run(f"Fecha de entrega: {FECHA}")
    doc.add_page_break()

    add_heading(doc, "1. Resumen ejecutivo", 1)
    doc.add_paragraph(
        "PeruRecetas es un agente de recetas y nutricion peruana que combina un LLM Gemini, "
        "memoria conversacional, tools de Python, recuperacion aumentada por generacion "
        "(RAG) con FAISS y una API externa de platos peruanos."
    )

    add_heading(doc, "2. Objetivo del proyecto", 1)
    doc.add_paragraph(
        "Implementar un agente AI aplicado a gastronomia peruana y nutricion basica, "
        "cumpliendo el flujo solicitado: agente LLM, memoria, tools, RAG y pruebas."
    )

    add_heading(doc, "3. Arquitectura", 1)
    doc.add_picture(str(ARCH_PATH), width=Inches(6.2))
    doc.add_paragraph(
        "El usuario interactua desde el notebook o Streamlit. El agente consulta memoria, "
        "tools locales, FAISS/RAG y la API externa antes de construir el prompt enviado al LLM."
    )

    add_heading(doc, "4. Modelos y librerias utilizadas", 1)
    add_bullets(
        doc,
        [
            "Gemini: modelo LLM y embeddings para representar semanticamente los documentos.",
            "AIsuite: cliente unificado para llamadas a modelos; se deja fallback al SDK oficial de Gemini.",
            "FAISS: base vectorial para busqueda semantica de chunks extraidos de TXT etiquetados.",
            "TXT etiquetados: recetas delimitadas con campos de ingredientes, preparacion y etiquetas.",
            "Streamlit: interfaz web para chat, consulta API, RAG e historial.",
            "requests/urllib: consulta HTTP a la API externa de comida peruana.",
        ],
    )

    add_heading(doc, "5. Dataset RAG", 1)
    catalogo = catalogar_dataset()
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Archivo"
    hdr[1].text = "Ruta"
    hdr[2].text = "Tamano bytes"
    hdr[3].text = "Recetas"
    for item in catalogo:
        row = table.add_row().cells
        row[0].text = str(item["archivo"])
        row[1].text = str(item["ruta"])
        row[2].text = str(item["tamano_bytes"])
        row[3].text = str(item.get("recetas", "No calculado"))

    add_heading(doc, "6. Implementacion", 1)
    add_bullets(
        doc,
        [
            "Memoria: historial de mensajes de usuario y asistente dentro de AgenteRecetas.",
            "Tools: recomendacion por ingrediente, sustitucion de ingredientes y consulta API.",
            "RAG: lectura de TXT etiquetados, chunking, embeddings Gemini, normalizacion e indice FAISS.",
            "API externa: consulta de platos por region, ingrediente, tipo y busqueda libre.",
            "Interfaz: PeruRecetas en Streamlit con chat, API, RAG e historial.",
        ],
    )

    add_heading(doc, "7. Pruebas propuestas", 1)
    add_bullets(
        doc,
        [
            "Validar que existen al menos 5 TXT y recetas etiquetadas para el RAG.",
            "Validar normalizacion de regiones para la API.",
            "Validar tool de sustitucion de ingredientes.",
            "Validar chunking de textos para el RAG.",
            "Validar API externa, recuperacion FAISS y memoria del agente en pruebas completas.",
        ],
    )

    add_heading(doc, "8. Cumplimiento del enunciado", 1)
    cumplimiento = [
        ("Agente LLM", "Cubierto con Gemini y clase AgenteRecetas."),
        ("Memoria", "Cubierto con historial conversacional."),
        ("Tools", "Cubierto con tres tools: recetas, sustituciones y API externa."),
        ("RAG", "Cubierto con FAISS y cinco TXT etiquetados del directorio recetarios."),
        ("Mejoramiento de tools", "Cubierto con consulta de informacion desde API externa."),
        ("Pruebas", "Cubierto con run_pruebas.py y celdas de prueba en el notebook."),
    ]
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Requisito"
    table.rows[0].cells[1].text = "Estado"
    for req, estado in cumplimiento:
        row = table.add_row().cells
        row[0].text = req
        row[1].text = estado

    add_heading(doc, "9. Conclusiones", 1)
    doc.add_paragraph(
        "El proyecto queda preparado para demostrar un agente autonomo aplicado al dominio "
        "gastronomico peruano. La arquitectura separa datos, recuperacion, herramientas, "
        "modelo e interfaz, lo que facilita la exposicion y la ejecucion en vivo."
    )

    add_heading(doc, "10. Fuentes", 1)
    add_bullets(
        doc,
        [
            "API de comida peruana: https://api-comida-peru.luisgagocasas.com/",
            "Dataset local: cinco TXT etiquetados ubicados en recetarios/.",
            "Enunciado del proyecto: RNA_proyecto_enunciado 26-1.pdf.",
        ],
    )

    doc.save(DOCX_PATH)


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def crear_pdf() -> None:
    crear_diagrama()
    font_regular = "Helvetica"
    font_bold = "Helvetica-Bold"
    arial = Path("C:/Windows/Fonts/arial.ttf")
    arial_bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if arial.exists() and arial_bold.exists():
        pdfmetrics.registerFont(TTFont("Arial", str(arial)))
        pdfmetrics.registerFont(TTFont("Arial-Bold", str(arial_bold)))
        font_regular = "Arial"
        font_bold = "Arial-Bold"

    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_regular
    styles.add(
        ParagraphStyle(
            name="TitleBlue",
            parent=styles["Title"],
            textColor=colors.HexColor("#0B2545"),
            fontName=font_bold,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Blue",
            parent=styles["Heading1"],
            textColor=colors.HexColor("#2E74B5"),
            fontName=font_bold,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            leading=14,
            spaceAfter=8,
            fontName=font_regular,
        )
    )

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    story = []
    story.append(p(PROJECT_TITLE, styles["TitleBlue"]))
    story.append(p(PROJECT_NAME, styles["Heading2"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(p(f"<b>Curso:</b> {CURSO}", styles["Body"]))
    story.append(p(f"<b>Docente:</b> {DOCENTE}", styles["Body"]))
    story.append(p("<b>Integrantes:</b><br/>" + "<br/>".join(INTEGRANTES), styles["Body"]))
    story.append(p(f"<b>Fecha de entrega:</b> {FECHA}", styles["Body"]))
    story.append(PageBreak())

    sections = [
        (
            "1. Resumen ejecutivo",
            "PeruRecetas es un agente de recetas y nutricion peruana que combina Gemini, memoria conversacional, tools de Python, RAG con FAISS y una API externa de platos peruanos.",
        ),
        (
            "2. Objetivo del proyecto",
            "Implementar un agente AI aplicado a gastronomia peruana y nutricion basica, cumpliendo el flujo solicitado: agente LLM, memoria, tools, RAG y pruebas.",
        ),
    ]
    for title, body in sections:
        story.append(p(title, styles["H1Blue"]))
        story.append(p(body, styles["Body"]))

    story.append(p("3. Arquitectura", styles["H1Blue"]))
    story.append(RLImage(str(ARCH_PATH), width=6.2 * inch, height=3.36 * inch))
    story.append(Spacer(1, 0.12 * inch))

    story.append(p("4. Modelos y librerias utilizadas", styles["H1Blue"]))
    bullets = [
        "Gemini: LLM y embeddings.",
        "AIsuite: cliente unificado con fallback al SDK de Gemini.",
        "FAISS: base vectorial del RAG.",
        "TXT etiquetados: lectura estructurada de recetas.",
        "Streamlit: interfaz web PeruRecetas.",
        "requests/urllib: consulta de API externa.",
    ]
    story.append(ListFlowable([ListItem(p(item, styles["Body"])) for item in bullets], bulletType="bullet"))

    story.append(p("5. Dataset RAG", styles["H1Blue"]))
    catalogo = catalogar_dataset()
    rows = [["Archivo", "Ruta", "Tamano", "Recetas"]]
    for item in catalogo:
        rows.append([
            item["archivo"],
            item["ruta"],
            str(item["tamano_bytes"]),
            str(item.get("recetas", "No calculado")),
        ])
    table = Table(rows, colWidths=[1.4 * inch, 2.4 * inch, 1.2 * inch, 0.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2CC")),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTNAME", (0, 1), (-1, -1), font_regular),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.15 * inch))

    story.append(p("6. Implementacion y pruebas", styles["H1Blue"]))
    impl = [
        "Memoria: historial conversacional en AgenteRecetas.",
        "Tools: recetas, sustituciones y consulta API.",
        "RAG: TXT etiquetados, chunking, embeddings Gemini y FAISS.",
        "Pruebas: dataset minimo, regiones, sustituciones, chunking, API, FAISS y memoria.",
    ]
    story.append(ListFlowable([ListItem(p(item, styles["Body"])) for item in impl], bulletType="bullet"))

    story.append(p("7. Cumplimiento del enunciado", styles["H1Blue"]))
    rows = [
        ["Requisito", "Estado"],
        ["Agente LLM", "Gemini + AgenteRecetas"],
        ["Memoria", "Historial de conversacion"],
        ["Tools", "Recetas, sustituciones y API externa"],
        ["RAG", "FAISS con cinco TXT etiquetados"],
        ["Mejoramiento", "Consulta de informacion de APIs"],
        ["Pruebas", "run_pruebas.py + notebook"],
    ]
    table = Table(rows, colWidths=[2.0 * inch, 4.2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2CC")),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTNAME", (0, 1), (-1, -1), font_regular),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)

    story.append(p("8. Fuentes", styles["H1Blue"]))
    refs = [
        "API de comida peruana: https://api-comida-peru.luisgagocasas.com/",
        "Dataset local: cinco TXT etiquetados ubicados en recetarios/.",
        "Enunciado del proyecto: RNA_proyecto_enunciado 26-1.pdf.",
    ]
    story.append(ListFlowable([ListItem(p(item, styles["Body"])) for item in refs], bulletType="bullet"))

    doc.build(story)


def main() -> None:
    ensure_dirs()
    crear_docx()
    crear_pdf()
    print(f"DOCX generado: {DOCX_PATH}")
    print(f"PDF generado: {PDF_PATH}")


if __name__ == "__main__":
    main()
