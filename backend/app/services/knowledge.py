import os
import json
import re
from typing import Optional, Dict, Any, List

FAQS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "faqs.json")

def load_faqs() -> List[Dict[str, Any]]:
    if not os.path.exists(FAQS_FILE_PATH):
        return []
    with open(FAQS_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def search_hospital_faq(query: str) -> Optional[Dict[str, Any]]:
    """Search the local grounded hospital knowledge base.
    Returns matched FAQ item or None if no factual match is found."""
    faqs = load_faqs()
    if not query or not faqs:
        return None

    query_lower = query.lower()
    query_tokens = set(re.findall(r"\w+", query_lower))
    # Remove common conversational stop words
    stop_words = {
        "the", "is", "at", "which", "on", "a", "an", "and", "or", "to", "in", "for", 
        "of", "what", "are", "do", "you", "have", "please", "tell", "me", "can", "i",
        "my", "we", "our", "there", "any", "this", "that", "with"
    }
    meaningful_tokens = query_tokens - stop_words

    if not meaningful_tokens:
        meaningful_tokens = query_tokens

    best_match = None
    best_score = 0.0

    for faq in faqs:
        score = 0.0
        # Check keywords
        keywords = [kw.lower() for kw in faq.get("keywords", [])]
        for kw in keywords:
            kw_tokens = set(re.findall(r"\w+", kw)) - stop_words
            # Multi-word exact phrase match in query
            if " " in kw and kw in query_lower:
                score += 4.0
            elif kw in meaningful_tokens:
                score += 1.5
            elif kw_tokens and kw_tokens.issubset(meaningful_tokens):
                score += 2.5

        # Check question match
        question_tokens = set(re.findall(r"\w+", faq.get("question", "").lower())) - stop_words
        overlap = meaningful_tokens.intersection(question_tokens)
        score += len(overlap) * 1.0

        if score > best_score:
            best_score = score
            best_match = faq

    # Require confidence score >= 3.0 to prevent hallucination / spurious matches
    if best_score >= 3.0:
        return best_match
    return None
