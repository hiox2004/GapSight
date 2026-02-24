from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analytics, competitors, insights, reports


app = FastAPI(title="GapSight API")


origins = [
    "http://localhost:5173",
    "https://gapsight.vercel.app",        # replace with your actual Vercel URL
    "https://gapsight-*.vercel.app",       # covers preview deployments too
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
app.include_router(reports.router)