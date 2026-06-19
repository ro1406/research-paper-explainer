"""
Live research-context lookup tools.
"""

import re
import xml.etree.ElementTree as ET

import requests

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_SEARCH_URL = "https://export.arxiv.org/api/query"
PAPER_FIELDS = "title,abstract,year,authors,url,citationCount,venue,fieldsOfStudy"


def _clean_text(value: str | None, max_length: int | None = None) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if max_length and len(text) > max_length:
        return f"{text[: max_length - 3].rstrip()}..."
    return text


def _build_research_query(concept: str, paper_context: str, domain: str) -> str:
    query_parts = [
        _clean_text(concept, 120),
        _clean_text(paper_context, 220),
        _clean_text(domain, 80),
    ]
    return " ".join(part for part in query_parts if part)


def _normalize_max_results(max_results: int) -> int:
    return max(1, min(int(max_results or 5), 10))


def _semantic_scholar_papers(query: str, max_results: int) -> list[dict]:
    response = requests.get(
        SEMANTIC_SCHOLAR_SEARCH_URL,
        params={
            "query": query,
            "limit": max_results,
            "fields": PAPER_FIELDS,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    papers: list[dict] = []
    for paper in data.get("data", []):
        title = _clean_text(paper.get("title"))
        if not title:
            continue

        papers.append(
            {
                "title": title,
                "year": paper.get("year"),
                "authors": [
                    _clean_text(author.get("name"))
                    for author in paper.get("authors", [])[:5]
                    if author.get("name")
                ],
                "venue": _clean_text(paper.get("venue")),
                "url": paper.get("url"),
                "citation_count": paper.get("citationCount"),
                "fields_of_study": paper.get("fieldsOfStudy") or [],
                "abstract": _clean_text(paper.get("abstract"), 700),
                "source": "Semantic Scholar",
            }
        )

    return papers


def _arxiv_papers(query: str, max_results: int) -> list[dict]:
    response = requests.get(
        ARXIV_SEARCH_URL,
        params={
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        },
        timeout=10,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    papers: list[dict] = []

    for entry in root.findall("atom:entry", namespace):
        title = _clean_text(
            entry.findtext("atom:title", default="", namespaces=namespace)
        )
        if not title:
            continue

        authors = [
            _clean_text(author.findtext("atom:name", default="", namespaces=namespace))
            for author in entry.findall("atom:author", namespace)[:5]
        ]
        papers.append(
            {
                "title": title,
                "year": (
                    entry.findtext("atom:published", default="", namespaces=namespace)
                    or ""
                )[:4],
                "authors": [author for author in authors if author],
                "venue": "arXiv",
                "url": entry.findtext("atom:id", default="", namespaces=namespace),
                "citation_count": None,
                "fields_of_study": [],
                "abstract": _clean_text(
                    entry.findtext("atom:summary", default="", namespaces=namespace),
                    700,
                ),
                "source": "arXiv",
            }
        )

    return papers


def _suggest_research_directions(concept: str, papers: list[dict]) -> list[str]:
    title_and_abstract = " ".join(
        f"{paper.get('title', '')} {paper.get('abstract', '')}" for paper in papers
    ).lower()
    directions: list[str] = []

    keyword_directions = [
        (
            ("efficient", "linear", "sparse", "compression"),
            f"More efficient versions of {concept}",
        ),
        (
            ("scaling", "large-scale", "foundation", "pretraining"),
            f"Scaling {concept} to larger models or datasets",
        ),
        (
            ("vision", "image", "multimodal", "video"),
            f"Using {concept} in vision or multimodal systems",
        ),
        (
            ("retrieval", "knowledge", "rag", "memory"),
            f"Combining {concept} with retrieval or external knowledge",
        ),
        (
            ("robust", "safety", "bias", "privacy"),
            f"Studying robustness, safety, or privacy around {concept}",
        ),
    ]

    for keywords, direction in keyword_directions:
        if any(keyword in title_and_abstract for keyword in keywords):
            directions.append(direction)

    if not directions:
        directions = [
            f"Foundational papers that introduced or popularized {concept}",
            f"Recent applications that adapt {concept} to new tasks",
            f"Limitations and follow-up methods that improve on {concept}",
        ]

    return directions[:5]


async def find_research_context(
    concept: str,
    paper_context: str,
    domain: str = "machine learning",
    max_results: int = 5,
) -> dict:
    """
    Finds external research context for a concept discussed in the uploaded paper.

    Use this when the user asks where a concept leads, what uses it, related work,
    follow-up reading, or how the idea connects to broader research.

    Args:
        concept (str): The concept or method to investigate.
        paper_context (str): Paper-specific context that makes the search precise.
        domain (str): The broader research domain, such as machine learning.
        max_results (int): Maximum number of papers to return, capped at 10.

    Returns:
        dict: Related papers, suggested directions, source metadata, or error details.
    """
    concept = _clean_text(concept, 120)
    paper_context = _clean_text(paper_context, 500)
    domain = _clean_text(domain, 80) or "machine learning"
    max_results = _normalize_max_results(max_results)

    if not concept:
        return {
            "status": "failed",
            "detail": "Provide a non-empty concept to search for research context.",
        }

    query = _build_research_query(concept, paper_context, domain)
    errors: list[str] = []

    try:
        papers = _semantic_scholar_papers(query, max_results)
        source = "Semantic Scholar"
    except Exception as exc:
        papers = []
        source = "arXiv"
        errors.append(f"Semantic Scholar search failed: {exc}")

    if not papers:
        try:
            papers = _arxiv_papers(query, max_results)
            source = "arXiv"
        except Exception as exc:
            errors.append(f"arXiv search failed: {exc}")

    if not papers:
        return {
            "status": "failed",
            "query": query,
            "detail": "No related papers found from Semantic Scholar or arXiv.",
            "errors": errors,
        }

    return {
        "status": "success",
        "concept": concept,
        "query": query,
        "source": source,
        "suggested_directions": _suggest_research_directions(concept, papers),
        "papers": papers[:max_results],
        "errors": errors,
    }
