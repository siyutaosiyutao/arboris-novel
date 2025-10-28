from fastapi import APIRouter

from . import admin, auth, auto_generator, llm_config, novels, updates, writer

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(novels.router)
api_router.include_router(writer.router)
api_router.include_router(admin.router)
api_router.include_router(updates.router)
api_router.include_router(llm_config.router)
api_router.include_router(auto_generator.router)
