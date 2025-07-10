
# FastAPI implementation for Simple Books API proxy

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict
import uuid

app = FastAPI()

# In-memory data stores
books = [
    {
        "id": 1,
        "name": "The Russian",
        "author": "James Patterson and James O. Born",
        "isbn": "1780899475",
        "type": "fiction",
        "price": 12.98,
        "current-stock": 12,
        "available": True
    },
    {
        "id": 2,
        "name": "Where the Crawdads Sing",
        "author": "Delia Owens",
        "isbn": "0735219095",
        "type": "fiction",
        "price": 15.99,
        "current-stock": 8,
        "available": True
    },
    {
        "id": 3,
        "name": "The Vanishing Half",
        "author": "Brit Bennett",
        "isbn": "0525536299",
        "type": "fiction",
        "price": 13.99,
        "current-stock": 5,
        "available": True
    },
    {
        "id": 4,
        "name": "The Midnight Library",
        "author": "Matt Haig",
        "isbn": "0525559477",
        "type": "fiction",
        "price": 14.99,
        "current-stock": 10,
        "available": True
    },
    {
        "id": 5,
        "name": "Educated",
        "author": "Tara Westover",
        "isbn": "0399590501",
        "type": "non-fiction",
        "price": 11.99,
        "current-stock": 7,
        "available": True
    },
    {
        "id": 6,
        "name": "Becoming",
        "author": "Michelle Obama",
        "isbn": "1524763136",
        "type": "non-fiction",
        "price": 16.99,
        "current-stock": 6,
        "available": True
    },
    {
        "id": 7,
        "name": "Sapiens",
        "author": "Yuval Noah Harari",
        "isbn": "0062316095",
        "type": "non-fiction",
        "price": 18.99,
        "current-stock": 9,
        "available": True
    },
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
    allowed_types = {"fiction", "non-fiction"}
    if type and type not in allowed_types:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid value for query parameter 'type'. Must be one of: fiction, non-fiction."
            },
        )
    if limit is not None:
        if not (1 <= limit <= 20):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid value for query parameter 'limit'. Must be between 1 and 20."
                },
            )
    filtered = books
    if type:
        filtered = [b for b in filtered if b["type"] == type]
    if limit:
        filtered = filtered[:limit]
    # Return only basic details for all books
    basic_fields = ("id", "name", "type", "available")
    return [{k: b[k] for k in basic_fields} for b in filtered]

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

