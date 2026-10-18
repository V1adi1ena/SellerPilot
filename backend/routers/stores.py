from fastapi import Query, Path, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from models import Store, User
from fastapi import APIRouter
from dependencies import get_current_user
from schemas import StoreCreate, StoreRead

router = APIRouter(tags=["stores"])

@router.post("/stores", status_code=201, response_model=StoreRead)
def create_store(
    store_data: StoreCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    store = Store(
        name=store_data.name,
        platform=store_data.platform,
        owner_id=current_user.id
    )

    session.add(store)
    session.commit()
    session.refresh(store)

    return store


@router.get("/stores", response_model=list[StoreRead])
def list_stores(
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    statement = (select(Store)
                 .where(Store.owner_id == current_user.id)
                 .order_by(Store.id)
                 .limit(limit)
    )
    return session.scalars(statement).all()


@router.get("/stores/{store_id}", response_model=StoreRead)
def get_store(
    store_id: int = Path(ge=1),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    store = session.scalar(
        select(Store)
        .where(
            Store.id == store_id,
            Store.owner_id == current_user.id)
    )
    if store is None:
        raise HTTPException(status_code=404, detail="店铺不存在")

    return store

