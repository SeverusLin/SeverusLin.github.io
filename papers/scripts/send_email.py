import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import json
import os
import datetime
import resend
from scripts.utils import load_config, setup_logging

def load_scoring_guide():
    try:
        guide_path = Path(__file__).resolve().parents[1] / "scoring_guide.md"
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.warning(f"Could not load scoring guide: {e}")
        return "0-2: unrelated, 3-4: weakly, 5-6: moderately, 7-8: strongly, 9-10: highly related"

def build_email_html(papers, config):
    include_abstract = config["email"].get("include_full_abstract", True)
    parts = ["<h1>arXiv Daily Papers</h1>"]

    for p in papers:
        parts.append(f"<h3>{p['title']}</h3>")
        parts.append(f"<p><strong>arXiv:</strong> <a href='{p['url']}'>{p['id']}</a></p>")
        parts.append(f"<p><strong>Category:</strong> {p['category']}")
        if p.get("cross_categories"):
            parts[-1] += f" (also in: {', '.join(p['cross_categories'])})"
        parts[-1] += "</p>"
        parts.append(f"<p><strong>Authors:</strong> {p['authors']}</p>")
        if include_abstract:
            parts.append(f"<p><strong>Abstract:</strong> {p['abstract']}</p>")

        if p.get("references") and p.get("relatedness"):
            parts.append("<p><strong>📊 AI Relevance (0-10):</strong></p><ul>")
            for ref in p["references"]:
                rid = ref["id"]
                label = ref.get("label", rid)
                score = p["relatedness"].get(rid)
                if score is not None:
                    parts.append(f"<li>{label} ({rid}): <strong>{score}</strong></li>")
                else:
                    parts.append(f"<li>{label} ({rid}): N/A</li>")
            parts.append("</ul>")

        parts.append("<hr>")

    # 读取独立的评分标准文件，替换原来的硬编码
    guide = load_scoring_guide()
    parts.append("<p><strong>Scoring Guide:</strong></p>")
    parts.append(f"<pre>{guide}</pre>")

    return "\n".join(parts)

def main():
    setup_logging()
    config = load_config()
    resend_api_key = os.environ.get("RESEND_API_KEY")
    email_to = os.environ.get("EMAIL_TO")
    if not resend_api_key or not email_to:
        logging.error("RESEND_API_KEY or EMAIL_TO not set.")
        return

    json_path = Path(__file__).resolve().parents[2] / "output" / "papers.json"
    if not json_path.exists():
        logging.warning("No papers.json found, email will be skipped.")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        papers = json.load(f)
    if not papers:
        logging.info("No papers to send.")
        return

    html_content = build_email_html(papers, config)
    resend.api_key = resend_api_key
    sender = config["email"]["sender"]
    subject = config["email"]["subject"] + f" – {datetime.date.today().isoformat()}"

    try:
        r = resend.Emails.send({
            "from": sender,
            "to": email_to,
            "subject": subject,
            "html": html_content
        })
        logging.info(f"Email sent, ID: {r['id']}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()