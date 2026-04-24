import sys
from pathlib import Path
# 把 papers/scripts 的父目录（即 papers/）加入 sys.path，以便使用绝对导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import json
import datetime
import arxiv
from scripts.utils import load_config, setup_logging
from scripts.ai_summarize import summarize_paper

def filter_by_keywords(paper, keywords):
    text = (paper.title + " " + paper.summary).lower()
    return any(kw.lower() in text for kw in keywords)

def fetch_papers(config):
    categories = config["categories"]
    keywords = config["keywords"]
    lookback = config["lookback_days"]

    all_papers = []
    for cat in categories:
        logging.info(f"Searching arXiv category: {cat}")
        search = arxiv.Search(
            query=f"cat:{cat}",
            max_results=100,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        for result in search.results():
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

    seen_ids = set()
    unique_papers = []
    for p in papers:
        if p.entry_id not in seen_ids:
            seen_ids.add(p.entry_id)
            unique_papers.append(p)

    papers_data = []
    for p in unique_papers:
        authors = ", ".join(a.name for a in p.authors)
        summary_text = p.summary.replace("\n", " ").strip()
        ai_summary = summarize_paper(p.title, summary_text)

        papers_data.append({
            "id": p.entry_id.split("/")[-1],
            "title": p.title,
            "authors": authors,
            "abstract": summary_text,
            "url": p.entry_id,
            "published": p.published.isoformat(),
            "ai_summary": ai_summary
        })

    output_dir = Path(__file__).resolve().parents[2] / "output"
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / "papers.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(papers_data, f, ensure_ascii=False, indent=2)

    logging.info(f"Saved {len(papers_data)} papers to {json_path}")

if __name__ == "__main__":
    main()