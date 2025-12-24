import requests
import json
import xml.etree.ElementTree as ET
import datetime
import os
import time

API_KEY = os.environ.get("DEEPSEEK_API_KEY")

RSS_SOURCES = [
    {
        "tag": "CN·具身智能",
        "url": "https://news.google.com/rss/search?q=具身智能+OR+人形机器人+OR+宇树科技+OR+智元机器人+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    },
    {
        "tag": "CN·自动驾驶",
        "url": "https://news.google.com/rss/search?q=端到端自动驾驶+OR+萝卜快跑+OR+华为ADS+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    },
    {
        "tag": "EN·Embodied AI",
        "url": "https://news.google.com/rss/search?q=%22Embodied+AI%22+OR+%22Humanoid+Robot%22+OR+%22Figure+AI%22+OR+%22Tesla+Optimus%22+when:1d&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "tag": "EN·AutoDriving",
        "url": "https://news.google.com/rss/search?q=%22Autonomous+Driving%22+OR+%22Robotaxi%22+OR+%22FSD+v12%22+OR+%22Waymo%22+when:1d&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "tag": "Paper·论文",
        "url": "https://news.google.com/rss/search?q=site:arxiv.org+%22Embodied+AI%22+OR+%22End-to-end+driving%22+OR+%22World+Model%22+when:1d&hl=en-US&gl=US&ceid=US:en"
    }
]

def fetch_rss(source_config):
    print(f"📡 抓取源: {source_config['tag']} ...")
    try:
        resp = requests.get(source_config['url'], timeout=15)
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            link = item.find('link').text
            try:
                dt = datetime.datetime.strptime(item.find('pubDate').text[:16], '%a, %d %b %Y')
                date_str = dt.strftime('%Y-%m-%d')
            except:
                date_str = datetime.date.today().strftime('%Y-%m-%d')
            
            source_name = source_config['tag']
            if "arxiv" in title.lower() or "arxiv" in link.lower():
                source_name = "Paper·论文"

            items.append({
                "title": title,
                "link": link,
                "date": date_str,
                "source": source_name,
                "lang": "CN" if "CN" in source_config['tag'] else "EN"
            })
        return items
    except Exception as e:
        print(f"❌ 失败: {e}")
        return []

def call_ai_summary(text, lang):
    if not API_KEY: return "未配置 API Key"
    
    prompt = """
    你是一名科技情报分析师。请阅读新闻标题，用中文生成一段约 80-100 字的深度解读。
    格式要求：
    1. 【核心内容】：简述发生了什么。
    2. 【关键意义】：对行业意味着什么。
    不要使用Markdown格式。
    """
    if "arxiv" in text.lower():
        prompt = "你是一名学术助手。请阅读论文标题，用中文简述其研究方向和核心创新点（80字左右）。"

    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": f"Title: {text}"}],
        "stream": False
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return "AI 分析超时"

def job():
    all_new_items = []
    for source in RSS_SOURCES:
        items = fetch_rss(source)
        all_new_items.extend(items[:3])
        time.sleep(1)

    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            try: old_data = json.load(f)
            except: old_data = []
