# -*- coding: utf-8 -*-
"""Build the English two-layer paper in the IEEE two-column layout."""

import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_a import ABSTRACT, AFFILIATION, AUTHORS, AUTHOR_NOTE, BLOCKS_A, TITLE  # noqa: E402
from content_b import BLOCKS_B  # noqa: E402

FONT = "Times New Roman"
MONO = "Courier New"


def set_run_font(run, size=10, bold=False, italic=False, name=FONT, caps=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if caps:
        run.font.small_caps = True
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def add_rich_text(paragraph, text, size=10, bold=False, italic=False):
    parts = text.split("*")
    for i, part in enumerate(parts):
        if not part:
            continue
        run = paragraph.add_run(part)
        set_run_font(run, size=size, bold=bold, italic=(italic or i % 2 == 1))


def para(doc, text="", size=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.5,
         before=0, after=0, bold=False, italic=False, line=0.98):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Cm(indent) if indent else None
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if text:
        add_rich_text(p, text, size=size, bold=bold, italic=italic)
    return p


def set_columns(section, num=2, space=340):
    sect_pr = section._sectPr
    cols = sect_pr.xpath("./w:cols")[0]
    cols.set(qn("w:num"), str(num))
    cols.set(qn("w:space"), str(space))
    cols.set(qn("w:equalWidth"), "1")


def set_table_widths(table, widths_cm):
    total = int(sum(widths_cm) * 567)
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout"):
        for old in tbl_pr.findall(qn(tag)):
            tbl_pr.remove(old)
    w = OxmlElement("w:tblW")
    w.set(qn("w:w"), str(total))
    w.set(qn("w:type"), "dxa")
    tbl_pr.append(w)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    for i, cm in enumerate(widths_cm):
        table.columns[i].width = Cm(cm)
        for cell in table.columns[i].cells:
            cell.width = Cm(cm)


def add_table(doc, caption, header, rows, widths=None):
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(6)
    cap.paragraph_format.space_after = Pt(3)
    cap.paragraph_format.keep_with_next = True
    set_run_font(cap.add_run(caption), size=8, caps=True)

    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    table.alignment = 1
    table.autofit = False
    if widths is None:
        widths = [8.2 / len(header)] * len(header)
    set_table_widths(table, widths)

    for i, h in enumerate(header):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_run_font(p.add_run(h), size=8, bold=True)

    for row in rows:
        new_row = table.add_row()
        tr_pr = new_row._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
        cells = new_row.cells
        for i, value in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            set_run_font(p.add_run(str(value)), size=8)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)
    spacer.paragraph_format.line_spacing = 1.0


def add_figure(doc, path, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.first_line_indent = None
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(7.8))

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    cap.paragraph_format.space_before = Pt(0)
    cap.paragraph_format.space_after = Pt(6)
    cap.paragraph_format.first_line_indent = None
    set_run_font(cap.add_run(caption), size=8)


def build(out_path="paper_two_layer/XR_TwoLayer_EN.docx"):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.6)
    sec.top_margin = Cm(1.9)
    sec.bottom_margin = Cm(2.2)
    set_columns(sec, 1)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    set_run_font(p.add_run(TITLE), size=20, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_run_font(p.add_run(AUTHORS), size=10.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_run_font(p.add_run(AFFILIATION), size=9, italic=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    set_run_font(p.add_run(AUTHOR_NOTE), size=8, italic=True)

    body = doc.add_section(WD_SECTION.CONTINUOUS)
    body.page_width, body.page_height = Cm(21.0), Cm(29.7)
    body.left_margin = body.right_margin = Cm(1.6)
    body.top_margin = Cm(1.9)
    body.bottom_margin = Cm(2.2)
    set_columns(body, 2)

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = None
    set_run_font(p.add_run("Abstract—"), size=9, bold=True)
    set_run_font(p.add_run(ABSTRACT), size=9)

    blocks = BLOCKS_A + BLOCKS_B
    refs = [b for b in blocks if b[0] == "refs"]
    rest = [b for b in blocks if b[0] != "refs"]
    cut = next((i for i, b in enumerate(rest)
                if b[0] == "h1" and b[1].startswith("APPENDIX")), len(rest))
    blocks = rest[:cut] + refs + rest[cut:]

    appendix_started = False
    for block in blocks:
        kind = block[0]
        if kind == "h1":
            if block[1].startswith("APPENDIX") and not appendix_started:
                appendix_started = True
                app = doc.add_section(WD_SECTION.NEW_PAGE)
                app.page_width, app.page_height = Cm(21.0), Cm(29.7)
                app.left_margin = app.right_margin = Cm(1.6)
                app.top_margin = Cm(1.9)
                app.bottom_margin = Cm(2.2)
                set_columns(app, 2)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            set_run_font(p.add_run(block[1]), size=10, caps=True)
        elif kind == "h2":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            set_run_font(p.add_run(block[1]), size=10, italic=True)
        elif kind == "p":
            para(doc, block[1])
        elif kind == "fig":
            add_figure(doc, block[1], block[2])
        elif kind == "table":
            add_table(doc, block[1], block[2], block[3], block[4] if len(block) > 4 else None)
        elif kind == "refs":
            for i, ref in enumerate(block[1], 1):
                p = doc.add_paragraph()
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.left_indent = Cm(0.55)
                p.paragraph_format.first_line_indent = Cm(-0.55)
                p.paragraph_format.space_after = Pt(1)
                set_run_font(p.add_run(f"[{i}] "), size=7.5)
                set_run_font(p.add_run(ref), size=7.5)
        else:
            raise ValueError(kind)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    doc.save(out_path)
    print("saved", os.path.abspath(out_path))


if __name__ == "__main__":
    build()
