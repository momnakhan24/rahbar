"""Tests for extraction, cleaning, and structure-aware chunk metadata."""

from __future__ import annotations

from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.extract import extract
from pipeline.models import Document, Page


def test_markdown_extraction_removes_front_matter(tmp_path) -> None:
    source = tmp_path / "rules.md"
    source.write_text("---\ndoc_version: 2026\nsuperseded: false\n---\n# Rules\n\nClause 1 applies.")
    result = extract(str(source), "2026", False)
    assert result.pages[0].text.startswith("# Rules")
    assert "doc_version" not in result.pages[0].text


def test_html_table_rows_keep_cells_separated(tmp_path) -> None:
    source = tmp_path / "fees.html"
    source.write_text(
        "<h1>Fee table</h1><table><tr><th>Program</th><th>Fee</th></tr>"
        "<tr><td>BS CS</td><td>10,000 per credit hour</td></tr></table>",
        encoding="utf-8",
    )
    result = extract(str(source), "2026", False)
    assert "Program | Fee" in result.pages[0].text
    assert "BS CS | 10,000 per credit hour" in result.pages[0].text


def test_clean_removes_repeated_page_furniture_but_keeps_clause_text() -> None:
    doc = Document("rules.pdf", "2026", False, [
        Page("rules.pdf", 1, "FAST University\n1.1 Rules\nClause A.\nPage 1"),
        Page("rules.pdf", 2, "FAST University\n1.2 Rules\nClause B.\nPage 2"),
    ])
    result = clean(doc)
    assert "FAST University" not in result.pages[0].text
    assert "1.1 Rules" in result.pages[0].text
    assert "Clause B." in result.pages[1].text


def test_chunking_preserves_page_section_version_and_overlap() -> None:
    words = " ".join(f"term{i}" for i in range(35))
    doc = Document("rules.md", "2026", False, [
        Page("rules.md", 7, f"# Academic warning\n\n{words}")
    ])
    chunks = chunk(doc, size=12, overlap=3)
    assert len(chunks) >= 3
    assert all(len(item.text.split()) <= 12 for item in chunks)
    assert all(item.section == "Academic warning" for item in chunks)
    assert all(item.page == 7 and item.doc_version == "2026" for item in chunks)
    assert all(item.metadata()["superseded"] is False for item in chunks)
    assert set(chunks[0].text.split()[-3:]) & set(chunks[1].text.split()[:3])


def test_chunk_rejects_invalid_overlap() -> None:
    doc = Document("x.md", "v1", False, [Page("x.md", 1, "One sentence.")])
    try:
        chunk(doc, size=10, overlap=10)
    except ValueError as exc:
        assert "overlap" in str(exc)
    else:
        raise AssertionError("invalid overlap was accepted")


def test_numbered_pdf_clauses_remain_searchable_evidence() -> None:
    doc = Document("rules.pdf", "2026", False, [Page("rules.pdf", 1,
        "5.4 A CGPA below 2.00 results in academic warning.\n"
        "5.6 Three warnings result in withdrawal.")])
    chunks = chunk(doc, size=400, overlap=50)
    assert len(chunks) == 2
    assert chunks[0].section.startswith("5.4")
    assert "CGPA below 2.00" in chunks[0].text
    assert chunks[1].section.startswith("5.6")
    assert "withdrawal" in chunks[1].text


def test_markdown_clause_text_keeps_its_parent_section() -> None:
    doc = Document("rules.md", "2026", False, [Page("rules.md", 1,
        "## 2. Academic warning\n\n2.1 A CGPA below 2.00 triggers warning.\n\n"
        "2.2 Three warnings result in withdrawal.")])
    chunks = chunk(doc, size=400, overlap=50)
    assert all(c.section == "2. Academic warning" for c in chunks)
    assert "CGPA below 2.00" in " ".join(c.text for c in chunks)
    assert "withdrawal" in " ".join(c.text for c in chunks)


def test_pdf_extraction_ignores_text_outside_the_visible_page(tmp_path) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    content = DecodedStreamObject()
    content.set_data(
        b"BT /F1 12 Tf 20 100 Td (Visible current policy requires attendance.) Tj ET\n"
        b"BT /F1 12 Tf -400 100 Td (Hidden obsolete policy) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    path = tmp_path / "off-page.pdf"
    writer.write(path)
    doc = extract(str(path), "2026", False)
    assert "Visible current policy" in doc.pages[0].text
    assert "Hidden obsolete" not in doc.pages[0].text
