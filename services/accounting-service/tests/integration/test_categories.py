import requests
import random

BASE_URL = "http://127.0.0.1:8000/categories/"

def test_category_lifecycle():
    unique_name = f"測試分類_{random.randint(1000, 9999)}"
    # Create
    resp = requests.post(BASE_URL, json={"name": unique_name, "color": "#000"})
    assert resp.status_code == 200, f"Error: {resp.text}"
    new_cat = resp.json()
    cat_id = new_cat["id"]
    assert new_cat["name"] == unique_name

    # List
    cats = requests.get(BASE_URL).json()
    assert any(c["id"] == cat_id for c in cats)

    # Update
    updated_name = f"已修改_{unique_name}"
    resp = requests.put(f"{BASE_URL}{cat_id}", json={"name": updated_name, "color": "#111"})
    assert resp.status_code == 200
    updated_cat = resp.json()
    assert updated_cat["name"] == updated_name
    assert updated_cat["color"] == "#111"

    # Delete
    requests.delete(f"{BASE_URL}{cat_id}")
    cats_after = requests.get(BASE_URL).json()
    assert all(c["id"] != cat_id for c in cats_after)
