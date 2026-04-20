import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 載入環境變數
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

from .routers import portfolio, health
from .database import engine, Base
from .tracing import setup_tracing

# 建立資料庫表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Home Service Hub - Stock Portfolio API",
    description="投資組合管理微服務。",
    version="1.0.0",
)

# CORS
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
app.include_router(portfolio.router)
app.include_router(health.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Home Service Hub - Stock Portfolio API",
        "docs": "/docs"
    }
