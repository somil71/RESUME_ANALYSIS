"""
Utility module for loading resume files by detecting format and extracting text.
"""

import os
from typing import Tuple
from analyzers.extractor import extract_from_pdf, extract_from_docx, extract_from_txt


def load_resume_file(file_path: str) -> Tuple[str, str]:
    """
    Load and extract text from a resume file based on its extension.
    
    Args:
        file_path (str): Path to the resume file.
    
    Returns:
        Tuple[str, str]: (extracted_text, file_type) or ("", "error") on failure.
    
    Raises:
        ValueError: If unsupported file type.
    """
    if not os.path.exists(file_path):
        return "", "File not found"
    
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == ".pdf":
            text = extract_from_pdf(file_path)
            return text, "pdf"
        elif ext == ".docx":
            text = extract_from_docx(file_path)
            return text, "docx"
        elif ext == ".txt":
            text = extract_from_txt(file_path)
            return text, "txt"
        else:
            return "", "Unsupported format"
    except Exception as e:
        return "", f"Extraction error: {str(e)}"