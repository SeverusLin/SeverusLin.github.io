import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import json
import time
from openai import OpenAI
from scripts.utils import load_config, get_api_key_from_env

def load_scoring_guide():
    try:
        guide_path = Path(__file__).resolve().parents[1] / "scoring_guide.md"
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.warning(f"Could not load scoring guide: {e}")
        return (
            "0-2: completely unrelated\n"
            "3-4: weakly related\n"
            "5-6: moderately related\n"
            "7-8: strongly related\n"
            "9-10: highly related"
        )

def get_client():
    config = load_config()
    api_key = get_api_key_from_env()
    base_url = config["ai"]["base_url"]
    return OpenAI(api_key=api_key, base_url=base_url), config["ai"]["model"], config["ai"].get("token_limit", 300)

def evaluate_relatedness(target_title, target_abstract, references):
    if not references:
        return {}

    ref_descriptions = []
    for r in references:
        label = r.get("label", r["id"])
        desc = f"ID: {r['id']} ({label})\nTitle: {r.get('title', 'N/A')}\nAbstract: {r.get('abstract', 'N/A')}"
        ref_descriptions.append(desc)
    ref_text = "\n\n".join(ref_descriptions)

    scoring_guide = load_scoring_guide()
    client, model, token_limit = get_client()

    prompt = (
        "You are a research evaluator. Below is a target paper and a list of reference papers. "
        "For each reference paper, give a relevance score (0-10) based on how closely the target paper's topic, methodology, and results align with that reference. "
        "Use the following scoring guide:\n\n"
        f"{scoring_guide}\n\n"
        "Target paper:\n"
        f"Title: {target_title}\nAbstract: {target_abstract}\n\n"
        "Reference papers:\n"
        f"{ref_text}\n\n"
        "Return ONLY a valid JSON object mapping reference IDs to integer scores. "
        "Example: {\"2301.00001\": 8, \"2312.12345\": 3}. Do not add any other text."
    )

    for attempt in range(4):  # 增加一次重试
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=token_limit,
                timeout=60
            )
            content = response.choices[0].message.content
            if content and content.strip():
                if content.startswith("```"):
                    content = content.strip("`").replace("json\n", "", 1).strip()
                scores = json.loads(content)
                valid = {}
                for r in references:
                    rid = r["id"]
                    if rid in scores:
                        try:
                            s = int(scores[rid])
                            valid[rid] = max(0, min(10, s))
                        except (ValueError, TypeError):
                            pass
                return valid
            else:
                logging.warning(f"Empty response on attempt {attempt+1} for {target_title[:60]}")
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed: {e}")
        time.sleep(2 ** attempt)   # 指数退避
    return {}