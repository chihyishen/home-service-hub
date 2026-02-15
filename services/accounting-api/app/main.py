from fastapi import FastAPI
from .routers import transactions
from .database import engine, Base

# 建立資料庫表 (在生產環境建議使用 Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Accounting Service")

app.include_router(transactions.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Agent Accounting Service API"}
