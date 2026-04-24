import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import json
import os
import datetime
import resend
from scripts.utils import load_config, setup_logging

def build_email_html(papers, config):
    """Build HTML email with same format as webpage: no title link, arXiv ID link, category bold."""
    include_abstract = config["email"].get("include_full_abstract", True)
    parts = ["<h1>arXiv Daily Papers</h1>"]
    for p in papers:
        # title as plain text (no link)
        parts.append(f"<h3>{p['title']}</h3>")
        # arXiv ID as link
        parts.append(f"<p><strong>arXiv:</strong> <a href='{p['url']}'>{p['id']}</a></p>")
        # category bold
        parts.append(f"<p><strong>{p['category']}</strong></p>")
        parts.append(f"<p><strong>{p['primary_category']}</strong></p>")
        if p.get('cross_categories'):
            parts.append(f"<p><strong>Cross-listed:</strong> {', '.join(p['cross_categories'])}</p>")
        parts.append(f"<p><strong>Authors:</strong> {p['authors']}</p>")
        parts.append(f"<p><strong>Main Proposition (AI):</strong> {p['ai_summary']}</p>")
        if include_abstract:
            parts.append(f"<p><strong>Abstract:</strong> {p['abstract']}</p>")
        parts.append("<hr>")
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
        logging.info("No papers to send, skipping email.")
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