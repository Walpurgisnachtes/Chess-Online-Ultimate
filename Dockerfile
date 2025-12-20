# 使用 Python 官方映像檔
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 修正：直接安裝 gunicorn 和 eventlet，確保它們存在
# 有時候 requirements.txt 因為編碼問題會跳過某些套件
COPY requirements.txt .
RUN pip install --no-cache-dir gunicorn eventlet && \
    pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼
COPY . .

# 設定環境變數，確保 Python 找得到 backend 資料夾，且 gunicorn 在 PATH 中
ENV PYTHONPATH=/app
ENV PATH="/home/python/.local/bin:${PATH}"
ENV PORT 8080

# 修正啟動指令：使用 python -m gunicorn 確保路徑正確
CMD python3 -m gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 backend.app:app