from fastapi.testclient import TestClient
from main import app, products

client = TestClient(app)

def test_product_lifecycle():
    products.clear()

    product_data = {
        "sku": "SKU-001",
        "title": "Running Shoes",
        "price": "29.99",
        "currency": "USD",
    }

    create_response = client.post("/products", json=product_data)
    assert create_response.status_code == 201
    assert create_response.json()["sku"] == "SKU-001"

    list_response = client.get("/products")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    duplicate_response = client.post("/products", json=product_data)
    assert duplicate_response.status_code == 409

    delete_response = client.delete("/products/SKU-001")
    assert delete_response.status_code == 204

    missing_response = client.get("/products/SKU-001")
    assert missing_response.status_code == 404