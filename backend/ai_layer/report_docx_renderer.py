"""
ai_layer/report_docx_renderer.py – Render báo cáo (HTML fragment) ra file .docx bằng python-docx.

Vì nguồn dữ liệu chính của báo cáo giờ là HTML (sinh trực tiếp từ LLM theo
report_generator_prompt.txt), renderer này PARSE HTML bằng BeautifulSoup rồi
build DOCX tương ứng — không còn đọc JSON blocks như thiết kế trước.

Hỗ trợ các tag HTML mà report_generator_prompt.txt yêu cầu LLM sử dụng:
  p, h2, h3, strong, table/thead/tbody/tr/th/td, ul/ol/li

Nguyên tắc áp dụng (tương đương khuyến nghị của docx skill, chuyển từ docx-js sang python-docx):
- Không tự chèn ký tự bullet unicode; dùng style "List Bullet" / "List Number" có sẵn của Word.
- Set độ rộng cột bảng rõ ràng (Inches), border mỏng màu xám nhạt.
- Font mặc định Times New Roman (văn bản hành chính VN thường dùng font này).
- <h2>/<h3> dùng style "Heading 1"/"Heading 2" có sẵn của Word để giữ outline đúng.
- Tiêu ngữ (CỘNG HÒA...) và <strong> với text-align:center được giữ center-align + bold.
"""
from __future__ import annotations

from io import BytesIO

from bs4 import BeautifulSoup, Tag
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

_BORDER_COLOR = "444444"
_HEADER_FILL = "F1F1F1"


def _is_centered(tag: Tag) -> bool:
    style = tag.get("style", "") or ""
    return "text-align:center" in style.replace(" ", "")


def _set_cell_border(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.makeelement(qn("w:tcBorders"), {})
    for edge in ("top", "left", "bottom", "right"):
        element = tc_pr.makeelement(qn(f"w:{edge}"), {
            qn("w:val"): "single",
            qn("w:sz"): "4",
            qn("w:space"): "0",
            qn("w:color"): _BORDER_COLOR,
        })
        borders.append(element)
    tc_pr.append(borders)


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): fill})
    tc_pr.append(shd)


def _add_paragraph_with_inline_formatting(document: Document, tag: Tag, style: str | None = None):
    """Thêm 1 paragraph, giữ định dạng <strong>/<b> bên trong (bold từng run riêng)."""
    paragraph = document.add_paragraph(style=style)
    if _is_centered(tag):
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if not tag.contents:
        paragraph.add_run(tag.get_text())
        return paragraph

    for child in tag.children:
        if isinstance(child, Tag) and child.name in ("strong", "b"):
            run = paragraph.add_run(child.get_text())
            run.bold = True
        elif isinstance(child, Tag) and child.name in ("em", "i"):
            run = paragraph.add_run(child.get_text())
            run.italic = True
        else:
            text = child.get_text() if isinstance(child, Tag) else str(child)
            if text.strip():
                paragraph.add_run(text)
    return paragraph


def _render_table(document: Document, table_tag: Tag) -> None:
    rows_data: list[list[str]] = []
    header_cells: list[str] = []

    thead = table_tag.find("thead")
    if thead:
        header_row = thead.find("tr")
        if header_row:
            header_cells = [cell.get_text(strip=True) for cell in header_row.find_all(["th", "td"])]

    tbody = table_tag.find("tbody") or table_tag
    for tr in tbody.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in tr.find_all(["td", "th"])]
        if cells and cells != header_cells:
            rows_data.append(cells)

    if not header_cells and not rows_data:
        return

    col_count = max(len(header_cells), max((len(r) for r in rows_data), default=0), 1)
    table = document.add_table(rows=0, cols=col_count)
    table.autofit = False
    col_width = Inches(6.3 / col_count)
    for col in table.columns:
        col.width = col_width

    if header_cells:
        header_row_obj = table.add_row()
        for index in range(col_count):
            cell = header_row_obj.cells[index]
            cell.text = header_cells[index] if index < len(header_cells) else ""
            cell.width = col_width
            _set_cell_border(cell)
            _set_cell_shading(cell, _HEADER_FILL)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True

    for row in rows_data:
        data_row = table.add_row()
        for index in range(col_count):
            cell = data_row.cells[index]
            cell.text = row[index] if index < len(row) else ""
            cell.width = col_width
            _set_cell_border(cell)

    document.add_paragraph()


def render_report_docx(html: str) -> bytes:
    """Parse HTML fragment báo cáo và render ra bytes của file .docx."""
    soup = BeautifulSoup(html or "", "html.parser")

    document = Document()
    normal_style = document.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(13)

    section = document.sections[0]
    section.page_width = Inches(8.27)   # A4
    section.page_height = Inches(11.69)
    section.top_margin = Inches(1.1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1.2)
    section.right_margin = Inches(0.9)

    # Lấy các node cấp cao nhất theo thứ tự xuất hiện trong HTML (không đào sâu lồng nhau
    # ngoài những gì các hàm con tự xử lý, vì prompt yêu cầu cấu trúc HTML phẳng/đơn giản).
    body = soup.body if soup.body else soup
    for tag in body.find_all(["p", "h2", "h3", "table", "ul", "ol"], recursive=False):
        if tag.name == "p":
            _add_paragraph_with_inline_formatting(document, tag)
        elif tag.name == "h2":
            paragraph = document.add_heading(tag.get_text(strip=True), level=1)
            if _is_centered(tag):
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif tag.name == "h3":
            document.add_heading(tag.get_text(strip=True), level=2)
        elif tag.name == "table":
            _render_table(document, tag)
        elif tag.name in ("ul", "ol"):
            style_name = "List Number" if tag.name == "ol" else "List Bullet"
            for li in tag.find_all("li", recursive=False):
                document.add_paragraph(li.get_text(strip=True), style=style_name)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()