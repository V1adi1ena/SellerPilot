"""应用入口：只负责注册路由和基础连通性接口。"""
from fastapi import FastAPI
from sqlalchemy import text
from database import engine
from routers import auth, stores, products, imports, analytics, agent, titles

app = FastAPI(swagger_ui_parameters={"persistAuthorization": True})
for module in (auth, stores, products, imports, analytics, agent, titles):
    app.include_router(module.router)

@app.get("/database-check")
def database_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar_one()
    return {"database": "mysql", "result": value}


@app.get("/hello")
def hello():
    return {"message": "Hello, SellerPilot"}


@app.get("/greet")
def greet(name: str):
    return {"message": f"Hello, {name}"}

