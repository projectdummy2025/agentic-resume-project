# Docling Reference

## What is Docling?
Docling simplifies document processing, parsing diverse formats — including advanced PDF understanding — and providing seamless integrations with the gen AI ecosystem.

## Features
- Parsing of multiple document formats incl. PDF, DOCX, PPTX, XLSX, HTML, EPUB, WAV, MP3, WebVTT, email formats (EML, MSG), images (PNG, TIFF, JPEG, ...), LaTeX, DocLang, plain text, and more
- Advanced PDF understanding incl. page layout, reading order, table structure, code, formulas, image classification, and more
- Unified, expressive DoclingDocument representation format
- Various export formats and options, including Markdown, HTML, WebVTT, DocLang, DocTags and lossless JSON
- Local execution capabilities for sensitive data and air-gapped environments
- Plug-and-play integrations incl. LangChain, LlamaIndex, Crew AI & Haystack for agentic AI
- Extensive OCR support for scanned PDFs and images
- Support of several Visual Language Models (GraniteDocling)

## Quickstart

### 1. Install
```bash
pip install docling
```
> **Note:** Python 3.9 support was dropped in docling version 2.70.0. Please use Python 3.10 or higher.

### 2. Convert a document (CLI)
```bash
docling https://arxiv.org/pdf/2206.01062
```
This generates a .md file in the current directory containing structured document content.

### 3. Python usage (recommended)
```python
from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
converter = DocumentConverter()
result = converter.convert(source)
print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"
```

## References
If you use Docling in your projects, please consider citing the following:
```bib
@techreport{Docling,
  author = {Deep Search Team},
  month = {8},
  title = {Docling Technical Report},
  url = {https://arxiv.org/abs/2408.09869},
  eprint = {2408.09869},
  doi = {10.48550/arXiv.2408.09869},
  version = {1.0.0},
  year = {2024}
}
```

## IBM Open Source AI
The project was started by the AI for knowledge team at IBM Research Zurich.
