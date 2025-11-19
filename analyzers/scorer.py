"""
Module for scoring the parsed resume using AI/ML.
Uses sentence-transformers for semantic similarity (embeddings) between resume and job desc/keywords.
Fallback to original scoring if unavailable.
"""

from typing import Dict, List, Any
import numpy as np

try:
    from sentence_transformers import SentenceTransformer, util  # AI/ML: Semantic embeddings
    SENTENCE_MODEL = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Falling back to keyword scoring.")


def score_resume(parsed: Dict[str, Any], job_desc: str = "", target_keywords: List[str] = []) -> Dict[str, float]:
    """
    Compute AI-enhanced scores for the parsed resume.
    
    Args:
        parsed (Dict[str, Any]): Parsed resume data.
        job_desc (str): Full job description text for semantic matching.
        target_keywords (List[str]): Fallback keywords.
    
    Returns:
        Dict[str, float]: Scores for completeness, semantics, skills, and total (0-100).
    """
    if "error" in parsed:
        return {"error": "Cannot score unparsed resume"}
    
    # Completeness: Unchanged (16.67 per section)
    sections_present = sum([
        bool(parsed["name"]),
        bool(parsed["email"]),
        bool(parsed["phone"]),
        bool(parsed["skills"]),
        bool(parsed["education"]),
        bool(parsed["experience"])
    ])
    completeness_score = (sections_present / 6) * 100
    
    # Prepare resume text for AI scoring
    resume_text = " ".join([
        parsed["name"],
        " ".join(parsed["skills"]),
        " ".join(parsed["education"]),
        " ".join(parsed["experience"])
    ])
    
    # AI/ML Semantic Scoring
    if ST_AVAILABLE and (job_desc or target_keywords):
        try:
            # Use job_desc if provided; else join keywords
            query_text = job_desc if job_desc else " ".join(target_keywords)
            
            # Generate embeddings
            resume_embedding = SENTENCE_MODEL.encode(resume_text)
            query_embedding = SENTENCE_MODEL.encode(query_text)
            
            # Cosine similarity (0-1, scale to 100)
            semantic_score = util.cos_sim(resume_embedding, query_embedding).item() * 100
            
            # Skill relevance: Semantic match per skill
            skills_lower = [s.lower() for s in parsed["skills"]]
            skill_similarities = []
            for skill in skills_lower:
                skill_emb = SENTENCE_MODEL.encode(skill)
                skill_sim = util.cos_sim(skill_emb, query_embedding).item() * 100
                skill_similarities.append(skill_sim)
            skill_score = np.mean(skill_similarities) if skill_similarities else 0
            
            print("AI semantic scoring successful.")
        except Exception as e:
            print(f"AI scoring failed ({e}), falling back.")
            semantic_score = skill_score = 0
    else:
        # Fallback: Original keyword matching
        resume_text_lower = resume_text.lower()
        keyword_matches = sum(1 for kw in target_keywords if kw.lower() in resume_text_lower)
        semantic_score = (keyword_matches / len(target_keywords)) * 100 if target_keywords else 0
        
        skills_lower = [s.lower() for s in parsed["skills"]]
        relevant_skills = sum(1 for skill in skills_lower if any(kw.lower() in skill for kw in target_keywords))
        skill_score = (relevant_skills / len(skills_lower)) * 100 if skills_lower else 0
    
    # Total: Average
    total_score = (completeness_score + semantic_score + skill_score) / 3
    
    return {
        "completeness": round(completeness_score, 2),
        "semantic_matching": round(semantic_score, 2),
        "skill_relevance": round(skill_score, 2),
        "total": round(total_score, 2)
    }