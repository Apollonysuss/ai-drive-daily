import requests
import json
import xml.etree.ElementTree as ET
import datetime
import os
import time

API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# --- 升级版数据源配置：广撒网 ---
RSS_SOURCES = [
    # 1. 国内产业/资本 (覆盖 36氪, 虎嗅, 钛媒体, 机器之心等)
    {
        "tag": "CN·行业",
        "url": "https://news.google.com/rss/search?q=具身智能+OR+人形机器人+OR+端到端自动驾驶+OR+Robotaxi+OR+世界模型+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    },
    {
        "tag": "CN·公司",
        "url": "https://news.google.com/rss/search?q=宇树科技+OR+智元机器人+OR+华为ADS+OR+小鹏NGP+OR+特斯拉FSD+OR+FigureAI+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    },
    # 2. 国际前沿 (覆盖 TechCrunch, TheVerge, Medium 等)
    {
        "tag": "EN·Tech",
        "url": "https://news.google.com/rss/search?q=\"Embodied+AI\"+OR+\"Humanoid+Robot\"+OR+\"Foundation+Model+for+Robotics\"+OR+\"Sim-to-Real\"+when:1d&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "tag": "EN·Auto",
        "url": "https://news.google.com/rss/search?q=\"End-to-end+Autonomous+Driving\"+OR+\"Waymo\"+OR+\"Tesla+Optimus\"+OR+\"NVIDIA+Isaac\"+when:1d&hl=en-US&gl=US&ceid=US:en"
    },
    # 3. 学术论文 (覆盖 Arxiv, CVPR, ICLR 等会议相关报道)
    {
        "tag": "Paper·论文",
        "url": "https://news.google.com/rss/search?q=site:arxiv.org+(\"Embodied+AI\"+OR+\"Autonomous+Driving\"+OR+\"World+Model\"+OR+\"Imitation+Learning\")+when:1d&hl=en-US&gl=US&ceid=US:en"
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
