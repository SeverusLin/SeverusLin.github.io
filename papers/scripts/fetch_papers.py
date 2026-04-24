import logging
import json
import datetime
import arxiv
from itertools import chain
from pathlib import Path
from .utils import load_config, setup_logging
from .ai_summarize import summarize_paper

def filter_by_keywords(paper, keywords):
    """Return True if any keyword appears in title or abstract (case-insensitive)."""
    text = (paper.title + " " + paper.summary).lower()
    return any(kw.lower() in text for kw in keywords)

def fetch_papers(config):
    categories = config["categories"]
    keywords = config["keywords"]
    lookback = config["lookback_days"]

    all_papers = []
    for cat in categories:
        logging.info(f"Searching arXiv category: {cat}")
        # arXiv API client
        search = arxiv.Search(
            query=f"cat:{cat}",
            max_results=100,  # safe limit
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        # arxiv library returns an iterator
        for result in search.results():
            # check if paper is within lookback days
            # result.published is a datetime object (timezone aware)
            days_ago = (datetime.datetime.now(datetime.timezone.utc) - result.published).days
            if days_ago > lookback:
                continue
            if filter_by_keywords(result, keywords):
                all_papers.append(result)
                logging.info(f"  Hit: {result.title[:70]}...")
    return all_papers

def main():
    setup_logging()
    config = load_config()
    papers = fetch_papers(config)

    # Deduplicate by entry_id
    seen_ids = set()
    unique_papers = []
    for p in papers:
        if p.entry_id not in seen_ids:
            seen_ids.add(p.entry_id)
            unique_papers.append(p)

    papers_data = []
    for p in unique_papers:
        # Authors list
        authors = ", ".join(a.name for a in p.authors)

        # Summary
        summary_text = p.summary.replace("\n", " ").strip()  # remove newlines

        # AI proposition
        ai_summary = summarize_paper(p.title, summary_text)

        papers_data.append({
            "id": p.entry_id.split("/")[-1],  # e.g., 2401.12345
            "title": p.title,
            "authors": authors,
            "abstract": summary_text,
            "url": p.entry_id,
            "published": p.published.isoformat(),
            "ai_summary": ai_summary
        })

    # Save to JSON file (used by HTML generator and email)
    output_dir = Path(__file__).resolve().parents[2] / "output"
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / "papers.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(papers_data, f, ensure_ascii=False, indent=2)

    logging.info(f"Saved {len(papers_data)} papers to {json_path}")

if __name__ == "__main__":
    main()