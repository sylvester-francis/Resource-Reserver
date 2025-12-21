"""Setup endpoints for first-run bootstrap and reopening setup."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import models, rbac, schemas, setup
from app.database import get_db
from app.services import UserService

setup_router = APIRouter(prefix="/setup", tags=["Setup"])


@setup_router.get("/status")
def get_setup_status(db: Session = Depends(get_db)):
    setup_complete, setup_reopened = setup.get_setup_status(db)
    user_count = db.query(models.User).count()
    return {
        "setup_complete": setup_complete,
        "setup_reopened": setup_reopened,
        "user_count": user_count,
    }


@setup_router.post("/initialize")
def initialize_setup(
    request: schemas.SetupInitializeRequest,
    db: Session = Depends(get_db),
    x_setup_token: str | None = Header(default=None, alias="X-Setup-Token"),
):
    setup_complete, setup_reopened = setup.get_setup_status(db)

    if setup_complete and not setup_reopened:
        raise HTTPException(status_code=400, detail="Setup already completed")

    if setup_reopened:
        valid, message = setup.validate_reopen_token(x_setup_token)
        if not valid:
            raise HTTPException(status_code=403, detail=message)

    if request.existing_username:
        existing_user = (
            db.query(models.User)
            .filter(models.User.username == request.existing_username.lower())
            .first()
        )
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        target_user = existing_user
    else:
        if not request.username or not request.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required",
            )
        user_service = UserService(db)
        target_user = user_service.create_user(
            schemas.UserCreate(username=request.username, password=request.password)
        )

    rbac.create_default_roles(db)
    rbac.assign_role(target_user.id, "admin", db)
    setup.mark_setup_complete(db)

    return {
        "message": "Setup completed successfully",
        "admin_user_id": target_user.id,
        "admin_username": target_user.username,
    }


@setup_router.post("/unlock")
def unlock_setup(
    db: Session = Depends(get_db),
    x_setup_token: str | None = Header(default=None, alias="X-Setup-Token"),
):
    setup_complete, _ = setup.get_setup_status(db)
    if not setup_complete:
        return {"message": "Setup is already open"}

    valid, message = setup.validate_reopen_token(x_setup_token)
    if not valid:
        raise HTTPException(status_code=403, detail=message)

    setup.mark_setup_reopened(db)
    return {"message": "Setup reopened"}
