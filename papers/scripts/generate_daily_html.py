import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import logging
import datetime
from jinja2 import Environment, FileSystemLoader
from scripts.utils import load_config, setup_logging

def main():
    setup_logging()
    config = load_config()

    json_path = Path(__file__).resolve().parents[2] / "output" / "papers.json"
    if not json_path.exists():
        logging.error("papers.json not found. Run fetch_papers.py first.")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("daily.html")

    today = datetime.date.today().isoformat()
    html = template.render(
        papers=papers,
        date=today,
        mathjax_cdn="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
    )

    output_file = Path(__file__).resolve().parents[2] / "output" / config["output"]["daily_html"]
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    logging.info(f"Generated daily HTML: {output_file}")

if __name__ == "__main__":
    main()