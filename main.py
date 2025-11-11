from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="A minimal FastAPI backend"
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.ALLOWED_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to FastAPI", "status": "running"}

@app.get("/health")
def health_check():
    return {"message": "Application is running.", "status": "healthy"}