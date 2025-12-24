import requests
import json
import xml.etree.ElementTree as ET
import time
import datetime
import os

print("🚀 脚本开始运行...") # 调试日志

API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def fetch_history(keyword, tag):
    print(f"🔍 正在挖掘: {keyword} ...")
    url = f"https://news.google.com/rss/search?q={keyword}&hl=zh-CN&gl=CN&ceid=CN:zh-CN"
    try:
        resp = requests.get(url, timeout=20)
        # 如果返回不是200，说明被墙了或者网络问题
        if resp.status_code != 200:
            print(f"⚠️ 请求失败，状态码: {resp.status_code}")
            return []
            
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
            
            items.append({
                "title": title, 
                "link": link, 
                "date": date_str, 
                "source": tag,
                "lang": "CN" if "CN" in tag else "EN"
            })
        print(f"   -> 找到 {len(items)} 条")
        return items
    except Exception as e:
        print(f"❌ 挖掘出错: {e}")
        return []

def call_ai(text, lang):
    if not API_KEY: return "未配置 API Key"
    prompt = "一句话概括核心价值（中文）。"
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
        return "生成中..."

def main():
    # 关键词任务
    tasks = [
        {"kw": "具身智能 2024", "tag": "CN·具身智能"},
        {"kw": "Tesla Optimus", "tag": "EN·Embodied AI"},
        {"kw": "端到端自动驾驶", "tag": "CN·自动驾驶"},
        {"kw": "site:arxiv.org Embodied AI", "tag": "Paper·论文"}
    ]
    
    new_items = []
    for task in tasks:
        # 无论成功失败，都继续下一个，防止脚本中断
        try:
            items = fetch_history(task['kw'], task['tag'])
            new_items.extend(items)
        except Exception as e:
            print(f"⚠️ 任务 {task['kw']} 跳过: {e}")
        time.sleep(1)

    # 读取旧数据 (如果文件不存在，就创建一个空的)
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except:
            old_data = []
    else:
        print("📂 本地没有 data.json，将创建新文件。")
        old_data = []

    seen = set(i['title'] for i in old_data)
    final_data = old_data
    
    # AI 摘要处理
    process_count = 0
    for item in new_items:
        if item['title'] in seen: continue
        
        # 为了防止超时，只处理前 5 条新数据，其他的先存标题
        if process_count < 5:
            print(f"🤖 AI 分析: {item['title'][:10]}...")
            item['summary'] = call_ai(item['title'], item['lang'])
            process_count += 1
        else:
            item['summary'] = "等待后续更新..."
            
        final_data.append(item)
        seen.add(item['title'])

    # 排序
    final_data.sort(key=lambda x: x['date'], reverse=True)

    # ⚠️ 关键：无论如何都要写入文件！哪怕是空的！
    print(f"💾 正在保存 {len(final_data)} 条数据到 data.json ...")
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print("✅ 脚本运行结束，data.json 已生成。")

# --- ⚠️ 最最关键的启动命令，千万不能漏 ---
if __name__ == "__main__":
    main()
