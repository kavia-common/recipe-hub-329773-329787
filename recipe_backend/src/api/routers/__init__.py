from src.api.routers.auth import router as auth_router
from src.api.routers.favorites import router as favorites_router
from src.api.routers.recipes import router as recipes_router
from src.api.routers.tags import router as tags_router

all_routers = [
    auth_router,
    recipes_router,
    favorites_router,
    tags_router,
]
