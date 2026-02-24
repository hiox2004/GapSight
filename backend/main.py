from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analytics, competitors, insights


app = FastAPI(title="GapSight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(analytics.router)
app.include_router(competitors.router)
app.include_router(insights.router)