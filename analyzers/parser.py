"""
Module for parsing extracted text into structured resume sections.
Fallbacks included. Fully upgraded for spaced headers and broken PDF text.
"""

import re
from typing import Dict, List, Any
from utils.helpers import EMAIL_REGEX, PHONE_REGEX


# ------------------------------
# TEXT NORMALIZER (fix spaced letters)
# ------------------------------
def normalize_text(text: str) -> str:
    import re
    # Fix spaced out letters: "T E C H N I C A L" → "TECHNICAL"
    text = re.sub(
        r'(?<=\b)([A-Za-z](?:\s[A-Za-z]){1,})(?=\b)',
        lambda m: m.group(0).replace(" ", ""),
        text
    )

    # Remove excessive spaces
    text = re.sub(r'\s{2,}', ' ', text)

    return text


# ------------------------------
# MAIN PARSER FUNCTION
# ------------------------------
def parse_resume(text: str) -> Dict[str, Any]:
    """
    Parse cleaned text into structured resume fields.
    """
    if not text:
        return {"error": "No text to parse"}

    text = normalize_text(text)  # <<< FIX APPLIED HERE
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    parsed = {
        "name": "",
        "email": [],
        "phone": [],
        "skills": [],
        "education": [],
        "experience": []
    }

    # ---------------------------------
    # NAME EXTRACTION (improved)
    # ---------------------------------
    for line in lines:
        # Skip email/phone lines
        if re.search(EMAIL_REGEX, line) or re.search(PHONE_REGEX, line):
            continue

        # Assume first simple line is the name
        if 2 <= len(line.split()) <= 5:  # reasonable name length
            parsed["name"] = line
            break

    # ---------------------------------
    # EMAIL + PHONE EXTRACTION
    # ---------------------------------
    parsed["email"] = list(set(re.findall(EMAIL_REGEX, text)))

    # FIXED PHONE REGEX HANDLING
    parsed["phone"] = list(set(re.findall(PHONE_REGEX, text)))

    # ---------------------------------
    # SECTION DETECTION (new + flexible)
    # Handles:
    #   SKILLS
    #   TECHNICAL SKILLS
    #   T E C H N I C A L   S K I L L S
    #   EXPERIENCE
    #   E X P E R I E N C E
    #   EDUCATION
    #   E D U C A T I O N
    # ---------------------------------
    current_section = None

    for raw in lines:
        stripped = raw.strip()
        clean = stripped.replace(" ", "").lower()

        # Detect headers
        if re.search(r'\beducation\b', clean):
            current_section = "education"
            continue
        elif re.search(r'\bexperience\b', clean):
            current_section = "experience"
            continue
        elif re.search(r'\bskills\b', clean):
            current_section = "skills"
            continue
        # Fill section content
        if current_section:
            if current_section == "skills":
                # Remove category labels like: "JavaScript:", "Mobile:", etc.
                cleaned_line = re.sub(r'^[A-Za-z ]+:\s*', '', stripped)

                # Split by comma, bullet, semicolon and extend skills
                skill_list = re.split(r'[,\n•;]', cleaned_line)
                parsed["skills"].extend([s.strip() for s in skill_list if s.strip()])
            else:
                parsed[current_section].append(stripped)

    # Remove duplicates
    parsed["skills"] = list(set(parsed["skills"]))

    return parsed
