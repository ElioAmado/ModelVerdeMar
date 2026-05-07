from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Verdemar AI Service")

# Definimos un modelo de datos (Opcional)
class Item(BaseModel):
    name: str
    price: float

@app.get("/")
def read_root():
    return {"message": "Bienvenido al servicio de FastAPI de Verdemar"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "query": q}

@app.post("/items/")
def create_item(item: Item):
    return {"message": f"Producto {item.name} creado", "total": item.price * 1.15}