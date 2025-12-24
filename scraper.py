import requests
import json
import xml.etree.ElementTree as ET
import datetime
import os
import time
import arxiv # 需要在 workflow 里 pip install arxiv

API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# --- 1. Google News 泛搜索源 ---
RSS_SOURCES = [
    {
        "tag": "CN·行业动态",
        "url": "https://news.google.com/rss/search?q=具身智能+OR+人形机器人+OR+端到端自动驾驶+OR+世界模型+when:1d&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    },
    {
        "tag": "EN·Global Tech",
        "url": "https://news.google.com/rss/search?q=\"Embodied+AI\"+OR+\"Humanoid+Robot\"+OR+\"Tesla+Optimus\"+OR+\"NVIDIA+Gr00t\"+when:1d&hl=en-US&gl=US&ceid=US:en"
    }
]

# --- 2. ArXiv 论文精准源关键词 ---
ARXIV_QUERIES = [
    "abs:\"Embodied AI\"", 
    "abs:\"Autonomous Driving\" AND abs:\"End-to-end\"",
    "abs:\"Humanoid Robot\""
]

def fetch_rss(source_config):
    print(f"📡 正在扫描新闻源: {source_config['tag']} ...")
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
            
            # 来源标签清洗
            source = source_config['tag']
            if "arxiv" in title.lower(): source = "Paper·论文"
            
            items.append({
                "title": title, "link": link, "date": date_str, 
                "source": source, "lang": "CN" if "CN" in source else "EN"
            })
        return items
    except Exception as e:
        print(f"❌ RSS抓取错误: {e}")
        return []

def fetch_arxiv_papers():
    print("🎓 正在连接 ArXiv 学术数据库...")
    items = []
    try:
        # 搜索最近提交的论文
        for query in ARXIV_QUERIES:
            search = arxiv.Search(
                query = query,
                max_results = 5, # 每个词抓5篇，保证全
                sort_by = arxiv.SortCriterion.SubmittedDate
            )
            for result in search.results():
                # 只保留最近2天的，保证新鲜
                published_date = result.published.date()
                if (datetime.date.today() - published_date).days > 2:
                    continue
                    
                items.append({
                    "title": result.title,
                    "link": result.entry_id,
                    "date": str(published_date),
                    "source": "Paper·论文",
                    "lang": "EN"
                })
        print(f"   -> 抓取到 {len(items)} 篇新论文")
        return items
    except Exception as e:
        print(f"❌ ArXiv 接口报错: {e}")
        return []

def call_ai_summary(text, lang):
    if not API_KEY: return "未配置 API Key"
    
    prompt = """
    你是一名科技情报分析师。请判断以下标题是否与“具身智能”或“自动驾驶”高度相关。
    如果【无关】（如广告、股市、无关社会新闻），请只回复“SKIP”。
    如果【相关】，请用中文生成80字左右的深度解读（包含核心内容+行业意义）。
    """
    
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
        if "SKIP" in content: return None # AI 认为无关，过滤掉
        return content
    except:
        return None

def job():
    all_items = []
    
    # 1. 抓 RSS 新闻
    for source in RSS_SOURCES:
        all_items.extend(fetch_rss(source))
        time.sleep(1)
        
    # 2. 抓 ArXiv 论文
    all_items.extend(fetch_arxiv_papers())

    # 3. 读取旧数据
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except: old_data = []
    else:
        old_data = []

    seen = set(i['title'] for i in old_data)
    final_data = old_data
    
    # 4. AI 过滤与总结
    print(f"🔍 原始抓取 {len(all_items)} 条，开始 AI 智能清洗...")
    new_count = 0
    
    for item in all_items:
        if item['title'] in seen: continue
        
        # 让 AI 决定留不留
        summary = call_ai_summary(item['title'], item['lang'])
        if summary: 
            item['summary'] = summary
            final_data.insert(0, item)
            seen.add(item['title'])
            new_count += 1
            print(f"✅ 收录: {item['title'][:15]}...")
        else:
            print(f"🗑️ 剔除无关: {item['title'][:15]}...")
        
        time.sleep(0.5) # 防止 API 超限

    # 保留 500 条
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data[:500], f, ensure_ascii=False, indent=2)
    print(f"🎉 更新完成，经 AI 筛选后新入库 {new_count} 条。")

if __name__ == "__main__":
    job()
