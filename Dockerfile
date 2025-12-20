# 測試
# 使用輕量級 Python 映像檔
FROM python:3.12-slim

# 設定環境變數，確保 Python 輸出直接印到終端機而不緩存
ENV PYTHONPATH /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# 設定 Cloud Run 預設埠號
ENV PORT 8080

# 設定容器內的工作目錄
WORKDIR /app

# 先複製 requirements.txt 以利用 Docker 層快取功能
COPY requirements.txt .

# 安裝相依套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案所有原始碼到容器內
COPY . .

# 啟動命令：使用 Gunicorn 搭配 eventlet 驅動程式以支援 SocketIO
# 假設你的主程式檔案是 app.py，且 Flask 實例名為 app
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0${PORT} backend.app:app