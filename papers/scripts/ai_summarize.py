import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import time
from openai import OpenAI
from scripts.utils import load_config, get_api_key_from_env

def get_client():
    config = load_config()
    api_key = get_api_key_from_env()
    base_url = config["ai"]["base_url"]
    return OpenAI(api_key=api_key, base_url=base_url), config["ai"]["model"]

def extract_theorem(title, abstract):
    """
    Use AI to extract the main theorem (or main result) from a paper's title and abstract.
    Returns a string containing the theorem in precise mathematical language with LaTeX,
    or a fallback message if extraction fails.
    """
    client, model = get_client()
    prompt = (
        "You are a mathematician. Read the following paper title and abstract. "
        "If the paper presents some main theorems, propositions, or core results, "
        "write them in precise mathematical language using LaTeX (inline $...$ or display $$...$$). "
        "Output ONLY the theorem statement. Do NOT add any extra commentary or preamble. "
        "If the paper does not contain a specific theorem, output 'No explicit theorem stated.'.\n\n"
        f"Title: {title}\n\nAbstract: {abstract}"
    )
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=400,
                timeout=60
            )
            content = response.choices[0].message.content.strip()
            if content:
                logging.info(f"Theorem extracted for: {title[:60]}...")
                return content
            else:
                logging.warning(f"Empty theorem response on attempt {attempt+1}")
        except Exception as e:
            logging.error(f"Theorem extraction error on attempt {attempt+1}: {e}")
        time.sleep(2)
    return "Theorem extraction failed."