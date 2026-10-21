import os
import requests
import time
from zhipuai import ZhipuAI
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# -------------------------- 你只需要在这里修改自己的配置 --------------------------
# 你要筛选的目标关键词，已经预设好光催化固氮、接触电催化固氮相关方向
SEARCH_KEYWORDS = {
    "photocatalytic nitrogen fixation",
    "contact electrification catalysis nitrogen fixation",
    "nitrogen fixation photocatalysis",
    "triboelectric catalysis nitrogen reduction"
}
# 每周最多推送的文献数量，已调整为100篇
MAX_PAPERS = 100
# ------------------------------------------------------------------------------

def fetch_new_papers():
    # 双域名自动 fallback，彻底解决GitHub Actions解析arxiv失败的问题
    for domain in ["export.arxiv.org", "arxiv.org"]:
        try:
            res = requests.get(
                f"https://{domain}/api/query?search_query=all:nitrogen+fixation&sortBy=submittedDate&sortOrder=descending&max_results=200",
                timeout=60
            )
            res.raise_for_status()
            break
        except Exception as e:
            print(f"尝试域名 {domain} 失败，2秒后重试下一个: {str(e)}")
            time.sleep(2)
            continue
    else:
        raise ConnectionError("所有arxiv域名均无法访问，请稍后重试")

    papers = []
    # 解析arxiv返回的XML格式文献数据
    for line in res.text.split("<entry>")[1:]:
        try:
            title = line.split("<title>")[1].split("</title>")[0].strip().replace("\n", " ")
            summary = line.split("<summary>")[1].split("</summary>")[0].strip().replace("\n", " ")
            paper_url = line.split("<id>")[1].split("</id>")[0].strip()
            # 精准过滤匹配你研究方向的文献
            if any(k in title.lower() or k in summary.lower() for k in SEARCH_KEYWORDS):
                papers.append({
                    "title": title,
                    "summary": summary,
                    "url": paper_url
                })
        except IndexError:
            continue
    return papers[:MAX_PAPERS]

def summarize_papers(papers):
    # 读取GitHub Secrets里的智谱AI API Key，不会泄露密钥
    client = ZhipuAI(api_key=os.environ["ZHIPUAI_API_KEY"])
    summarized_content = "# 本周光催化/接触电催化固氮最新文献汇总\n\n"
    for idx, paper in enumerate(papers, 1):
        prompt = f"""请用中文简洁总结这篇固氮方向的学术文献核心创新点、实验亮点和研究价值，控制在150字以内：
        标题：{paper['title']}
        摘要：{paper['summary']}
        """
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        summarized_content += f"## {idx}. {paper['title']}\n"
        summarized_content += f"🔗 原文链接：{paper['url']}\n"
        summarized_content += f"💡 核心要点：{response.choices[0].message.content}\n\n"
    return summarized_content

def send_email(content):
    # 读取GitHub Secrets里的邮箱配置信息
    sender = os.environ["EMAIL_SENDER"]
    receiver = os.environ["EMAIL_RECEIVER"]
    auth_code = os.environ["EMAIL_AUTH_CODE"]
    
    msg = MIMEText(content, 'html', 'utf-8')
    msg['From'] = Header("每周文献自动推送机器人", 'utf-8')
    msg['To'] = Header(receiver, 'utf-8')
    msg['Subject'] = Header(f"📬 本周固氮方向最新高分文献汇总 {time.strftime('%Y-%m-%d')}", 'utf-8')

    # 适配QQ邮箱/163邮箱通用SMTP配置
    server = smtplib.SMTP_SSL('smtp.qq.com', 465)
    server.login(sender, auth_code)
    server.sendmail(sender, [receiver], msg.as_string())
    server.quit()
    print("邮件推送成功！")

if __name__ == "__main__":
    print("开始抓取最新文献...")
    papers = fetch_new_papers()
    print(f"成功筛选到 {len(papers)} 篇匹配方向的文献")
    if not papers:
        print("本周没有匹配关键词的新文献，跳过推送")
        exit(0)
    print("正在调用智谱AI生成文献要点总结...")
    final_content = summarize_papers(papers)
    print("正在发送汇总邮件...")
    send_email(final_content)
