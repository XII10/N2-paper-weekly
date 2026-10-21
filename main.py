import requests
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# 读取GitHub Secrets里的配置信息
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY")
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
RECEIVE_EMAIL = os.environ.get("RECEIVE_EMAIL")

# 光催化固氮、接触电催化固氮关键词筛选
SEARCH_KEYWORDS = ["photocatalytic nitrogen fixation", "contact electrification nitrogen fixation", "固氮 光催化", "接触电催化 固氮"]

def fetch_new_papers():
    # 调用公开文献接口抓取最新一周相关高分文献
    import time
# 双域名自动 fallback，彻底解决解析失败问题
for domain in ["export.arxiv.org", "arxiv.org"]:
    try:
        res = requests.get(f"https://{domain}/api/query?search_query=all:nitrogen+fixation&sortBy=submittedDate&sortOrder=descending&max_results=20", timeout=30)
        res.raise_for_status()
        break
except Exception:
        time.sleep(2)
        continue

    papers = []
    # 简单过滤匹配关键词的文献
    for line in res.text.split("<entry>")[1:]:
        title = line.split("<title>")[1].split("</title>")[0].strip()
        summary = line.split("<summary>")[1].split("</summary>")[0].strip()
        if any(k in title.lower() or k in summary.lower() for k in SEARCH_KEYWORDS):
            papers.append({"title": title, "summary": summary})
    return papers[:10]

def ai_summarize(papers):
    # 调用智谱AI生成文献要点总结
    prompt = f"请把以下最新固氮领域文献整理成清晰的要点总结，每篇标注核心创新点：{str(papers)}"
    headers = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "glm-4-flash", "messages": [{"role":"user", "content": prompt}]}
    resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=data)
    return resp.json()["choices"][0]["message"]["content"]

def send_email(content):
    msg = MIMEText(content, "html", "utf-8")
    msg["Subject"] = f"本周固氮领域最新高分文献汇总 {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = SMTP_USER
    msg["To"] = RECEIVE_EMAIL
    server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [RECEIVE_EMAIL], msg.as_string())
    server.quit()

if __name__ == "__main__":
    papers = fetch_new_papers()
    result = ai_summarize(papers)
    send_email(result)
