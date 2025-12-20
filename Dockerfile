FROM python:3.12-slim

WORKDIR /app

# 安裝基本套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有檔案
COPY . .

# 關鍵環境變數：讓 Python 把 /app 和 /app/backend 都當作模組搜尋路徑
ENV PYTHONPATH="/app:/app/backend"
ENV PORT 8080

# 啟動命令：指定在 backend 資料夾內的 app 模組
# 格式為 [目錄].[檔案]:[變數]
CMD ["python3", "-m", "gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:8080", "--timeout", "120", "backend.app:app"]