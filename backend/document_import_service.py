"""Safe document text extraction for standards imports.

Only text that can be extracted with a declared method is persisted. Scanned
PDFs are reported as OCR-pending when a local OCR stack is unavailable.
"""
from io import BytesIO
from pathlib import Path
import re
import shutil


CLAUSE_START = re.compile(r'^\s*(?:第)?(?P<number>\d+(?:\.\d+){1,5})(?:条)?[、.．\s]*', re.M)


class DocumentImportError(ValueError):
    pass


def ocr_available():
    return bool(shutil.which('tesseract') and shutil.which('pdftoppm'))


def extract_document_text(content: bytes, filename: str):
    extension = Path(filename).suffix.lower()
    if extension == '.docx':
        try:
            from docx import Document
            document = Document(BytesIO(content))
        except Exception as exc:
            raise DocumentImportError(f'Word 文档读取失败：{exc}') from exc
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        for table in document.tables:
            paragraphs.extend(' '.join(cell.text.strip() for cell in row.cells if cell.text.strip()) for row in table.rows)
        text = '\n'.join(part for part in paragraphs if part)
        if not text.strip():
            raise DocumentImportError('Word 文档中没有可导入的文字内容。')
        return {'text': text, 'method': 'docx_text', 'ocr_pending': False}
    if extension == '.pdf':
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(content))
            text = '\n'.join((page.extract_text() or '').strip() for page in reader.pages)
        except Exception as exc:
            raise DocumentImportError(f'PDF 读取失败：{exc}') from exc
        if len(re.sub(r'\s+', '', text)) < 20:
            if ocr_available():
                try:
                    from pdf2image import convert_from_bytes
                    import pytesseract
                    pages = convert_from_bytes(content, dpi=250)
                    text = '\n'.join(pytesseract.image_to_string(page, lang='chi_sim+eng') for page in pages)
                except Exception as exc:
                    raise DocumentImportError(f'扫描 PDF OCR 失败：{exc}') from exc
                if len(re.sub(r'\s+', '', text)) < 20:
                    raise DocumentImportError('扫描 PDF 的 OCR 未识别到足够文字，请检查清晰度或语言包。')
                return {'text': text, 'method': 'pdf_ocr', 'ocr_pending': False}
            raise DocumentImportError('该 PDF 未包含可提取文本，且当前环境未安装 OCR 引擎（Tesseract + Poppler）。')
        return {'text': text, 'method': 'pdf_text', 'ocr_pending': False}
    raise DocumentImportError('仅支持 PDF 或 DOCX 文档。')


def split_into_articles(text: str, max_articles=1000):
    matches = list(CLAUSE_START.finditer(text))
    if not matches:
        paragraphs = [part.strip() for part in re.split(r'\n{1,}', text) if len(part.strip()) >= 8]
        return [(f'导入段落 {index + 1}', part) for index, part in enumerate(paragraphs[:max_articles])]
    articles = []
    for index, match in enumerate(matches[:max_articles]):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if len(content) >= 8:
            articles.append((match.group('number'), content))
    return articles
