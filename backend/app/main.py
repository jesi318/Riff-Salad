from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import riffs
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RiffVault API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(riffs.router, prefix="/api/riffs", tags=["riffs"])

@app.get("/")
def read_root():
    return {"message": "Welcome to RiffVault API"}
