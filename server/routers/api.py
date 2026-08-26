"""Main API routes — replace with your business logic."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/")
async def root() -> dict:
    return {"message": "API is running"}


# Example protected endpoint:
# @router.post("/items", dependencies=[Depends(verify_bearer_token)])
# async def create_item(...):
#     ...
