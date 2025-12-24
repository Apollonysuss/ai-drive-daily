name: 手动挖掘历史

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  history-job:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - uses: actions/setup-python@v2
      with:
        python-version: '3.9'
        
    - run: pip install requests
    
    # 👇 修复了这里：name: 后面加了空格
    - name: 拉取最新数据
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git pull origin main || echo "远程还没有 data.json，跳过拉取"
    
    - name: 运行历史挖掘
      env:
        DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
      run: python get_history.py
      
    - name: 保存结果
      run: |
        git add data.json
        git commit -m "History update" || echo "无新数据"
        git push origin main
