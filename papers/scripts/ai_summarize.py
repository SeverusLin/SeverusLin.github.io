import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from openai import OpenAI
from scripts.utils import load_config, get_api_key_from_env

def get_client():
    config = load_config()
    api_key = get_api_key_from_env()
    base_url = config["ai"]["base_url"]
    return OpenAI(api_key=api_key, base_url=base_url), config["ai"]["model"]

def generate_report(title, abstract):
    """
    Generate a ~1000 words Markdown reading report for a paper.
    Returns the Markdown string.
    """
    client, model = get_client()
    prompt = (
        "You are an expert academic researcher. Read the following paper title and abstract. "
        "Generate a comprehensive reading report in **Markdown format**. "
        "The report should be approximately 1000 words, written in English, and cover the following sections:\n\n"
        "## 1. Main Motivation\n"
        "- Why was this research conducted? What problem does it address?\n\n"
        "## 2. Core Methodology\n"
        "- How did the authors approach the problem? Describe the key techniques, algorithms, or theoretical framework.\n\n"
        "## 3. Key Results and Theorems\n"
        "- What are the main findings, theorems, or experimental outcomes? Explain them clearly.\n\n"
        "## 4. Innovations and Contributions\n"
        "- What are the novel aspects? How does this work advance the field?\n\n"
        "## 5. Critical Discussion (Optional)\n"
        "- Any limitations, assumptions, or potential improvements you can infer from the abstract.\n\n"
        "Use headings, bullet points, and LaTeX math (inside $...$ or $$...$$) where appropriate. "
        "Do not add any extra commentary outside the report. Output ONLY the Markdown content, no preamble.\n\n"
        f"Title: {title}\n\nAbstract: {abstract}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful academic summarizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,      # 1000 words ≈ 1500 tokens, safe margin
            timeout=120
        )
        content = response.choices[0].message.content.strip()
        if content:
            logging.info(f"Generated report for: {title[:60]}... ({len(content)} chars)")
            return content
        else:
            logging.warning(f"Empty report for {title[:60]}")
            return "*No report generated.*"
    except Exception as e:
        logging.error(f"AI report generation failed for {title}: {e}")
        return f"*Report unavailable (error: {str(e)[:100]})*"