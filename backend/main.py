from fastapi import FastAPI, Query, Path, HTTPException
from decimal import Decimal
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text, Numeric, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
load_dotenv()


database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3307")),
    database=os.getenv("DB_NAME"),
    query={"charset": "utf8mb4"},
)
engine = create_engine(database_url)
class Base(DeclarativeBase):
    pass
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")

app = FastAPI()

@app.get("/database-check")
def database_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar_one()
    return {"database": "mysql", "result": value}

class ProductCreate(BaseModel):
    sku: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")
    title: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(ge=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")

products: dict[str, ProductCreate] = {}

@app.get("/hello")
def hello():
    return {"message": "Hello, SellerPilot"}

@app.get("/greet")
def greet(name: str):
    return {"message": f"Hello, {name}"}

@app.get("/products")
def list_products(limit: int = Query(default=10, ge=1, le=100)):
    return list(products.values())[:limit]

@app.get("/products/{sku}")
def get_product(sku: str = Path(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")):
    product = products.get(sku)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product 

@app.post("/products", status_code=201)
def create_product(product: ProductCreate):
    if product.sku in products:
        raise HTTPException(status_code=409, detail="sku已存在")
    products[product.sku] = product
    return product
    return {"message": "商品创建成功", "product": product}

@app.delete("/products/{sku}", status_code=204)
def delete_product(
    sku: str = Path(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$",),):
    if sku not in products:
        raise HTTPException(status_code=404, detail="商品不存在")
    del products[sku]

@app.post("/database-products", status_code=201)
def create_database_product(product: ProductCreate):
    with Session(engine) as session:
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
        )

        session.add(database_product)
        session.commit()
        session.refresh(database_product)

        return {
            "id": database_product.id,
            "sku": database_product.sku,
            "title": database_product.title,
            "price": database_product.price,
            "currency": database_product.currency,
        }