from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chatbot, conversations, departments, evidences, kpi, reports, tasks, users
from core.config import get_settings
from core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(departments.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(evidences.router, prefix=settings.api_prefix)
app.include_router(kpi.router, prefix=settings.api_prefix)
app.include_router(chatbot.router, prefix=settings.api_prefix)
app.include_router(conversations.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
