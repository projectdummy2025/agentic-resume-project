import html
import io
import re
import markdown
from xhtml2pdf import pisa
from docx import Document
from docx.shared import Pt, Inches, RGBColor

pdfStyles = """
@page {
    size: a4 portrait;
    margin: 2.2cm 2cm 2.2cm 2cm;
    @bottom-right {
        content: counter(page);
        font-size: 9pt;
        color: #71717a;
    }
}
body {
    font-family: Helvetica, Arial, sans-serif;
    color: #18181b;
    font-size: 10.5pt;
    line-height: 1.6;
}
h1 {
    font-size: 20pt;
    color: #0f172a;
    border-bottom: 2px solid #0284c7;
    padding-bottom: 6px;
    margin-top: 0;
    margin-bottom: 16px;
}
h2 {
    font-size: 14pt;
    color: #0369a1;
    margin-top: 18px;
    margin-bottom: 8px;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
}
h3 {
    font-size: 11.5pt;
    color: #334155;
    margin-top: 14px;
    margin-bottom: 6px;
}
p {
    margin-top: 0;
    margin-bottom: 10px;
    text-align: justify;
}
ul, ol {
    margin-top: 4px;
    margin-bottom: 12px;
    padding-left: 24px;
}
li {
    margin-bottom: 4px;
}
blockquote {
    border-left: 3px solid #38bdf8;
    background-color: #f8fafc;
    margin: 12px 0;
    padding: 8px 14px;
    color: #475569;
}
code {
    font-family: Courier, monospace;
    background-color: #f1f5f9;
    padding: 2px 4px;
    font-size: 9.5pt;
    color: #0f172a;
}
hr {
    border: none;
    border-top: 1px solid #cbd5e1;
    margin: 20px 0;
}
"""


def createPdf(markdownText: str, title: str = "Dokumen Ringkasan") -> bytes:
    # Hindari raw HTML dan remote image fetch dari konten dokumen tidak tepercaya
    safeMarkdown = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", markdownText)
    safeMarkdown = re.sub(r"<(?=\/?[a-zA-Z][^>]*>)", "&lt;", safeMarkdown)
    htmlBody = markdown.markdown(
        safeMarkdown,
        extensions=["extra", "sane_lists", "nl2br"],
    )

    # Render Markdown yang telah dibersihkan menjadi dokumen A4
    safeTitle = html.escape(title)
    fullHtml = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{safeTitle}</title>
    <style>
        {pdfStyles}
    </style>
</head>
<body>
    {htmlBody}
</body>
</html>"""

    outputBuffer = io.BytesIO()
    pdfStatus = pisa.CreatePDF(fullHtml, dest=outputBuffer, encoding="utf-8")
    if pdfStatus.err:
        raise RuntimeError(f"Gagal mengonversi Markdown ke PDF: error kode {pdfStatus.err}")

    outputBuffer.seek(0)
    return outputBuffer.getvalue()


def createDocx(markdownText: str, title: str = "Dokumen Ringkasan") -> bytes:
    document = Document()

    # Gunakan margin dokumen standar agar hasil konsisten pada A4
    for section in document.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Ubah blok Markdown umum menjadi elemen Word secara linear
    lines = markdownText.splitlines()
    inCodeBlock = False
    codeLines = []

    for line in lines:
        strippedLine = line.strip()

        # Gabungkan fenced code block menjadi paragraf monospace
        if strippedLine.startswith("```"):
            if inCodeBlock:
                codeText = "\n".join(codeLines)
                codeParagraph = document.add_paragraph(codeText)
                codeParagraph.paragraph_format.left_indent = Inches(0.4)
                if codeParagraph.runs:
                    codeParagraph.runs[0].font.name = "Courier New"
                    codeParagraph.runs[0].font.size = Pt(9.5)
                    codeParagraph.runs[0].font.color.rgb = RGBColor(71, 85, 105)
                codeLines = []
                inCodeBlock = False
            else:
                inCodeBlock = True
                codeLines = []
            continue

        if inCodeBlock:
            codeLines.append(line)
            continue

        if not strippedLine:
            continue

        # Buat heading berdasarkan level Markdown
        if strippedLine.startswith("# "):
            heading = document.add_heading(strippedLine[2:].strip(), level=1)
            heading.paragraph_format.space_before = Pt(14)
            heading.paragraph_format.space_after = Pt(8)
            continue

        if strippedLine.startswith("## "):
            heading = document.add_heading(strippedLine[3:].strip(), level=2)
            heading.paragraph_format.space_before = Pt(12)
            heading.paragraph_format.space_after = Pt(6)
            continue

        if strippedLine.startswith("### "):
            heading = document.add_heading(strippedLine[4:].strip(), level=3)
            heading.paragraph_format.space_before = Pt(10)
            heading.paragraph_format.space_after = Pt(4)
            continue

        # Buat bullet list dari marker dash atau asterisk
        if strippedLine.startswith(("- ", "* ")):
            listText = strippedLine[2:].strip()
            paragraph = document.add_paragraph(style="List Bullet")
            addRuns(paragraph, listText)
            paragraph.paragraph_format.space_after = Pt(3)
            continue

        # Buat numbered list dari marker angka
        numberMatch = re.match(r"^(\d+)\.\s+(.*)$", strippedLine)
        if numberMatch:
            listText = numberMatch.group(2)
            paragraph = document.add_paragraph(style="List Number")
            addRuns(paragraph, listText)
            paragraph.paragraph_format.space_after = Pt(3)
            continue

        # Tampilkan blockquote dengan indentasi dan italic
        if strippedLine.startswith(">"):
            quoteText = strippedLine.lstrip(">").strip()
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.4)
            addRuns(paragraph, quoteText, italic=True)
            paragraph.paragraph_format.space_after = Pt(6)
            continue

        # Tampilkan teks lain sebagai paragraf standar
        paragraph = document.add_paragraph()
        addRuns(paragraph, strippedLine)
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.line_spacing = 1.15

    outputBuffer = io.BytesIO()
    document.save(outputBuffer)
    outputBuffer.seek(0)
    return outputBuffer.getvalue()


def addRuns(paragraph, text: str, italic: bool = False):
    # Pertahankan bold, italic, dan inline code Markdown pada DOCX
    tokens = re.split(r"(\*\*.*?\*\*|\*.*?\*|`.*?`)", text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**") and len(token) >= 4:
            run = paragraph.add_run(token[2:-2])
            run.bold = True
            run.italic = italic
        elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        elif token.startswith("`") and token.endswith("`") and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(9.5)
        else:
            run = paragraph.add_run(token)
            if italic:
                run.italic = True
