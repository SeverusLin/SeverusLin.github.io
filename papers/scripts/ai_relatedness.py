import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import json
import time
from openai import OpenAI
from scripts.utils import load_config, get_api_key_from_env

def get_client():
    config = load_config()
    api_key = get_api_key_from_env()
    base_url = config["ai"]["base_url"]
    return OpenAI(api_key=api_key, base_url=base_url), config["ai"]["model"]

def evaluate_relatedness(target_title, target_abstract, references):
    """
    根据参考论文列表，对目标论文进行 0-10 关联度打分。
    返回 dict: {ref_id: score}，失败返回空字典。
    """
    if not references:
        return {}

    # 构造参考论文简短描述
    ref_descriptions = []
    for r in references:
        label = r.get("label", r["id"])
        desc = f"ID: {r['id']} ({label})\nTitle: {r.get('title', 'N/A')}\nAbstract: {r.get('abstract', 'N/A')}"
        ref_descriptions.append(desc)

    ref_text = "\n\n".join(ref_descriptions)

    prompt = (
        "You are a research evaluator. Below is a target paper and a list of reference papers. "
        "For each reference paper, give a relevance score (0-10) based on how closely the target paper's topic, methodology, and results align with that reference. "
        "Use the following scale:\n"
        "- 0-2: completely unrelated (different field)\n"
        "- 3-4: weakly related (same broad area but different subfield)\n"
        "- 5-6: moderately related (shares some common concepts or techniques)\n"
        "- 7-8: strongly related (same subfield, similar methods)\n"
        "- 9-10: highly related (very close topic, potential overlapping results)\n\n"
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
                # 清除可能的代码块标记
                if content.startswith("```"):
                    content = content.strip("`").replace("json\n", "", 1).strip()
                scores = json.loads(content)
                # 只保留 references 中存在的 ID，并限制 0-10
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