from docx import Document
import fitz
import os
from src.exceptions.exceptions import FileTypeError, FileProcessingError


def extract_from_pdf(path):
    try:
        text = ""
        with fitz.open(path) as pdf:
            for page in pdf:
                text += page.get_text() + "\n"
        return text
    except Exception as e:
        raise FileProcessingError(f"Failed to extract text from PDF: {str(e)}")


def extract_from_docx(path):
    try:
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        raise FileProcessingError(f"Failed to extract text from DOCX: {str(e)}")


def extract_from_txt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with a different encoding
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            raise FileProcessingError(f"Failed to decode text file: {str(e)}")
    except Exception as e:
        raise FileProcessingError(f"Failed to read text file: {str(e)}")


def load_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        return extract_from_txt(file_path)
    elif ext == ".pdf":
        return extract_from_pdf(file_path)
    elif ext == ".docx":
        return extract_from_docx(file_path)
    else:
        raise FileTypeError(f"Unsupported file type: {ext}")