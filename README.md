# Resume Analyzer

A simple, terminal-based tool for extracting, parsing, and scoring resumes from PDF, DOCX, or TXT files. It identifies key sections, extracts contact info using regex, and scores based on completeness, keyword matching, and skill relevance.

## Features
- Supports PDF (via pdfplumber), DOCX (via python-docx), and TXT files.
- Parses sections: Name, Email, Phone, Skills, Education, Experience.
- Scores resumes against provided keywords (default: python, java, sql, git).
- Handles edge cases: Missing sections, invalid formats, empty/corrupted files, multiple contacts.
- Outputs: Terminal summary and JSON file (`resume_analysis.json`).

## Installation

1. Ensure Python 3.8+ is installed.
2. Clone or download this project.
3. Install dependencies:
