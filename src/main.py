from fastapi import FastAPI
from src.controller.document_controller import document_router# your router file
from src.controller.auth_controller import auth_router
def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG FastAPI",
        version="0.1.0"
    )

    # Register routes
    app.include_router(document_router, prefix="/api", tags=["documents"])
    app.include_router(auth_router, tags=["authentication"])
    return app

app = create_app()
