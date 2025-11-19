"""
scoring_engine.py
Master scoring engine that:
 - computes completeness
 - computes skill relevance (keyword matching + embedding similarity)
 - computes experience relevance (embedding-based or token overlap fallback)
 - computes project/cert/cert relevance
 - computes seniority/depth bonus
 - returns a detailed breakdown and final score (0-100)
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import math
import re

# try to use sentence-transformers; if unavailable, fall back to token overlap
try:
    from sentence_transformers import SentenceTransformer, util
    SENT_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    ST_AVAILABLE = True
except Exception:
    SENT_MODEL = None
    ST_AVAILABLE = False

from analyzers.keyword_engine import best_keywords_for_scoring, generate_keywords_from_resume, generate_keywords_from_jd


# ---------- WEIGHTS (tweak if you want) ----------
WEIGHTS = {
    "completeness": 15,        # %
    "skill_match": 35,         # %
    "experience_relevance": 25,# %
    "projects_cert": 10,       # %
    "seniority": 15            # %
}


# ---------- HELPERS ----------
def safe_text(obj) -> str:
    if not obj:
        return ""
    if isinstance(obj, list):
        return " ".join(obj)
    return str(obj)


def jaccard_similarity(a: str, b: str) -> float:
    a_tokens = set(re.findall(r'\w+', a.lower()))
    b_tokens = set(re.findall(r'\w+', b.lower()))
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def embed_similarity(a: str, b: str) -> float:
    if ST_AVAILABLE and SENT_MODEL:
        try:
            emb_a = SENT_MODEL.encode(a, convert_to_tensor=True)
            emb_b = SENT_MODEL.encode(b, convert_to_tensor=True)
            sim = util.cos_sim(emb_a, emb_b).item()
            return float(max(0.0, min(1.0, sim)))  # clamp
        except Exception:
            return jaccard_similarity(a, b)
    else:
        return jaccard_similarity(a, b)


# ---------- SCORING COMPONENTS ----------
def score_completeness(parsed: Dict[str, Any]) -> float:
    sections = ["name", "email", "phone", "skills", "education", "experience"]
    present = 0
    for s in sections:
        val = parsed.get(s)
        if val:
            # treat lists with at least 1 element as present
            if isinstance(val, list) and len(val) > 0:
                present += 1
            elif isinstance(val, str) and val.strip():
                present += 1
    return (present / len(sections)) * WEIGHTS["completeness"]


def score_skill_match(parsed: Dict[str, Any], job_desc: str = "", target_keywords: List[str] = None) -> Tuple[float, Dict[str, Any]]:
    """
    Returns a weighted skill_match score and diagnostic info.
    Uses:
      - exact keyword overlap (bag-of-words)
      - embedding similarity between skill list and job_desc (if available)
    """
    if target_keywords is None:
        # auto-generate target keywords from resume + jd
        target_keywords = best_keywords_for_scoring(parsed, job_desc, top_n=40)

    # prepare text blobs
    resume_skills = " ".join(parsed.get("skills", []))
    jd_text = job_desc or " ".join(target_keywords)

    # exact match ratio
    resume_lower = resume_skills.lower()
    exact_matches = [kw for kw in target_keywords if kw.lower() in resume_lower]
    exact_ratio = len(exact_matches) / max(1, len(target_keywords))

    # embedding similarity across full skill text vs jd
    emb_sim = embed_similarity(resume_skills, jd_text)

    # per-skill similarity (average)
    per_skill_sims = []
    for s in parsed.get("skills", []):
        per_skill_sims.append(embed_similarity(s, jd_text))
    per_skill_avg = float(np.mean(per_skill_sims)) if per_skill_sims else 0.0

    # combine: weights inside skill_match
    skill_match_score = (0.5 * exact_ratio) + (0.35 * emb_sim) + (0.15 * per_skill_avg)
    skill_match_score = max(0.0, min(1.0, skill_match_score))

    # scale to allocated weight
    scaled = skill_match_score * WEIGHTS["skill_match"]

    diag = {
        "target_keywords_used": target_keywords,
        "exact_matches": exact_matches,
        "exact_ratio": exact_ratio,
        "embedding_similarity": emb_sim,
        "per_skill_avg": per_skill_avg,
        "raw_score_0_1": skill_match_score,
        "scaled_to_weight": scaled
    }
    return scaled, diag


def score_experience_relevance(parsed: Dict[str, Any], job_desc: str = "") -> Tuple[float, Dict[str, Any]]:
    """
    Measures how relevant experience entries are to job_desc.
    Uses embeddings or jaccard as fallback; averages across experience lines.
    """
    exp_lines = parsed.get("experience", [])
    if not exp_lines:
        return 0.0, {"reason": "no_experience"}

    jd_text = job_desc or " ".join(generate_keywords_from_resume(parsed, top_n=30))
    sims = []
    for line in exp_lines:
        sims.append(embed_similarity(line, jd_text))
    avg_sim = float(np.mean(sims)) if sims else 0.0
    scaled = avg_sim * WEIGHTS["experience_relevance"]
    diag = {"avg_similarity": avg_sim, "scaled": scaled}
    return scaled, diag


def score_projects_and_certs(parsed: Dict[str, Any], job_desc: str = "") -> Tuple[float, Dict[str, Any]]:
    """
    Looks for keywords in experience/project strings indicating projects or certs
    and scores them against the JD keywords.
    """
    text_blob = " ".join(parsed.get("experience", []) + parsed.get("education", []))
    # naive detection of certs/projects words
    cert_tokens = ["certificate", "certification", "certified", "aws", "gcp", "azure"]
    found = [tok for tok in cert_tokens if tok in text_blob.lower()]
    # similarity with JD
    jd_text = job_desc or " ".join(generate_keywords_from_resume(parsed, top_n=20))
    sim = embed_similarity(text_blob, jd_text)
    # score: presence bonus + similarity
    presence_score = min(1.0, len(found) / 2.0)
    raw = 0.6 * sim + 0.4 * presence_score
    scaled = raw * WEIGHTS["projects_cert"]
    diag = {"found_certs": found, "sim": sim, "raw": raw, "scaled": scaled}
    return scaled, diag


def score_seniority_depth(parsed: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Gives a bonus based on experience length, number of skills, and breadth.
    This is not exact years-based; it infers depth from counts and breadth markers.
    """
    num_exp = len(parsed.get("experience", []))
    num_skills = len(parsed.get("skills", []))
    # rough heuristics: 0-1 exp => low, 2-4 => mid, 5+ => high
    exp_score = min(1.0, num_exp / 4.0)
    skill_score = min(1.0, num_skills / 15.0)
    raw = 0.6 * exp_score + 0.4 * skill_score
    scaled = raw * WEIGHTS["seniority"]
    diag = {"num_exp": num_exp, "num_skills": num_skills, "raw": raw, "scaled": scaled}
    return scaled, diag


