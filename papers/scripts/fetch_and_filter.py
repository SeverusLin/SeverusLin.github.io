import os, json, logging
from datetime import datetime, timedelta, timezone
import arxiv
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# ---------- 读取配置 ----------
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, "config.json"), encoding="utf-8") as f:
    config = json.load(f)

KEYWORDS = config["keywords"]
CATEGORIES = config.get("categories", [])
DAYS_BACK = config.get("days_back", 1)

# ---------- 初始化 DeepSeek 客户端 ----------
client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.environ["DEEPSEEK_API_KEY"]
)
# 用 V4 Flash 版本，速度快且免费
LLM_MODEL = "deepseek-v4-flash"

def is_relevant(title: str, abstract: str) -> bool:
    prompt = f"""你是数学领域专家。判断以下论文是否与任一关键词高度相关：{', '.join(KEYWORDS)}
只回答 "yes" 或 "no"，不要解释。

标题: {title}
摘要: {abstract}"""
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0
        )
        answer = resp.choices[0].message.content.strip().lower()
        return answer.startswith("yes")
    except Exception as e:
        logging.error(f"DeepSeek error: {e}")
        return False

# ---------- 获取 ArXiv 论文 ----------
now = datetime.now(timezone.utc)
start_date = now - timedelta(days=DAYS_BACK)

cat_filter = ""
if CATEGORIES:
    cat_parts = [f"cat:{c}" for c in CATEGORIES]
    cat_filter = "(" + " OR ".join(cat_parts) + ") AND "
search_query = f"{cat_filter}cat:math.*"

arxiv_client = arxiv.Client()
search = arxiv.Search(
    query=search_query,
    max_results=200,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

papers = []
for r in arxiv_client.results(search):
    pub = r.published.replace(tzinfo=timezone.utc)
    if pub < start_date:
        break
    papers.append(r)

logging.info(f"Fetched {len(papers)} papers from ArXiv")

# ---------- DeepSeek 筛选 ----------
filtered = []
for i, p in enumerate(papers):
    logging.info(f"Checking [{i+1}/{len(papers)}] {p.title[:60]}...")
    if is_relevant(p.title, p.summary):
        filtered.append({
            "title": p.title,
            "abstract": p.summary.replace("\n", " "),
            "url": p.entry_id,
            "authors": [a.name for a in p.authors],
            "published": p.published.isoformat()
        })

logging.info(f"Found {len(filtered)} relevant papers")

# ---------- 生成 HTML ----------
date_str = now.strftime("%Y-%m-%d")
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Daily ArXiv Papers – {date_str}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em; }}
  .paper {{ border-bottom: 1px solid #eee; padding: 1.2em 0; }}
  .title {{ font-size: 1.1em; font-weight: 600; }}
  .authors {{ color: #555; font-size: 0.9em; }}
  .abstract {{ color: #333; margin-top: 0.4em; }}
  a {{ color: #0645ad; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>📄 Daily ArXiv Papers – {date_str}</h1>
<p>Keywords: {', '.join(KEYWORDS)}</p>
<hr>"""

if not filtered:
    html += "<p>No relevant papers found today.</p>"
else:
    for p in filtered:
        authors_str = ', '.join(p['authors'])
        html += f"""
<div class="paper">
  <div class="title"><a href="{p['url']}" target="_blank">{p['title']}</a></div>
  <div class="authors">{authors_str}</div>
  <div class="abstract">{p['abstract'][:300]}...</div>
</div>"""

html += """
</body>
</html>"""

# 输出到 papers/index.html
papers_dir = os.path.join(script_dir, "..")
os.makedirs(papers_dir, exist_ok=True)
output_path = os.path.join(papers_dir, "index.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
logging.info(f"HTML saved to {output_path}")

# ---------- 发送邮件（Resend） ----------
if os.environ.get("SEND_EMAIL", "true").lower() == "true":
    try:
        import resend
        resend.api_key = os.environ["RESEND_API_KEY"]

        if filtered:
            text = "\n\n".join(
                [f"{p['title']}\n{p['url']}\n{p['abstract'][:200]}..." for p in filtered]
            )
        else:
            text = "今天没有找到相关论文。"

        resend.Emails.send({
            "from": "Kobayashi Bot <onboarding@resend.dev>",
            "to": [os.environ["EMAIL_TO"]],
            "subject": f"Daily ArXiv Papers - {date_str}",
            "html": f"<pre>{text}</pre>"
        })
        logging.info("Email sent successfully")
    except Exception as e:
        logging.error(f"Email error: {e}")