"""
keyword_engine.py
Extracts and ranks keywords from resume text or job description.
Produces:
 - technical_keywords (ranked by frequency + heuristics)
 - domain_keywords
 - soft_keywords
 - top_keywords_flat (best N keywords for scoring)
"""

import re
from collections import Counter
from typing import Dict, List, Tuple

# common programming tokens/words to prefer
TECH_TOKENS = {
    "python", "java", "javascript", "typescript", "react", "reactjs", "node", "node.js",
    "express", "express.js", "django", "flask", "c++", "c", "c#", "go", "golang",
    "sql", "mysql", "postgres", "mongodb", "redis", "docker", "kubernetes", "aws",
    "gcp", "azure", "git", "ci/cd", "jenkins", "circleci", "heroku",
    "html", "css", "tailwind", "bootstrap", "figma", "postman", "rest", "graphql",
    "tensorflow", "pytorch", "opencv", "socket.io"
}

SOFT_TOKENS = {
    "leadership", "communication", "collaboration", "team", "agile", "scrum", "problem",
    "analysis", "design", "testing", "deployment", "optimization"
}


def clean_text(text: str) -> str:
    if not text:
        return ""
    # remove special chars except . / + - (for versions etc.)
    text = re.sub(r"[^\w\.\+\-/]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def extract_candidate_keywords_from_text(text: str) -> List[str]:
    """
    Heuristic extraction from resume or JD text:
      - finds tokens and multi-word phrases that look like tech names
      - returns list sorted by estimated importance
    """
    text_clean = clean_text(text)
    words = text_clean.split()
    # n-grams (1..3) and count
    ngrams = []
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i:i + n])
            # keep grams with alpha/num
            if len(gram) > 1:
                ngrams.append(gram)
    counts = Counter(ngrams)

    # rank by: token in TECH_TOKENS or presence of typical separators (like ".js"), frequency, length
    scored: List[Tuple[str, float]] = []
    for token, freq in counts.items():
        score = freq
        # boost if matches known tech tokens
        token_cmp = token.replace(".", "").replace("-", " ").lower()
        for tk in TECH_TOKENS:
            if tk in token_cmp:
                score += 5
        # boost if multi-word (likely phrase)
        if len(token.split()) > 1:
            score += 1
        scored.append((token, score))

    # sort and filter
    scored_sorted = sorted(scored, key=lambda x: (-x[1], -len(x[0])))
    # remove too generic tokens and overlap, keep top 60
    results = []
    seen = set()
    for tok, _ in scored_sorted:
        tok_clean = tok.strip()
        if len(tok_clean) < 2:
            continue
        # simple filter: skip purely numeric
        if re.fullmatch(r"\d+", tok_clean):
            continue
        # avoid duplicates (substrings)
        if any(tok_clean in s or s in tok_clean for s in seen):
            continue
        results.append(tok_clean)
        seen.add(tok_clean)
        if len(results) >= 60:
            break
    return results


def split_keywords_by_type(keywords: List[str]) -> Dict[str, List[str]]:
    tech = []
    soft = []
    domain = []
    for k in keywords:
        k_clean = k.lower()
        if any(tk in k_clean for tk in TECH_TOKENS):
            tech.append(k)
        elif any(sk in k_clean for sk in SOFT_TOKENS):
            soft.append(k)
        else:
            # heuristically classify multi-word phrases as domain keywords
            if " " in k_clean:
                domain.append(k)
            else:
                # single words: fallback to tech if contains letters typical for tech
                if len(k_clean) <= 4:
                    tech.append(k)
                else:
                    domain.append(k)
    return {"technical_keywords": tech, "domain_keywords": domain, "soft_keywords": soft}


def generate_keywords_from_resume(parsed_resume: Dict[str, List[str]], top_n: int = 25) -> List[str]:
    """
    Accepts parsed resume dict (the output of your parse_resume).
    Will combine 'skills', 'education', 'experience', 'projects', 'certifications' (if present)
    and return top_n keywords prioritized for scoring.
    """
    pieces = []
    # skills list is probably already clean
    skills = parsed_resume.get("skills", [])
    pieces.extend(skills)
    # include education/experience/project lines too
    for field in ("education", "experience"):
        for line in parsed_resume.get(field, []):
            pieces.append(line)
    # some resumes include 'projects' or 'certifications' as experience entries
    text_blob = " ".join(pieces)
    candidates = extract_candidate_keywords_from_text(text_blob)
    # prefer exact skills first
    ranked = []
    # normalize skills (lowercase)
    skills_lower = {s.lower() for s in skills}
    for s in candidates:
        if s.lower() in skills_lower:
            ranked.append(s)
    # append others
    for s in candidates:
        if s not in ranked:
            ranked.append(s)
    return ranked[:top_n]


def generate_keywords_from_jd(job_desc: str, top_n: int = 30) -> List[str]:
    candidates = extract_candidate_keywords_from_text(job_desc)
    return candidates[:top_n]


# small utility to produce a flat best-keyword list
def best_keywords_for_scoring(parsed_resume: Dict[str, List[str]], job_desc: str = "", top_n: int = 30) -> List[str]:
    resume_kw = generate_keywords_from_resume(parsed_resume, top_n=top_n)
    if job_desc:
        jd_kw = generate_keywords_from_jd(job_desc, top_n=top_n)
        # intersection of high-priority resume_kw and jd_kw first
        common = [k for k in resume_kw if any(k.lower() in j.lower() or j.lower() in k.lower() for j in jd_kw)]
        # fill with resume_kw then jd_kw
        final = common + [k for k in resume_kw if k not in common] + [k for k in jd_kw if k not in common]
        # dedupe while preserving order
        seen = set()
        res = []
        for item in final:
            if item.lower() not in seen:
                res.append(item)
                seen.add(item.lower())
            if len(res) >= top_n:
                break
        return res
    else:
        return resume_kw[:top_n]
