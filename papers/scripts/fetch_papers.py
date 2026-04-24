import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import json
import datetime
from arxiv import Client, Search, SortCriterion
from scripts.utils import load_config, setup_logging
from scripts.ai_relatedness import evaluate_relatedness

def filter_by_keywords(paper, keywords):
    text = (paper.title + " " + paper.summary).lower()
    return any(kw.lower() in text for kw in keywords)

def count_keyword_hits(paper, keywords):
    text = (paper.title + " " + paper.summary).lower()
    return sum(text.count(kw.lower()) for kw in keywords)

def fetch_papers(config):
    categories = config["categories"]
    keywords = config["keywords"]
    lookback = config["lookback_days"]
    all_papers = []
    client = Client()
    for cat in categories:
        logging.info(f"Searching arXiv category: {cat}")
        search = Search(
            query=f"cat:{cat}",
            max_results=100,
            sort_by=SortCriterion.SubmittedDate
        )
        for result in client.results(search):
            days_ago = (datetime.datetime.now(datetime.timezone.utc) - result.published).days
            if days_ago > lookback:
                continue
            if filter_by_keywords(result, keywords):
                all_papers.append(result)
                logging.info(f"  Hit: {result.title[:70]}...")
    return all_papers

def fetch_reference_info(ref_list, client):
    """根据 arXiv ID 获取参考论文的标题和摘要"""
    refs = []
    ids = [item["id"] for item in ref_list]
    try:
        search = Search(id_list=ids)
        results = list(client.results(search))
        for item in ref_list:
            rid = item["id"]
            match = next((r for r in results if r.entry_id.split("/")[-1] == rid), None)
            info = {
                "id": rid,
                "title": match.title if match else "Unknown",
                "abstract": match.summary.replace("\n", " ") if match else "",
                "label": item.get("label", rid)
            }
            refs.append(info)
    except Exception as e:
        logging.warning(f"Failed to fetch reference paper info: {e}")
        for item in ref_list:
            refs.append({"id": item["id"], "title": "N/A", "abstract": "", "label": item.get("label", item["id"])})
    return refs

def main():
    setup_logging()
    config = load_config()
    papers = fetch_papers(config)

    seen_ids = set()
    unique = []
    for p in papers:
        if p.entry_id not in seen_ids:
            seen_ids.add(p.entry_id)
            unique.append(p)

    keywords = config.get("keywords", [])
    if unique and keywords:
        scored = [(p, count_keyword_hits(p, keywords)) for p in unique]
        scored.sort(key=lambda x: x[1], reverse=True)
        unique = [p for p, s in scored]

    ref_list = config.get("reference_papers", [])
    references = []
    if ref_list:
        client = Client()
        references = fetch_reference_info(ref_list, client)

    papers_data = []
    for p in unique:
        authors = ", ".join(a.name for a in p.authors)
        abstract = p.summary.replace("\n", " ").strip()

        relatedness = {}
        if references:
            relatedness = evaluate_relatedness(p.title, abstract, references)

        all_cats = [str(c) for c in p.categories]
        primary = p.primary_category
        cross = [c for c in all_cats if c != primary]

        papers_data.append({
            "id": p.entry_id.split("/")[-1],
            "title": p.title,
            "authors": authors,
            "abstract": abstract,
            "url": p.entry_id,
            "published": p.published.isoformat(),
            "category": primary,
            "cross_categories": cross,
            "relatedness": relatedness,
            "references": references
        })

    output_dir = Path(__file__).resolve().parents[2] / "output"
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / "papers.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(papers_data, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(papers_data)} papers to {json_path}")

if __name__ == "__main__":
    main()