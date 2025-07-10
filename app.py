    
# FastAPI implementation for Simple Books API proxy

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict
import uuid

app = FastAPI()

# In-memory data stores
books = [
    {"id": 1, "name": "The Great Gatsby", "type": "fiction", "available": True},
    {"id": 2, "name": "A Brief History of Time", "type": "non-fiction", "available": True},
    {"id": 3, "name": "1984", "type": "fiction", "available": True},
    {"id": 4, "name": "Sapiens", "type": "non-fiction", "available": True},
    {"id": 5, "name": "To Kill a Mockingbird", "type": "fiction", "available": True},
]
orders: Dict[str, Dict] = {}
api_clients: Dict[str, Dict] = {}

# Status endpoint
@app.get("/status")
async def get_status():
    return {"status": "OK"}

# List of books
@app.get("/books")
async def get_books(type: Optional[str] = None, limit: Optional[int] = None):
    filtered = books
    if type:
        filtered = [b for b in filtered if b["type"] == type]
    if limit:
        filtered = filtered[:limit]
    return filtered

# Get a single book
@app.get("/books/{book_id}")
async def get_book(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")

# Register API client
@app.post("/api-clients/")
async def register_client(request: Request):
    data = await request.json()
    client_email = data.get("clientEmail")
    client_name = data.get("clientName")
    if not client_email or not client_name:
        raise HTTPException(status_code=400, detail="clientEmail and clientName required.")
    # Check for existing
    for client in api_clients.values():
        if client["clientEmail"] == client_email:
            raise HTTPException(status_code=409, detail="API client already registered.")
    token = str(uuid.uuid4())
    api_clients[token] = {"clientEmail": client_email, "clientName": client_name}
    return {"accessToken": token}

# Submit an order (requires auth)
@app.post("/orders")
async def submit_order(request: Request, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1]
    if token not in api_clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    data = await request.json()
    book_id = data.get("bookId")
    customer_name = data.get("customerName")
    if not book_id or not customer_name:
        raise HTTPException(status_code=400, detail="bookId and customerName required.")
    # Check book exists
    book = next((b for b in books if b["id"] == book_id), None)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    order_id = str(uuid.uuid4())[:20]
    order = {"id": order_id, "bookId": book_id, "customerName": customer_name}
    orders[order_id] = order
    return {"orderId": order_id}

# Get all orders (requires auth)
@app.get("/orders")
async def get_orders(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1]
    if token not in api_clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    return list(orders.values())

# Get an order (requires auth)
@app.get("/orders/{order_id}")
async def get_order(order_id: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1]
    if token not in api_clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order

# Update an order (requires auth)
@app.patch("/orders/{order_id}")
async def update_order(order_id: str, request: Request, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1]
    if token not in api_clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    data = await request.json()
    customer_name = data.get("customerName")
    if customer_name:
        order["customerName"] = customer_name
    return order

# Delete an order (requires auth)
@app.delete("/orders/{order_id}")
async def delete_order(order_id: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1]
    if token not in api_clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found.")
    del orders[order_id]
    return JSONResponse(status_code=204, content={})

