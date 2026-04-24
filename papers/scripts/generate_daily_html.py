import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import logging
import datetime
from jinja2 import Environment, FileSystemLoader
from scripts.utils import load_config, setup_logging

def load_scoring_guide():
    try:
        guide_path = Path(__file__).resolve().parents[1] / "scoring_guide.md"
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.warning(f"Could not load scoring guide: {e}")
        return ""

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
    scoring_guide = load_scoring_guide()

    html = template.render(
        papers=papers,
        date=today,
        scoring_guide_content=scoring_guide
    )

    output_file = Path(__file__).resolve().parents[2] / "output" / config["output"]["daily_html"]
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    logging.info(f"Generated daily HTML: {output_file}")

if __name__ == "__main__":
    main()