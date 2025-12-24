import requests
import json
import xml.etree.ElementTree as ET
import datetime
import os
import time
import arxiv 

API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# --- 1. 广撒网：Google News 源 ---
RSS_SOURCES = [
    {
        "tag": "CN·行业",
        "url": "https://news.google.com/rss/search?q=具身智能+OR+人形机器人+OR+端到端自动驾驶+OR+世界模型+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    },
    {
        "tag": "CN·企业",
        "url": "https://news.google.com/rss/search?q=宇树科技+OR+智元机器人+OR+华为ADS+OR+特斯拉FSD+OR+Waymo+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    },
    {
        "tag": "EN·Tech",
        "url": "https://news.google.com/rss/search?q=\"Embodied+AI\"+OR+\"Humanoid+Robot\"+OR+\"Tesla+Optimus\"+OR+\"NVIDIA+Isaac\"+when:1d&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "tag": "EN·Auto",
        "url": "https://news.google.com/rss/search?q=\"End-to-end+Autonomous+Driving\"+OR+\"Robotaxi\"+OR+\"Waymo\"+when:1d&hl=en-US&gl=US&ceid=US:en"
    }
]

# --- 2. 精准打击：ArXiv 论文源 ---
ARXIV_QUERIES = [
    "abs:\"Embodied AI\"", 
    "abs:\"Autonomous Driving\" AND abs:\"End-to-end\"",
    "abs:\"Humanoid Robot\""
]

def fetch_rss(source_config):
    print(f"📡 扫描 RSS: {source_config['tag']} ...")
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
            
            source = source_config['tag']
            if "arxiv" in title.lower(): source = "Paper·论文"
            items.append({"title": title, "link": link, "date": date_str, "source": source, "lang": "CN" if "CN" in source else "EN"})
        return items
    except:
        return []

def fetch_arxiv_papers():
    print("🎓 连接 ArXiv 学术库...")
    items = []
    try:
        for query in ARXIV_QUERIES:
            search = arxiv.Search(query=query, max_results=5, sort_by=arxiv.SortCriterion.SubmittedDate)
            for result in search.results():
                pub_date = result.published.date()
                if (datetime.date.today() - pub_date).days > 3: continue
                items.append({
                    "title": result.title,
                    "link": result.entry_id,
                    "date": str(pub_date),
                    "source": "Paper·论文",
                    "lang": "EN"
                })
        return items
    except Exception as e:
        print(f"❌ ArXiv 错误: {e}")
        return []

def call_ai_summary(text, lang):
    if not API_KEY: return "未配置 API Key"
    prompt = "你是一名科技分析师。判断标题是否与具身智能/自动驾驶/机器人高度相关。无关回复SKIP。相关则用中文生成80字深度解读（核心+意义）。"
    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": f"Title: {text}"}],
        "stream": False
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        content = res.json()['choices'][0]['message']['content']
        return None if "SKIP" in content else content
    except:
        return None

# --- 修改重点：强制注入今天的日期 ---
def generate_daily_brief(today_items):
    if not API_KEY or not today_items: return
    
    # 1. 获取 Python 算出来的真实日期
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    print(f"📝 正在生成【{today_str} 日报】...")
    titles = [item['title'] for item in today_items[:20]]
    titles_text = "\n".join(titles)
    
    # 2. 在提示词里直接告诉 AI 今天是几号
    prompt = f"""
    你是一名顶级行业分析师。今天是 {today_str}。
    请根据今日抓取的新闻标题，写一篇【具身智能与自动驾驶日报】。
    
    【格式要求】：
    1. 使用 Markdown 格式。
    2. 第一行必须是：### 📅 行业趋势分析 ({today_str})
    3. 内容包含三个板块：
       - 🚀 **重点突发**：今日最重要的1-2件事。
       - 💡 **技术风向**：有什么新技术或论文出现。
       - 📊 **市场动态**：企业融资或合作动态。
    4. 字数控制在 400 字以内，语言犀利，观点鲜明。
    """
    
    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": f"今日新闻:\n{titles_text}"}],
        "stream": False
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        content = res.json()['choices'][0]['message']['content']
        
        with open('daily_brief.json', 'w', encoding='utf-8') as f:
            json.dump({"date": today_str, "content": content}, f, ensure_ascii=False, indent=2)
        print("✅ 日报生成成功！(daily_brief.json)")
    except Exception as e:
        print(f"❌ 日报生成失败: {e}")

def job():
    all_items = []
    for source in RSS_SOURCES:
        all_items.extend(fetch_rss(source))
        time.sleep(1)
    
    all_items.extend(fetch_arxiv_papers())

    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r', encoding='utf-8') as f: old_data = json.load(f)
        except: old_data = []
    else: old_data = []

    seen = set(i['title'] for i in old_data)
    final_data = old_data
    
    today_new_items = []

    print(f"🔍 原始抓取 {len(all_items)} 条，开始 AI 清洗...")
    for item in all_items:
        if item['title'] in seen: continue
        
        summary = call_ai_summary(item['title'], item['lang'])
        if summary: 
            item['summary'] = summary
            final_data.insert(0, item)
            today_new_items.append(item)
            seen.add(item['title'])
            print(f"✅ 收录: {item['title'][:15]}...")
        time.sleep(0.5)

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data[:600], f, ensure_ascii=False, indent=2)
    
    if len(today_new_items) > 0:
        generate_daily_brief(today_new_items)
    elif len(final_data) > 0:
        generate_daily_brief(final_data[:15])

if __name__ == "__main__":
    job()
