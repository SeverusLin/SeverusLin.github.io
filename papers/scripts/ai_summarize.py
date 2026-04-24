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

def summarize_paper(title, abstract):
    client, model = get_client()
    prompt = (
        "You are a mathematician and computer scientist. "
        "Read the following paper title and abstract. "
        "Output ONLY the main proposition or theorem of the paper in one or two sentences. "
        "Do not add any commentary.\n\n"
        f"Title: {title}\n\nAbstract: {abstract}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a research summarizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"AI summarization failed for {title}: {e}")
        return "AI summary unavailable."

def analyze_paper_deep(title, abstract):
    client, model = get_client()
    prompt = (
        "You are an expert researcher. Analyze the following paper in detail:\n"
        "1. Main motivation\n2. Method/approach\n3. Key results or theorems\n4. Innovations\n"
        "Output in English with clear sections.\n\n"
        f"Title: {title}\n\nAbstract: {abstract}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a research analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Deep analysis failed: {e}")
        return "Analysis unavailable due to an error."