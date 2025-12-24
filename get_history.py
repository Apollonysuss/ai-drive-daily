import requests
import json
import xml.etree.ElementTree as ET
import time
import datetime
import os

print("🚀 脚本开始运行...") 

API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def fetch_history(keyword, tag):
    print(f"🔍 正在挖掘: {keyword} ...")
    url = f"https://news.google.com/rss/search?q={keyword}&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200: return []
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            link = item.find('link').text
            try:
                dt = datetime.datetime.strptime(item.find('pubDate').text[:16], '%a, %d %b %Y')
                date_str = dt.strftime('%Y-%m-%d')
            except:
                date_str = "2024-01-01"
            items.append({"title": title, "link": link, "date": date_str, "source": tag, "lang": "CN" if "CN" in tag else "EN"})
        print(f"   -> 找到 {len(items)} 条")
        return items
    except:
        return []

def call_ai(text, lang):
    if not API_KEY: return "未配置 API Key"
    
    # 提示词：要求生成中文深度解读
    prompt = """
    你是一名科技情报分析师。请阅读标题，用中文生成一段约 80-100 字的深度解读。
    格式要求：
    1. 【核心内容】：简述发生了什么。
    2. 【关键意义】：对行业的影响。
    """
    
    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
        "stream": False
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return "AI 分析超时"

def main():
    tasks = [
        {"kw": "具身智能 2024", "tag": "CN·具身智能"},
        {"kw": "Tesla Optimus progress", "tag": "EN·Embodied AI"},
        {"kw": "端到端自动驾驶 进展", "tag": "CN·自动驾驶"},
        {"kw": "site:arxiv.org Embodied AI", "tag": "Paper·论文"}
    ]
    
    new_items = []
    for task in tasks:
        items = fetch_history(task['kw'], task['tag'])
        new_items.extend(items)
        time.sleep(1)

    # 读取旧数据
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except:
            old_data = []
    else:
        old_data = []

    seen = set(i['title'] for i in old_data)
    final_data = old_data
    
    # --- 这里是修改的核心：不再限制数量 ---
    count = 0
    for item in new_items:
        if item['title'] in seen: continue
        
        print(f"🤖 [{count+1}] AI 正在解读: {item['title'][:15]}...")
        
        # 只要不是太旧的数据，都进行分析
        item['summary'] = call_ai(item['title'], item['lang'])
        
        final_data.append(item)
        seen.add(item['title'])
        count += 1
        
        # 稍微休息一下，防止接口每秒请求太多被封
        time.sleep(0.5)

    final_data.sort(key=lambda x: x['date'], reverse=True)

    print(f"💾 保存中... 共 {len(final_data)} 条数据")
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("✅ 完成！")

if __name__ == "__main__":
    main()
