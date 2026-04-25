"""
app/services/groq_service.py
Groq LLM wrapper with:
  - Automatic model fallback chain (handles decommissioned models)
  - Lawyer-optimised system prompt
  - Indian Constitution reference context
  - generate_relevance_summary() — per-result explanation at search time
  - chat_with_case()             — deep chat with a specific case
  - general_legal_chat()         — constitutional / general legal assistant
"""

from __future__ import annotations
import logging
from functools import lru_cache
from typing import List

from groq import Groq, BadRequestError

from app.core.config import settings
from app.models.schemas import ChatMessage

logger = logging.getLogger(__name__)


# ── Model fallback chain ───────────────────────────────────────────────────────
# Tried in order; skips decommissioned models automatically.
_MODEL_FALLBACKS = [
    settings.GROQ_MODEL,  # primary from .env
    *settings.GROQ_FALLBACK_MODELS,
]


@lru_cache(maxsize=1)
def _client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
    return Groq(api_key=settings.GROQ_API_KEY, timeout=30.0, max_retries=2)


def _chat_with_fallback(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    last_error = None
    tried: list[str] = []
    for model in _MODEL_FALLBACKS:
        if model in tried:
            continue
        tried.append(model)
        try:
            resp = _client().chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
            if model != settings.GROQ_MODEL:
                logger.warning("Fallback model used: %s", model)
            return resp.choices[0].message.content.strip()
        except BadRequestError as exc:
            if "decommissioned" in str(exc) or "model_not_found" in str(exc):
                logger.warning("Model %s decommissioned, trying next.", model)
                last_error = exc
                continue
            raise
        except Exception as exc:
            last_error = exc
            logger.error("Groq error with %s: %s", model, exc)
            continue
    raise RuntimeError(f"All Groq models failed. Last: {last_error}. Tried: {tried}.")


# ── System prompts ─────────────────────────────────────────────────────────────

# Core identity — shared across all prompts
_LAWYER_IDENTITY = """You are VakilAI, an expert Indian legal assistant built for practising advocates, 
law students, and litigants. You have deep knowledge of:
- The Constitution of India (all articles, schedules, amendments up to 2024)
- Supreme Court and High Court jurisprudence
- Indian Penal Code, CrPC, CPC, Evidence Act, and major statutes
- Fundamental Rights (Part III), Directive Principles (Part IV), Fundamental Duties (Part IV-A)
- Landmark constitutional cases and their ratio decidendi

You communicate in clear, precise legal language. When relevant, cite specific:
- Article numbers from the Constitution
- Section numbers from statutes  
- Case names and year (if known)
- Legal maxims in Latin/English with their meaning

Always clarify: you provide legal information and analysis, not formal legal advice. 
For formal representation, the user should consult a registered advocate.
Never fabricate case names, citations, or statutory provisions."""


# Constitutional reference — key articles embedded as context
_CONSTITUTION_REFERENCE = """
INDIAN CONSTITUTION — KEY PROVISIONS REFERENCE:

FUNDAMENTAL RIGHTS (Part III):
- Art 12: Definition of State (for FR enforcement)
- Art 13: Laws inconsistent with FRs are void
- Art 14: Equality before law and equal protection
- Art 15: Prohibition of discrimination (race, caste, sex, religion, place of birth)
- Art 16: Equality of opportunity in public employment
- Art 17: Abolition of untouchability
- Art 19: Six freedoms — speech, assembly, association, movement, residence, profession
- Art 20: Protection against double jeopardy, self-incrimination, ex-post-facto law
- Art 21: Right to life and personal liberty (most expansively interpreted right)
- Art 21A: Right to education (6-14 years)
- Art 22: Protection against arbitrary arrest and detention
- Art 23: Prohibition of traffic in persons and forced labour
- Art 24: Prohibition of child labour in factories/hazardous employment
- Art 25-28: Freedom of religion
- Art 29-30: Cultural and educational rights of minorities
- Art 32: Right to constitutional remedies (Dr Ambedkar called this "heart and soul")

DIRECTIVE PRINCIPLES (Part IV — Art 36-51): Non-justiciable but fundamental to governance.
Key: Art 39A (free legal aid), Art 44 (Uniform Civil Code), Art 45 (early childhood care)

CONSTITUTIONAL WRITS (Art 32 / 226):
- Habeas Corpus: produce the body; challenge illegal detention
- Mandamus: command a public authority to perform a duty
- Prohibition: stop inferior court from exceeding jurisdiction
- Certiorari: quash order of inferior court/tribunal
- Quo Warranto: challenge right to hold public office

KEY AMENDMENTS:
- 1st Amendment (1951): Restrictions on Art 19, Ninth Schedule
- 42nd Amendment (1976): Added "socialist", "secular", "integrity" to Preamble
- 44th Amendment (1978): Restored Art 19, removed Art 31 right to property
- 86th Amendment (2002): Art 21A — right to education
- 101st Amendment (2016): GST (Art 246A, 269A, 279A)
- 103rd Amendment (2019): 10% EWS reservation

LANDMARK CASES:
- Kesavananda Bharati (1973): Basic Structure doctrine — Parliament cannot amend basic structure
- Maneka Gandhi (1978): Art 21 — procedure must be just, fair, reasonable
- Indira Sawhney (1992): 50% cap on reservations, no reservation in promotions
- Vishaka (1997): Sexual harassment at workplace guidelines
- Puttaswamy (2017): Right to privacy is a fundamental right under Art 21
- Navtej Singh Johar (2018): Decriminalised consensual same-sex relations (Sec 377 IPC)
- Joseph Shine (2018): Adultery (Sec 497 IPC) struck down
"""

# ── Prompt templates ───────────────────────────────────────────────────────────

_SUMMARY_SYSTEM = f"""{_LAWYER_IDENTITY}

Your current task: Given a user's legal scenario and a Supreme Court case excerpt, 
write exactly 2-3 sentences explaining:
1. What legal issue the case decides (ratio decidendi)
2. How it is directly relevant to the user's scenario

Be precise. Cite the constitutional article or statute if applicable. No preamble."""


_CASE_CHAT_SYSTEM_TMPL = f"""{_LAWYER_IDENTITY}

{_CONSTITUTION_REFERENCE}

You are now analysing this specific Supreme Court case:

--- CASE: {{pdf_index}} ---
{{case_text}}
--- END OF CASE ---

When answering questions about this case:
- Identify the parties, court, and year if mentioned
- State the ratio decidendi (binding legal principle) clearly
- Distinguish obiter dicta from the ratio
- Explain how the constitutional provisions or statutes were interpreted
- Suggest how this precedent applies to similar fact patterns
- If asked in Hindi, respond in Hindi. If asked in English, respond in English."""


_GENERAL_LEGAL_SYSTEM = f"""{_LAWYER_IDENTITY}

{_CONSTITUTION_REFERENCE}

You help users with:
1. Understanding their constitutional rights
2. Explaining what legal steps to take in a given situation
3. Identifying relevant laws, sections, and precedents
4. Drafting legal notices, applications, or understanding documents
5. Explaining court procedures (trial court → HC → SC)
6. Advising on which court/tribunal has jurisdiction

RESPONSE FORMAT for legal queries:
- Start with the directly applicable law/article
- Explain what it means in plain language
- State what the user CAN do legally
- State what the user CANNOT do / risks involved
- Suggest next practical step (file complaint, send notice, approach court etc.)

If the query is in Hindi, respond entirely in Hindi.
If the query is in English, respond in English.
Mix Hinglish only if the user writes in Hinglish."""


# ── Public API ─────────────────────────────────────────────────────────────────


def generate_relevance_summary(query: str, case_text: str, pdf_index: str) -> str:
    """2-3 sentence relevance explanation shown on each search result card."""
    if not settings.GROQ_API_KEY:
        return f"{pdf_index} — set GROQ_API_KEY to enable AI summaries."

    prompt = (
        f"User scenario:\n{query}\n\n"
        f"Case excerpt ({pdf_index}):\n{case_text[: settings.SUMMARY_CONTEXT_MAX_CHARS]}\n\n"
        "Write the 2-3 sentence relevance summary."
    )
    try:
        return _chat_with_fallback(
            messages=[
                {"role": "system", "content": _SUMMARY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=settings.GROQ_SUMMARY_MAX_TOKENS,
            temperature=settings.GROQ_SUMMARY_TEMPERATURE,
        )
    except Exception as exc:
        logger.error("Groq summary error (%s): %s", pdf_index, exc)
        return f"Summary unavailable for {pdf_index}."


def chat_with_case(
    pdf_index: str,
    case_text: str,
    messages: List[ChatMessage],
) -> str:
    """Deep chat grounded in a specific Supreme Court case."""
    system = _CASE_CHAT_SYSTEM_TMPL.format(
        pdf_index=pdf_index,
        case_text=case_text[: settings.CHAT_CONTEXT_MAX_CHARS],
    )
    groq_msgs = [{"role": "system", "content": system}]
    for m in messages:
        groq_msgs.append({"role": m.role, "content": m.content})

    return _chat_with_fallback(
        messages=groq_msgs,
        max_tokens=settings.GROQ_MAX_TOKENS,
        temperature=settings.GROQ_CHAT_TEMPERATURE,
    )


def general_legal_chat(messages: List[ChatMessage]) -> str:
    """
    General constitutional / legal assistant chat.
    Not grounded in a specific case — uses Constitution reference + LLM knowledge.
    Used by the standalone assistant panel (not the case-specific chat).
    """
    groq_msgs = [{"role": "system", "content": _GENERAL_LEGAL_SYSTEM}]
    for m in messages:
        groq_msgs.append({"role": m.role, "content": m.content})

    return _chat_with_fallback(
        messages=groq_msgs,
        max_tokens=settings.GROQ_MAX_TOKENS,
        temperature=settings.GROQ_ASSISTANT_TEMPERATURE,
    )


# ── Query expansion ────────────────────────────────────────────────────────────

_EXPANSION_SYSTEM = """You are an Indian Supreme Court legal search expert.
Given a user's legal query, generate exactly {n} alternative search queries 
that cover the same legal issue using different terminology.

Rules:
- Use Indian legal terms (IPC, CrPC, CPC, Article numbers, etc.)
- Cover synonymous legal concepts (e.g. "eviction" → "ejectment", "dispossession")
- Vary between formal legal language and plain language
- Keep each query under 20 words
- Return ONLY a JSON array of strings, nothing else. Example:
  ["query one", "query two", "query three"]"""


def expand_query(query: str, n: int = 3) -> list[str]:
    """
    Use Groq to generate n alternative legal search queries.
    Falls back to [query] if Groq is unavailable or fails.
    """
    if not settings.GROQ_API_KEY:
        return [query]

    try:
        result = _chat_with_fallback(
            messages=[
                {"role": "system", "content": _EXPANSION_SYSTEM.format(n=n)},
                {"role": "user", "content": f"Query: {query}"},
            ],
            max_tokens=200,
            temperature=0.4,
        )
        # Parse JSON array
        import json
        import re

        match = re.search(r"\[.*?\]", result, re.DOTALL)
        if match:
            variants = json.loads(match.group())
            # Deduplicate, keep original first
            seen = {query.lower()}
            filtered = [query]
            for v in variants:
                if isinstance(v, str) and v.lower() not in seen:
                    seen.add(v.lower())
                    filtered.append(v.strip())
            return filtered[: n + 1]
    except Exception as exc:
        logger.warning("Query expansion failed: %s", exc)

    return [query]
