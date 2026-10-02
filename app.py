import os
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = FastAPI()

# AWS S3 設定 (從 .env 讀取)
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# CDN_DOMAIN 是你的 CloudFront 網域 (例如: dcdwayne.com)
CDN_DOMAIN = os.getenv("CDN_DOMAIN") 

s3_client = boto3.client(
    's3',
    region_name=S3_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

# 資料庫連線設定 (從 .env 讀取)
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "photo_board"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "")
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# ==========================================
# API 路由區塊
# ==========================================

# 首頁路由：當使用者訪問 / 時，回傳 index.html
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

# 1. 新增圖文 (POST)
@app.post("/api/posts")
async def create_post(
    text: str = Form(...), 
    image: UploadFile = File(...)
):
    try:
        # 1. 產生唯一的檔案名稱，避免覆蓋
        file_extension = image.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # 2. 上傳圖片到 S3
        s3_client.upload_fileobj(
            image.file,
            S3_BUCKET,
            unique_filename,
            ExtraArgs={"ContentType": image.content_type}
        )
        
        # 3. 將文字內容與「圖片的 Key」存入 RDS
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            sql = "INSERT INTO posts (text_content, image_key) VALUES (%s, %s)"
            cursor.execute(sql, (text, unique_filename))
            conn.commit()
            cursor.close()
            conn.close()
            
            return JSONResponse(status_code=201, content={"ok": True, "message": "上傳成功"})
        else:
            raise HTTPException(status_code=500, detail="Database connection failed")
            
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. 取得所有圖文 (GET)
@app.get("/api/posts")
async def get_posts():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        # 依照建立時間反向排序，最新的在最上面
        cursor.execute("SELECT id, text_content, image_key FROM posts ORDER BY created_at DESC")
        posts = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 組合前端需要的 CDN 圖片網址
        result = []
        for post in posts:
            result.append({
                "id": post["id"],
                "text": post["text_content"],
                "imageUrl": f"https://{CDN_DOMAIN}/{post['image_key']}" # 組合 CDN 網址
            })
            
        return result
    else:
        raise HTTPException(status_code=500, detail="Database connection failed")

# 3. 刪除特定圖文 (DELETE)
@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # 1. 先查出這筆留言的 image_key
        cursor.execute("SELECT image_key FROM posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        
        if not post:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Post not found")
            
        image_key = post["image_key"]
        
        try:
            # 2. 呼叫 S3 API 刪除實體圖片
            s3_client.delete_object(Bucket=S3_BUCKET, Key=image_key)
            
            # 3. 從 RDS 中刪除該筆資料
            cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
            conn.commit()
            
            return JSONResponse(status_code=200, content={"ok": True, "message": "刪除成功"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"刪除過程發生錯誤: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    else:
        raise HTTPException(status_code=500, detail="Database connection failed")

# ==========================================
# 網站圖示 (Favicon)
# ==========================================
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # 直接回傳 static 資料夾裡面的圖片
    return FileResponse("static/img/favicon.ico")

# 掛載前端靜態檔案 (設定路由為 "/" 時預設抓取 static/index.html)
app.mount("/static", StaticFiles(directory="static"), name="static")