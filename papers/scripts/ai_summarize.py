import logging
from openai import OpenAI
from .utils import get_api_key_from_env

def get_client():
    """Create an OpenAI client using config base_url and model (model is used later)."""
    from .utils import load_config
    config = load_config()
    api_key = get_api_key_from_env()
    base_url = config["ai"]["base_url"]
    return OpenAI(api_key=api_key, base_url=base_url), config["ai"]["model"]

def summarize_paper(title, abstract):
    """
    Generate a short main proposition summary.
    Returns a string.
    """
    client, model = get_client()
    prompt = (
        "You are a mathematician and computer scientist. "
        "Please read the following paper title and abstract. "
        "Output ONLY the main proposition or theorem of the paper in one or two sentences. "
        "Do not add any extra commentary, explanation, or preamble. "
        "Just the proposition/theorem itself.\n\n"
        f"Title: {title}\n\n"
        f"Abstract: {abstract}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful research summarizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        summary = response.choices[0].message.content.strip()
        logging.info(f"Summarized: {title[:60]}... -> {summary[:80]}...")
        return summary
    except Exception as e:
        logging.error(f"AI summarization failed for {title}: {e}")
        return "AI summary unavailable."

def analyze_paper_deep(title, abstract):
    """
    Provide a deeper analysis: motivation, methods, main results, innovations.
    Returns a string (possibly with markdown formatting).
    """
    client, model = get_client()
    prompt = (
        "You are an expert researcher. Analyze the following paper in detail. "
        "Provide:\n"
        "1. Main motivation\n"
        "2. Method/approach\n"
        "3. Key results or theorems\n"
        "4. Innovations/contributions\n"
        "Use clear sections with headings. Output in English. "
        "Do not ask follow-up questions.\n\n"
        f"Title: {title}\n\n"
        f"Abstract: {abstract}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful research analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        analysis = response.choices[0].message.content.strip()
        return analysis
    except Exception as e:
        logging.error(f"Deep analysis failed: {e}")
        return "Analysis unavailable due to an error."