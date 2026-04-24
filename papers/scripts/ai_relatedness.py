import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import json
import time
from openai import OpenAI
from scripts.utils import load_config, get_api_key_from_env

# 读取独立评分标准文件
def load_scoring_guide():
    """
    从 papers/scoring_guide.md 加载评分标准文本。
    如果文件不存在，返回默认的简要标准。
    """
    try:
        guide_path = Path(__file__).resolve().parents[1] / "scoring_guide.md"
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.warning(f"Could not load scoring guide: {e}. Using default scale.")
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
    return OpenAI(api_key=api_key, base_url=base_url), config["ai"]["model"]

def evaluate_relatedness(target_title, target_abstract, references):
    if not references:
        return {}

    # 构造参考论文描述
    ref_descriptions = []
    for r in references:
        label = r.get("label", r["id"])
        desc = f"ID: {r['id']} ({label})\nTitle: {r.get('title', 'N/A')}\nAbstract: {r.get('abstract', 'N/A')}"
        ref_descriptions.append(desc)
    ref_text = "\n\n".join(ref_descriptions)

    # 从独立文件加载评分指南
    scoring_guide = load_scoring_guide()

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

    client, model = get_client()
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300,
                timeout=60
            )
            content = response.choices[0].message.content.strip()
            if content:
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
        except Exception as e:
            logging.warning(f"Relatedness evaluation attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return {}