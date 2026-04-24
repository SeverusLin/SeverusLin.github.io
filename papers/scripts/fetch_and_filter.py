import os, json, logging, sys
from datetime import datetime, timedelta, timezone
import arxiv
from openai import OpenAI

# 设置日志级别为 DEBUG 以便看更多细节
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout
)

# ---------- 读取配置 ----------
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.json")
logging.info(f"Reading config from {config_path}")
with open(config_path, encoding="utf-8") as f:
    config = json.load(f)

KEYWORDS = config["keywords"]
CATEGORIES = config.get("categories", [])
# 测试阶段固定搜索最近7天，方便看到更多论文
SEARCH_DAYS = 7
today_date = datetime.now(timezone.utc).date()
start_date = today_date - timedelta(days=SEARCH_DAYS)

logging.info(f"Keywords: {KEYWORDS}")
logging.info(f"Categories filter: {CATEGORIES}")
logging.info(f"Searching from {start_date} to {today_date}")

# ---------- 初始化 DeepSeek ----------
client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY", "")
)
if not client.api_key:
    logging.error("DEEPSEEK_API_KEY is not set!")
    sys.exit(1)
else:
    logging.info("DeepSeek client initialized")

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
        logging.debug(f"DeepSeek response: '{answer}' for title '{title[:50]}...'")
        return answer.startswith("yes")
    except Exception as e:
        logging.error(f"DeepSeek API error: {e}")
        return False

# ---------- 获取 ArXiv 论文 ----------
cat_filter = ""
if CATEGORIES:
    cat_parts = [f"cat:{c}" for c in CATEGORIES]
    cat_filter = "(" + " OR ".join(cat_parts) + ") AND "
search_query = f"{cat_filter}cat:math.*"
logging.info(f"ArXiv search query: {search_query}")

arxiv_client = arxiv.Client()
search = arxiv.Search(
    query=search_query,
    max_results=500,                       # 足够覆盖7天
    sort_by=arxiv.SortCriterion.SubmittedDate
)

papers = []
fetched_count = 0
for r in arxiv_client.results(search):
    pub = r.published
    pub_date = pub.date() if hasattr(pub, 'date') else pub.date()
    # 调试：打印每篇论文的发布时间
    if fetched_count < 3:
        logging.debug(f"Paper: {r.title[:40]}... published {pub} (date part: {pub_date})")
    if pub_date < start_date:
        # 因为按提交时间降序排列，一旦早于起始日期就停止
        logging.info(f"Reached paper older than start_date: {pub_date}, stopping fetch.")
        break
    if pub_date <= today_date:
        papers.append(r)
    fetched_count += 1

logging.info(f"Total papers fetched from ArXiv: {len(papers)} (checked {fetched_count})")

if len(papers) == 0:
    logging.warning("No papers returned from ArXiv. Check query and date range manually.")
    # 尝试构造一个示例 URL 让用户验证
    logging.info("You can test the API directly: https://export.arxiv.org/api/query?search_query=cat:math.*&sortBy=submittedDate&sortOrder=descending&max_results=5")

# ---------- DeepSeek 筛选 ----------
filtered = []
for i, p in enumerate(papers):
    if (i+1) % 10 == 0:
        logging.info(f"Progress: {i+1}/{len(papers)} papers screened...")
    if is_relevant(p.title, p.summary):
        filtered.append({
            "title": p.title,
            "abstract": p.summary.replace("\n", " "),
            "url": p.entry_id,
            "authors": [a.name for a in p.authors],
            "published": p.published.isoformat()
        })

logging.info(f"After filtering: {len(filtered)} relevant papers")

# ---------- 生成 HTML ----------
date_str = today_date.isoformat()
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
<p>Keywords: {', '.join(KEYWORDS)} | Last {SEARCH_DAYS} days</p>
<hr>"""

if not filtered:
    html += "<p>No relevant papers found in the last 7 days.</p>"
else:
    for p in filtered:
        authors_str = ', '.join(p['authors'])
        html += f"""
<div class="paper">
  <div class="title"><a href="{p['url']}" target="_blank">{p['title']}</a></div>
  <div class="authors">{authors_str}</div>
  <div class="abstract">{p['abstract'][:300]}...</div>
</div>"""

html += "\n</body>\n</html>"

papers_dir = os.path.join(script_dir, "..")
os.makedirs(papers_dir, exist_ok=True)
output_path = os.path.join(papers_dir, "index.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
logging.info(f"HTML written to {output_path}")

# ---------- 邮件（根据环境变量决定）----------
send_email_flag = os.environ.get("SEND_EMAIL", "true").lower()
if send_email_flag == "true":
    try:
        import resend
        resend.api_key = os.environ.get("RESEND_API_KEY", "")
        if not resend.api_key:
            logging.error("RESEND_API_KEY is missing, cannot send email")
        else:
            if filtered:
                text = "\n\n".join(
                    [f"{p['title']}\n{p['url']}\n{p['abstract'][:200]}..." for p in filtered]
                )
            else:
                text = "今天没有找到相关论文。"

            resend.Emails.send({
                "from": "ArXiv Bot <onboarding@resend.dev>",
                "to": [os.environ["EMAIL_TO"]],
                "subject": f"Daily ArXiv Papers - {date_str}",
                "html": f"<pre>{text}</pre>"
            })
            logging.info("Email sent successfully")
    except Exception as e:
        logging.error(f"Email error: {e}")
else:
    logging.info("Email sending skipped (SEND_EMAIL != true)")