# ---------- MASTER FUNCTION ----------
def score_resume_master(parsed: Dict[str, Any], job_desc: str = "", target_keywords: List[str] = None) -> Dict[str, Any]:
    """
    Returns:
      {
        "breakdown": {component_name: score_weighted, ...},
        "diagnostics": {...},
        "final_score": 0-100
      }
    """
    diagnostics = {}

    completeness = score_completeness(parsed)
    diagnostics["completeness"] = completeness

    skill_score, skill_diag = score_skill_match(parsed, job_desc, target_keywords)
    diagnostics["skill_match"] = skill_diag

    exp_score, exp_diag = score_experience_relevance(parsed, job_desc)
    diagnostics["experience_relevance"] = exp_diag

    proj_score, proj_diag = score_projects_and_certs(parsed, job_desc)
    diagnostics["projects_cert"] = proj_diag

    senior_score, senior_diag = score_seniority_depth(parsed)
    diagnostics["seniority"] = senior_diag

    breakdown = {
        "completeness": completeness,
        "skill_match": skill_score,
        "experience_relevance": exp_score,
        "projects_cert": proj_score,
        "seniority": senior_score
    }

    final = sum(breakdown.values())
    # final should be in 0..100
    final = max(0.0, min(100.0, final))

    return {
        "breakdown": breakdown,
        "diagnostics": diagnostics,
        "final_score": round(final, 2)
    }
