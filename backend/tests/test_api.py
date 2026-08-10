import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert "message" in json_data
    assert "version" in json_data

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert "services" in json_data

def test_list_documents_endpoint():
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "documents" in json_data["data"]

def test_upload_and_delete_workflow():
    content = b"This is a test document content for RAG integration testing. It covers AI, Machine Learning and Data Science."
    files = {"files": ("test_doc.txt", content, "text/plain")}
    
    upload_res = client.post("/api/v1/upload", files=files, data={"collection_id": "test_collection"})
    assert upload_res.status_code == 201
    upload_json = upload_res.json()
    assert upload_json["status"] == "success"
    uploaded_files = upload_json["data"]["uploaded_files"]
    assert len(uploaded_files) > 0
    file_id = uploaded_files[0]["file_id"]
    
    list_res = client.get("/api/v1/documents", params={"collection_id": "test_collection"})
    assert list_res.status_code == 200
    docs = list_res.json()["data"]["documents"]
    found = any(d["file_id"] == file_id for d in docs)
    assert found
    
    delete_res = client.delete(f"/api/v1/documents/{file_id}", params={"collection_id": "test_collection"})
    assert delete_res.status_code == 200
    delete_json = delete_res.json()
    assert delete_json["status"] == "success"
