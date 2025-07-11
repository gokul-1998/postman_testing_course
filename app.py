
# FastAPI implementation for Simple Books API proxy

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict

import uuid
import json
import os
from fastapi import status

app = FastAPI()

# File paths
PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), 'db', 'products.json')
ORDERS_FILE = os.path.join(os.path.dirname(__file__), 'db', 'orders.json')

# Middleware to load data before every request
@app.middleware("http")
async def load_data_middleware(request, call_next):
    global books, orders
    # Load books
    if not os.path.exists(PRODUCTS_FILE):
        raise FileNotFoundError(f"Products file not found: {PRODUCTS_FILE}")
    with open(PRODUCTS_FILE, 'r') as f:
        try:
            books = json.load(f)
        except Exception:
            raise ValueError(f"Error loading products from {PRODUCTS_FILE}")
    # Load orders as dict keyed by id
    if not os.path.exists(ORDERS_FILE):
        raise FileNotFoundError(f"Orders file not found: {ORDERS_FILE}")
    with open(ORDERS_FILE, 'r') as f:
        try:
            orders_list = json.load(f)
            if isinstance(orders_list, list):
                orders = {o["id"]: o for o in orders_list if "id" in o}
            elif isinstance(orders_list, dict):
                orders = orders_list
            else:
                orders = {}
        except Exception:
            raise ValueError(f"Error loading orders from {ORDERS_FILE}")
    response = await call_next(request)
    return response

API_CLIENTS_FILE = os.path.join(os.path.dirname(__file__), 'db', 'api_clients.json')
def load_api_clients():
    if not os.path.exists(API_CLIENTS_FILE):
        return {}
    with open(API_CLIENTS_FILE, 'r') as f:
        try:
            data = json.load(f)
            return {c["token"]: c for c in data}
        except Exception:
            return {}


def save_api_clients(clients_dict):
    data = list(clients_dict.values())
    with open(API_CLIENTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Save orders to file
def save_orders(orders_dict):
    # Save as a list of order objects
    with open(ORDERS_FILE, 'w') as f:
        json.dump(list(orders_dict.values()), f, indent=2)

api_clients: Dict[str, Dict] = load_api_clients()

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
    # Always reload from file to avoid race conditions
    clients = load_api_clients()
    for client in clients.values():
        if client["clientEmail"] == client_email:
            raise HTTPException(status_code=409, detail="API client already registered.")
    token = str(uuid.uuid4())
    client_obj = {"token": token, "clientEmail": client_email, "clientName": client_name}
    clients[token] = client_obj
    save_api_clients(clients)
    return {"accessToken": token}

# Submit an order (requires auth)
@app.post("/orders")
async def submit_order(request: Request, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1].strip()
    clients = load_api_clients()
    print(f"Token from header: '{token}'")
    print(f"Tokens in file: {list(clients.keys())}")
    if token not in clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing bookId."})
    book_id = data.get("bookId")
    customer_name = data.get("customerName")
    if not book_id:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing bookId."})
    if not customer_name:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing customerName."})
    # Check book exists and is available
    book = next((b for b in books if b["id"] == book_id), None)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    if not book.get("available", False):
        return JSONResponse(status_code=404, content={"error": "This Book is not in stock.Try ordering later."})
    order_id = str(uuid.uuid4())[:20]
    order = {"id": order_id, "bookId": book_id, "customerName": customer_name}
    orders[order_id] = order
    save_orders(orders)
    return JSONResponse(status_code=201, content={"created": True, "orderId": order_id})

# Get all orders (requires auth)
@app.get("/orders")
async def get_orders(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1].strip()
    clients = load_api_clients()
    print(f"Token from header: '{token}'")
    print(f"Tokens in file: {list(clients.keys())}")
    if token not in clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    return list(orders.values())

# Get an order (requires auth)
@app.get("/orders/{order_id}")
async def get_order(order_id: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1].strip()
    clients = load_api_clients()
    print(f"Token from header: '{token}'")
    print(f"Tokens in file: {list(clients.keys())}")
    if token not in clients:
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
    token = authorization.split(" ", 1)[1].strip()
    clients = load_api_clients()
    print(f"Token from header: '{token}'")
    print(f"Tokens in file: {list(clients.keys())}")
    if token not in clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    data = await request.json()
    customer_name = data.get("customerName")
    if customer_name:
        order["customerName"] = customer_name
        save_orders(orders)
    return order

# Delete an order (requires auth)
@app.delete("/orders/{order_id}")
async def delete_order(order_id: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.split(" ", 1)[1].strip()
    clients = load_api_clients()
    print(f"Token from header: '{token}'")
    print(f"Tokens in file: {list(clients.keys())}")
    if token not in clients:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found.")
    del orders[order_id]
    save_orders(orders)
    return JSONResponse(status_code=204, content={})

