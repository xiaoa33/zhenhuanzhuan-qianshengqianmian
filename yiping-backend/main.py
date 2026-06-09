import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import asr, chat, synthesize, digital_human, summary

app = FastAPI(title="甄嬛传·千声千面 后端服务")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建静态目录（首次运行时自动创建）
os.makedirs("static/audio", exist_ok=True)
os.makedirs("static/video", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(chat.router)
app.include_router(asr.router)
app.include_router(synthesize.router)
app.include_router(digital_human.router)
app.include_router(summary.router)


@app.get("/")
def health():
    return {"status": "ok", "mock": os.getenv("USE_MOCK", "true")}
