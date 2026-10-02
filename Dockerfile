# 1. 使用官方的輕量級 Python 3.10 作為基底環境
FROM python:3.10-slim

# 2. 設定容器內的工作目錄為 /app
WORKDIR /app

# 3. 先將 requirements.txt 複製到容器內
COPY requirements.txt .

# 4. 根據清單安裝所有需要的 Python 套件 (加上 --no-cache-dir 讓映像檔更小)
RUN pip install --no-cache-dir -r requirements.txt

# 5. 將你本地專案的所有程式碼與檔案，複製到容器的 /app 目錄下
COPY . .

# 6. 宣告容器運行時對外開放的 Port (FastAPI 預設是 8000)
EXPOSE 8000

# 7. 容器啟動時執行的指令 (注意：--host 0.0.0.0 是必填的，這樣才能接收來自容器外部的連線)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]