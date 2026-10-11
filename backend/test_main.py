import pytest
from fastapi.testclient import TestClient

from main import app
from models import Product, Store
from database import database_url, get_db

from decimal import Decimal
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch
from uuid import uuid4

test_engine = create_engine(
    database_url.set(database="sellerpilot_test")
)


def override_get_db():
    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def use_test_database():
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)

client = TestClient(app)


def test_product_lifecycle():
    sku = f"TEST-{uuid4().hex[:12]}"
    product_data = {
        "sku": sku,
        "title": "Running Shoes",
        "price": "29.99",
        "currency": "USD",
        "stock": 5,
    }
    try:
        create_response = client.post("/products", json=product_data)
        assert create_response.status_code == 201
        assert create_response.json()["sku"] == sku

        detail_response = client.get(f"/products/{sku}")
        assert detail_response.status_code == 200
        assert detail_response.json()["title"] == "Running Shoes"

        duplicate_response = client.post("/products", json=product_data)
        assert duplicate_response.status_code == 409

        update_response = client.put(
            f"/products/{sku}",
            json={
                "title": "Updated Shoes",
                "price": "39.99",
                "currency": "EUR",
                "stock": 5,
            },
        )
        assert update_response.status_code == 200

        updated_response = client.get(f"/products/{sku}")
        assert updated_response.status_code == 200

        updated_product = updated_response.json()
        assert updated_product["sku"] == sku
        assert updated_product["title"] == "Updated Shoes"
        assert Decimal(str(updated_product["price"])) == Decimal("39.99")
        assert updated_product["currency"] == "EUR"
        assert updated_product["stock"] == 5

        delete_response = client.delete(f"/products/{sku}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/products/{sku}")
        assert missing_response.status_code == 404

    finally:
        client.delete(f"/products/{sku}")

def test_reject_negative_price():
    response = client.post(
        "/products",
        json={
            "sku": "SKU-NEG",
            "title": "Running Shoes",
            "price": "-10",
            "currency": "USD",
        },
    )

    assert response.status_code == 422
    missing_response = client.get("/products/SKU-NEG")
    assert missing_response.status_code == 404

def test_handle_integrity_error():
    sku = f"TEST-{uuid4().hex[:12]}"

    with patch( # 只能说明当出现IntegrityError时会返回409
        "main.Session.commit",
        side_effect=IntegrityError("INSERT", {}, Exception("test")),
    ), patch("main.Session.rollback") as rollback_mock:
        response = client.post(
            "/products",
            json={
                "sku": sku,
                "title": "Test Product",
                "price": "10.00",
                "currency": "USD",
            },
        )

        assert response.status_code == 409
        rollback_mock.assert_called_once()

def test_database_sku_unique():
    sku = f"TEST-{uuid4().hex[:12]}"
    try:
        with Session(test_engine) as session:
            first_product = Product(
                sku=sku,
                title="First Product",
                price="10.00",
                currency="USD",
            )
            session.add(first_product)
            session.commit()

            second_product = Product(
                sku=sku,
                title="Second Product",
                price="20.00",
                currency="USD",
            )
            session.add(second_product)

            with pytest.raises(IntegrityError):
                session.commit()

            session.rollback()
    finally:
        with Session(test_engine) as session:
            product = session.scalar(
                select(Product).where(Product.sku == sku)
            )
            if product is not None:
                session.delete(product)
                session.commit()

def test_update_requires_all_fields():
    response = client.put(
        "/products/TEST-MISSING-FIELDS",
        json={"price": "19.99"},
    )

    assert response.status_code == 422

    errors = response.json()["detail"]
    missing_fields = {
        error["loc"][-1]
        for error in errors
        if error["type"] == "missing"
    }

    assert missing_fields == {"title", "currency", "stock"}

def test_reject_price_with_too_many_decimal_places():
    response = client.post(
        "/products",
        json={
            "sku": f"TEST-{uuid4().hex[:12]}",
            "title": "Test Product",
            "price": "19.999",
            "currency": "USD",
        },
    )

    assert response.status_code == 422

    errors = response.json()["detail"]
    assert any(
        error["loc"] == ["body", "price"]
        and error["type"] == "decimal_max_places"
        for error in errors
    )

def test_filter_products_by_store():
    store_ids = []
    skus = []

    try:
        for name in ["Test Store A", "Test Store B"]:
            store_response = client.post(
                "/stores",
                json={"name": name, "platform": "amazon"},
            )
            assert store_response.status_code == 201

            store_id = store_response.json()["id"]
            store_ids.append(store_id)

            sku = f"TEST-{uuid4().hex[:12]}"
            skus.append(sku)

            product_response = client.post(
                "/products",
                json={
                    "sku": sku,
                    "title": "Test Product",
                    "price": "10.00",
                    "store_id": store_id,
                },
            )
            assert product_response.status_code == 201

        response = client.get(
            "/products",
            params={"store_id": store_ids[0]},
        )
        assert response.status_code == 200

        products = response.json()
        assert len(products) == 1
        assert products[0]["sku"] == skus[0]
        assert products[0]["store_id"] == store_ids[0]

    finally:
        with Session(test_engine) as session:
            session.execute(
                delete(Product).where(Product.sku.in_(skus))
            )
            session.execute(
                delete(Store).where(Store.id.in_(store_ids))
            )
            session.commit()

