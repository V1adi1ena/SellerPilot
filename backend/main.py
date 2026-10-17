from fastapi import (
    FastAPI,
    Query, 
    Path,
    HTTPException,
    Depends,
    File, 
    UploadFile,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from imports import(
    MAX_FILE_BYTES,
    CsvImportError,
    ImportConflictError,
    import_orders_csv,
)
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, AwareDatetime

import os
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import  engine, get_db
from models import Product, Store, User
from secuity import hash_password, verify_password, create_access_token, decode_access_token
from services import StoreNotFoundError, list_low_stock_products
from order_items_import import parse_order_items_csv, import_order_items_csv
from analytics import list_product_sales, list_store_orders, summarize_sales
from llm import ModelError
from agent import AgentError, run_store_agent
from conversations import (
    ConversationConflictError,
    ConversationError,
    ConversationNotFoundError,
    run_conversation_agent,
)
from title_drafts import (
    ProductNotFoundError,
    TitleDraftError,
    TitleDraftSaveError,
    TitleDraftConflictError,
    TitleDraftNotFoundError,
    create_product_title_draft,
    get_product_title_draft,
    confirm_product_title_draft,
)

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    session: Session = Depends(get_db),
):
    auth_error = HTTPException(
        status_code=401,
        detail="登录凭证无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise auth_error

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        if user_id < 1:
            raise ValueError("无效用户 ID")

    except (InvalidTokenError, ValueError, KeyError, TypeError):
        raise auth_error

    user = session.get(User, user_id)
    if user is None:
        raise auth_error

    return user

app = FastAPI(swagger_ui_parameters={"persistAuthorization":True})

@app.get("/database-check")
def database_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar_one()
    return {"database": "mysql", "result": value}

class ProductCreate(BaseModel):
    sku: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")
    title: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    stock: int = Field(default=0, ge=0)
    store_id: int = Field(ge=1)
class ProductUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    stock: int = Field(ge=0)
class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    title: str
    price: Decimal
    currency: str
    stock: int
    store_id: int|None

class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    platform: str = Field(pattern=r"^(amazon|shopify)$")
class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    platform: str
    owner_id: int|None

class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    password: str = Field(min_length=8, max_length=128)
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str    
class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)

class TokenRead(BaseModel):
    access_token: str
    token_type: str
class AgentQuestion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    message: str=Field(min_length=1, max_length=2000)
    conversation_id:int|None=Field(default=None, ge=1, strict=True)

class TitleDraftConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: bool = Field(strict=True)

def owned_products_query(user_id:int):
    return (select(Product)
            .join(Store, Product.store_id == Store.id)
            .where(Store.owner_id == user_id)
    )

@app.get("/hello")
def hello():
    return {"message": "Hello, SellerPilot"}

@app.get("/greet")
def greet(name: str):
    return {"message": f"Hello, {name}"}

@app.post("/products", status_code=201, response_model=ProductRead)
def create_database_product(product: ProductCreate,
                            session: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user),
                            ):
    store = session.scalar(
        select(Store).where(
            Store.id == product.store_id,
            Store.owner_id == current_user.id,
        )
    )
    if store is None: 
            raise HTTPException(status_code=404, detail="店铺不存在")
    existing_product = session.scalar(
        select(Product).where(Product.sku == product.sku)
    )
    if existing_product is not None:
        raise HTTPException(status_code=409, detail="数据库中已存在该 SKU")
        
    database_product = Product(
        sku=product.sku,
        title=product.title,
        price=product.price,
        currency=product.currency,
        stock=product.stock,
        store_id = product.store_id
    )

    session.add(database_product)
    try: session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="写入违反数据库约束")
    session.refresh(database_product)

    return database_product

@app.get("/products", response_model=list[ProductRead])
def list_database_products(limit:int=Query(default=10, ge=1, le=100),
                           store_id:int|None=Query(default=None, ge=1),
                           session: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user),
                           ):
    statement = owned_products_query(current_user.id)
    if store_id is not None:
        statement = statement.where(Product.store_id == store_id)
    statement = statement.order_by(Product.id).limit(limit)
    return session.scalars(statement).all()

@app.get("/products/{sku}", response_model=ProductRead)
def get_database_product(sku: str = Path(
                            min_length = 3,
                            max_length=30,
                            pattern = r"^[A-Za-z0-9-]+$" 
                        ),
                        session: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user),):
    statement = owned_products_query(current_user.id).where(Product.sku == sku)
    product = session.scalar(statement)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

@app.delete("/products/{sku}", status_code=204)
def delete_database_product(sku: str = Path(
        min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$"),
        session: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
    statement = owned_products_query(current_user.id).where(Product.sku == sku)
    product = session.scalar(statement)

    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    session.delete(product)
    session.commit()

@app.put("/products/{sku}", response_model=ProductRead)
def updata_product(product_data: ProductUpdate,
                   sku: str = Path(
                       min_length=3, 
                       max_length=30,
                       pattern=r"^[A-Za-z0-9-]+$",
                   ),
                   session: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user),
                   ):
    statement = owned_products_query(current_user.id).where(Product.sku == sku)
    product = session.scalar(statement)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    product.title = product_data.title
    product.price = product_data.price
    product.currency = product_data.currency
    product.stock = product_data.stock

    session.commit()
    session.refresh(product)

    return product

@app.post("/stores", status_code=201, response_model=StoreRead)
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

@app.get("/stores", response_model=list[StoreRead])
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

@app.get("/stores/{store_id}", response_model=StoreRead)
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

@app.post("/auth/register", status_code=201, response_model=UserRead)
def register_user(
    user_data: UserCreate,
    session: Session=Depends(get_db)
):
    existing_user = session.scalar(
        select(User).where(User.username==user_data.username)
    )
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="用户名已经存在")

    user = User(
        username = user_data.username,
        password_hash = hash_password(user_data.password),
    )
    session.add(user)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="用户名已存在")

    session.refresh(user)
    return user

