from fastapi import FastAPI, Query, Path, HTTPException, Depends
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
import os
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import  engine, get_db
from models import Product

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
    price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    stock: int = Field(default=0, ge=0)
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

@app.get("/hello")
def hello():
    return {"message": "Hello, SellerPilot"}

@app.get("/greet")
def greet(name: str):
    return {"message": f"Hello, {name}"}

@app.post("/products", status_code=201, response_model=ProductRead)
def create_database_product(product: ProductCreate, session: Session = Depends(get_db)):
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
                           session: Session = Depends(get_db)):
    statement = select(Product).order_by(Product.id).limit(limit)
    database_products = session.scalars(statement).all()

    return database_products

@app.get("/products/{sku}", response_model=ProductRead)
def get_database_product(sku: str = Path(
                            min_length = 3,
                            max_length=30,
                            pattern = r"^[A-Za-z0-9-]+$" 
                        ),
                        session: Session = Depends(get_db)):
    product = session.scalar(select(Product).where(Product.sku == sku))
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

@app.delete("/products/{sku}", status_code=204)
def delete_database_product(sku: str = Path(
        min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$"),
        session: Session = Depends(get_db)):
    statement = select(Product).where(Product.sku == sku)
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
                   session: Session = Depends(get_db)):
    product = session.scalar(select(Product).where(Product.sku == sku))
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    product.title = product_data.title
    product.price = product_data.price
    product.currency = product_data.currency
    product.stock = product_data.stock

    session.commit()
    session.refresh(product)

    return product


