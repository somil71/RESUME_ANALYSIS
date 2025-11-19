"""
Module for extracting text from different resume file formats.
Handles PDF, DOCX, and TXT files with error handling for corrupted or unreadable files.
"""
def normalize_extracted_text(text: str) -> str:
    import re
    # Fix spaced-out letters: "T E C H N I C A L" → "TECHNICAL"
    text = re.sub(r'(?<=\b)([A-Za-z](?:\s[A-Za-z]){1,})(?=\b)',
                  lambda m: m.group(0).replace(" ", ""),
                  text)
    # Remove extra spaces
    text = re.sub(r'\s{2,}', ' ', text)
    return text


import pdfplumber  # For PDF text extraction
from docx import Document  # For DOCX text extraction
import os


def extract_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using pdfplumber.
    
    Args:
        file_path (str): Path to the PDF file.
    
    Returns:
        str: Extracted text or empty string on error.
    
    Raises:
        FileNotFoundError: If file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    page_text = normalize_extracted_text(page_text)
                    text += page_text + "\n"

        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF (possibly corrupted): {e}")
        return ""


def extract_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file using python-docx.
    
    Args:
        file_path (str): Path to the DOCX file.
    
    Returns:
        str: Extracted text or empty string on error.
    
    Raises:
        FileNotFoundError: If file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"DOCX file not found: {file_path}")
    
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return ""


def extract_from_txt(file_path: str) -> str:
    """
    Extract text from a TXT file using built-in open().
    
    Args:
        file_path (str): Path to the TXT file.
    
    Returns:
        str: Extracted text or empty string on error.
    
    Raises:
        FileNotFoundError: If file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"TXT file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        print(f"Error reading TXT: {e}")
        return ""