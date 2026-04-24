import sys
import logging
import datetime
import arxiv
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from .utils import load_config, setup_logging
from .ai_summarize import analyze_paper_deep

def main():
    setup_logging()
    if len(sys.argv) < 2:
        logging.error("Please provide an arXiv ID (e.g., 2401.12345)")
        return

    arxiv_id = sys.argv[1].strip()
    config = load_config()

    # Search the specific paper
    search = arxiv.Search(id_list=[arxiv_id])
    try:
        paper = next(search.results())
    except StopIteration:
        logging.error(f"Paper with ID {arxiv_id} not found.")
        return

    title = paper.title
    authors = ", ".join(a.name for a in paper.authors)
    abstract = paper.summary.replace("\n", " ").strip()
    url = paper.entry_id

    logging.info(f"Analyzing {title}...")
    analysis = analyze_paper_deep(title, abstract)

    # Render analysis.html
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("analysis.html")
    html = template.render(
        title=title,
        authors=authors,
        abstract=abstract,
        url=url,
        analysis=analysis,
        date=datetime.date.today().isoformat()
    )

    output_dir = Path(__file__).resolve().parents[2] / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / config["output"]["analysis_html"]
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    logging.info(f"Analysis saved to {output_file}")

if __name__ == "__main__":
    main()