@app.post("/auth/login", response_model=TokenRead)
def login_user(
    login_data: UserLogin,
    session: Session = Depends(get_db),
):
    user = session.scalar(
        select(User).where(User.username == login_data.username)
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
        )

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }

@app.get("/auth/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.get(
    "/stores/{store_id}/products/low-stock",
    response_model=list[ProductRead],
)
def get_low_stock_products(
    store_id: int = Path(ge=1),
    threshold: int = Query(default=10, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return list_low_stock_products(
            session,
            user_id=current_user.id,
            store_id=store_id,
            threshold=threshold,
            limit=limit,
        )
    except StoreNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

@app.post("/stores/{store_id}/imports/orders")
def upload_orders_csv(
    store_id: int = Path(ge=1),
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=422,
                detail="请上传 .csv 文件",
            )

        content = file.file.read(MAX_FILE_BYTES + 1)

        return import_orders_csv(
            session,
            user_id=current_user.id,
            store_id=store_id,
            content=content,
        )

    except StoreNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except CsvImportError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "errors": exc.errors,
            },
        ) from exc

    except ImportConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

@app.post("/stores/{store_id}/imports/order-items")
def upload_order_items_csv(
    store_id: int = Path(ge=1),
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=422,
                detail="请上传 .csv 文件",
            )

        content = file.file.read(MAX_FILE_BYTES + 1)

        return import_order_items_csv(
            session,
            user_id=current_user.id,
            store_id=store_id,
            content=content,
        )

    except StoreNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except CsvImportError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "errors": exc.errors,
            },
        ) from exc

    except ImportConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@app.get("/stores/{store_id}/orders")
def get_store_orders(
    store_id: int = Path(ge=1),
    start_at: AwareDatetime = Query(...),
    end_at: AwareDatetime = Query(...),
    status: Literal["pending", "paid", "shipped", "cancelled"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=2147483647),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return list_store_orders(session, user_id=current_user.id, store_id=store_id,
            start_at=start_at, end_at=end_at, status=status, limit=limit, offset=offset)
    except StoreNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/stores/{store_id}/sales/summary")
def get_sales_summary(
    store_id: int = Path(ge=1),
    start_at: AwareDatetime = Query(...),
    end_at: AwareDatetime = Query(...),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return summarize_sales(session, user_id=current_user.id, store_id=store_id,
                               start_at=start_at, end_at=end_at)
    except StoreNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/stores/{store_id}/sales/products")
def get_product_sales(
    store_id: int = Path(ge=1),
    start_at: AwareDatetime = Query(...),
    end_at: AwareDatetime = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=2147483647),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return list_product_sales(session, user_id=current_user.id, store_id=store_id,
            start_at=start_at, end_at=end_at, limit=limit, offset=offset)
    except StoreNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



# query_store_agent        接收请求，取得登录用户和地址中的店铺编号
#         ↓
# run_conversation_agent   检查权限、读取会话历史
#         ↓
# run_store_agent          组织消息，请模型选择工具
#         ↓
# execute_tool             校验工具名称和参数，执行对应函数
#         ↓
# summarize_sales          再次检查权限，查询销售汇总
@app.post("/store/{store_id}/agent/query")
def query_store_agent(
    body: AgentQuestion,
    store_id: int=Path(ge=1),
    session: Session=Depends(get_db),
    current_usr: User=Depends(get_current_user),
):
    try:
        return run_conversation_agent(
            session,
            user_id=current_usr.id,
            store_id=store_id,
            question=body.message,
            conversation_id=body.conversation_id,
        )
    except (StoreNotFoundError, ConversationNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConversationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ConversationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (ModelError, AgentError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    

@app.post("/stores/{store_id}/products/{product_id}/title-drafts", status_code=201)
def generate_product_title_draft(
    store_id: int = Path(ge=1),
    product_id: int = Path(ge=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return create_product_title_draft(
            session,
            user_id=current_user.id,
            store_id=store_id,
            product_id=product_id,
        )
    except (StoreNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ModelError, TitleDraftError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TitleDraftSaveError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get("/stores/{store_id}/title-drafts/{draft_id}")
def read_product_title_draft(
    store_id: int = Path(ge=1),
    draft_id: int = Path(ge=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_product_title_draft(
            session, user_id=current_user.id, store_id=store_id, draft_id=draft_id,
        )
    except (StoreNotFoundError, TitleDraftNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/stores/{store_id}/title-drafts/{draft_id}/confirm")
def apply_product_title_draft(
    body: TitleDraftConfirmation,
    store_id: int = Path(ge=1),
    draft_id: int = Path(ge=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return confirm_product_title_draft(
            session, user_id=current_user.id, store_id=store_id,
            draft_id=draft_id, confirmed=body.confirmed,
        )
    except (StoreNotFoundError, TitleDraftNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TitleDraftConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TitleDraftSaveError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


