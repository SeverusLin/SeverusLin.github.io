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
        "You are a research assistant. Read the following paper title and abstract. "
        "Write a summary of the paper's main contributions and results in about 200 words. "
        "Focus on what the paper does, its key ideas, and any theorems or algorithms presented. "
        "Use plain English. The summary must be complete, no truncation.\n\n"
        f"Title: {title}\n\nAbstract: {abstract}"
    )
    import time

    # 尝试主模型两次
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful research summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,          # 足够 200 词
                timeout=90
            )
            finish_reason = response.choices[0].finish_reason
            content = response.choices[0].message.content
            logging.info(f"Attempt {attempt+1}: finish_reason={finish_reason}, len={len(content) if content else 0}")
            if finish_reason == "length":
                # 输出被截断，增大 max_tokens 重试
                logging.warning("Output truncated, retrying with larger max_tokens")
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful research summarizer."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=500,   # 放宽上限
                        timeout=90
                    )
                    content = response.choices[0].message.content
                    finish_reason = response.choices[0].finish_reason
                    logging.info(f"Retry with larger tokens: finish_reason={finish_reason}, len={len(content) if content else 0}")
                except Exception as e:
                    logging.error(f"Retry failed: {e}")
            if content and content.strip():
                return content.strip()
            else:
                logging.warning(f"Empty content (finish_reason={finish_reason}), retrying...")
                time.sleep(2)
        except Exception as e:
            logging.error(f"Attempt {attempt+1} error: {e}")
            time.sleep(2)

    # 降级到绝对稳定的旧模型
    fallback_model = "deepseek-chat"
    logging.info(f"Main model failed, trying fallback model: {fallback_model}")
    try:
        response = client.chat.completions.create(
            model=fallback_model,
            messages=[
                {"role": "system", "content": "You are a helpful research summarizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300,
            timeout=90
        )
        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()
        else:
            # 如果还空，再次用 500 tokens 尝试
            response = client.chat.completions.create(
                model=fallback_model,
                messages=[
                    {"role": "system", "content": "You are a helpful research summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                timeout=90
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
    except Exception as e:
        logging.error(f"Fallback model also failed: {e}")

    # 所有措施都失败，返回明确的失败提示（极低概率）
    return "AI summary could not be generated. Please try again later."

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