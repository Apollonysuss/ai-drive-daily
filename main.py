import arxiv
import json
import os
import requests
import datetime
import random

# 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "YOUR_API_KEY_HERE")
DATA_FILE = "data.json"
BRIEF_FILE = "daily_brief.json"

# 模拟 DeepSeek 调用 (如果没有 Key，为了防止报错，代码里做了 fallback)
def summarize_with_deepseek(text):
    if "YOUR_API_KEY" in DEEPSEEK_API_KEY:
        return f"【AI 摘要 (测试)】: {text[:100]}... (请配置 API Key 以启用真实摘要)"
    
    url = "https://api.deepseek.com/v1/chat/completions" # 假设的端点，请根据官方文档调整
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个科技新闻助手，请用中文简要总结以下关于具身智能或自动驾驶的论文内容。"},
            {"role": "user", "content": text}
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek API Error: {e}")
        return f"摘要生成失败: {text[:100]}..."

def fetch_arxiv_papers():
    # 搜索关键词：具身智能 和 自动驾驶
    query = 'cat:cs.RO AND ("embodied ai" OR "autonomous driving")'
    search = arxiv.Search(
        query=query,
        max_results=10,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    new_items = []
    for result in search.results():
        # 简单分类
        tag = "具身智能" if "embodied" in result.title.lower() else "自动驾驶"
        
        item = {
            "id": result.entry_id,
            "title": result.title,
            "date": result.published.strftime("%Y-%m-%d"),
            "tag": tag,
            "summary": summarize_with_deepseek(result.summary), # AI 摘要
            "raw_summary": result.summary, # 原文摘要
            "link": result.pdf_url
        }
        new_items.append(item)
    return new_items

def generate_daily_brief(items):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    brief = {
        "date": today,
        "content": f"### {today} AI 日报\n\n今日更新了 {len(items)} 篇关于具身智能与自动驾驶的论文。重点关注方向包括端到端控制与新一代感知算法..."
    }
    return brief

def main():
    print("开始抓取 Arxiv 数据...")
    new_data = fetch_arxiv_papers()
    
    # 读取旧数据以避免完全覆盖（可选，这里演示追加模式）
    all_data = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        except:
            pass
    
    # 将新数据插到最前面
    # 实际生产中应根据 ID 去重
    existing_ids = {item['id'] for item in all_data}
    unique_new_data = [item for item in new_data if item['id'] not in existing_ids]
    
    final_data = unique_new_data + all_data
    
    # 保存数据列表
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    # 生成并保存日报
    daily_brief = generate_daily_brief(unique_new_data)
    with open(BRIEF_FILE, 'w', encoding='utf-8') as f:
        json.dump(daily_brief, f, ensure_ascii=False, indent=2)

    print(f"更新完成，新增 {len(unique_new_data)} 条数据。")

if __name__ == "__main__":
    main()
