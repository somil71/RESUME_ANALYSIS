"""
Helper module with regex patterns and utility functions.
"""

import re

# Regex patterns for common resume elements
EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_REGEX = r'\(?\b[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
