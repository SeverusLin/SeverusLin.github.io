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
    client, model = get_client()
    prompt = (
        "You are a mathematician. Read the following paper title and abstract. "
        "If the paper states a main theorem or proposition, write it in precise mathematical language using LaTeX. "
        "If no theorem is explicitly stated, try to infer the main result from the abstract and present it as a theorem. "
        "If absolutely no result can be inferred, output exactly the phrase: 'No explicit theorem stated.'\n\n"
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
            content = response.choices[0].message.content
            if content and content.strip():
                logging.info(f"Theorem extracted for: {title[:60]}...")
                return content.strip()
            else:
                logging.warning(f"Empty theorem response on attempt {attempt+1} for {title[:60]}")
        except Exception as e:
            logging.error(f"Theorem extraction error on attempt {attempt+1}: {e}")
        time.sleep(2)

    logging.warning(f"All attempts failed to extract theorem for: {title[:60]}")
    return "No explicit theorem stated."