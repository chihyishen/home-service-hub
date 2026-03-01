import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 載入環境變數 (優先讀取專案根目錄的 .env)
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

from .routers import transactions, cards, recurring, categories, payment_methods
from .database import engine, Base
from .tracing import setup_tracing

# 建立資料庫表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Home Service Hub - Accounting API",
    description="記帳與財務管理微服務。",
    version="1.2.0",
)

# 增加 CORS 中間件支援遠端開發
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 OpenTelemetry
setup_tracing(app=app, engine=engine)

# 註冊路由
app.include_router(transactions.router)
app.include_router(cards.router)
app.include_router(recurring.router)
app.include_router(categories.router)
app.include_router(payment_methods.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Home Service Hub - Accounting API",
        "docs": "/docs"
    }
