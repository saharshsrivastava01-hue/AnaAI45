import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DATABASE_PATH", "nexus.db")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
CURRENCY = os.getenv("STORE_CURRENCY", "INR")

app = FastAPI(title="NEXUS Global Commerce API", version="0.1.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=origins != ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            price REAL NOT NULL CHECK(price >= 0), currency TEXT NOT NULL,
            image_url TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL, email TEXT NOT NULL,
            items_json TEXT NOT NULL, total REAL NOT NULL,
            currency TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )""")
        count = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
        if count == 0:
            conn.executemany(
                "INSERT INTO products(name,description,price,currency,image_url) VALUES(?,?,?,?,?)",
                [
                    ("Everyday Essential Tee", "Illustrative catalogue item. Confirm stock before selling.", 799, CURRENCY, ""),
                    ("Minimal Carry Tote", "Illustrative catalogue item. Confirm stock before selling.", 499, CURRENCY, ""),
                    ("Studio Overshirt", "Illustrative catalogue item. Confirm stock before selling.", 1499, CURRENCY, ""),
                ],
            )

init_db()

class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    price: float = Field(ge=0)
    currency: str = Field(default=CURRENCY, min_length=3, max_length=3)
    image_url: str = Field(default="", max_length=1000)

class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=20)

class OrderIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    items: list[OrderItem] = Field(min_length=1, max_length=30)

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

@app.get("/health")
def health():
    return {"status": "ok", "service": "nexus-api", "ai_configured": bool(AI_API_KEY)}

@app.get("/api/products")
def products():
    with db() as conn:
        rows = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

@app.post("/api/products")
def add_product(product: ProductIn, x_admin_token: Optional[str] = Header(default=None)):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Admin token is not configured or is invalid.")
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO products(name,description,price,currency,image_url) VALUES(?,?,?,?,?)",
            (product.name, product.description, product.price, product.currency.upper(), product.image_url),
        )
        return {"id": cur.lastrowid, "created": True}

@app.post("/api/orders")
def create_order(order: OrderIn):
    import json
    with db() as conn:
        total = 0.0
        resolved = []
        for item in order.items:
            row = conn.execute("SELECT id,name,price,currency FROM products WHERE id=? AND active=1", (item.product_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} is unavailable.")
            total += float(row["price"]) * item.quantity
            resolved.append({"product_id": row["id"], "name": row["name"], "unit_price": row["price"], "quantity": item.quantity})
        currencies = {conn.execute("SELECT currency FROM products WHERE id=?", (x["product_id"],)).fetchone()["currency"] for x in resolved}
        if len(currencies) != 1:
            raise HTTPException(status_code=400, detail="An order must use one currency.")
        currency = currencies.pop()
        cur = conn.execute(
            "INSERT INTO orders(customer_name,email,items_json,total,currency,status,created_at) VALUES(?,?,?,?,?,?,?)",
            (order.customer_name, order.email, json.dumps(resolved), round(total, 2), currency, "pending_payment", datetime.now(timezone.utc).isoformat()),
        )
        return {"order_id": cur.lastrowid, "total": round(total, 2), "currency": currency,
                "status": "pending_payment", "notice": "No payment has been collected. Connect a verified payment gateway before accepting real orders."}

@app.post("/api/assistant")
async def assistant(chat: ChatIn):
    if not AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI is not configured. Add AI_API_KEY to the server environment.")
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": "You are the NEXUS store assistant. Help customers understand products, sizing, shipping and returns. Never invent stock, delivery dates, discounts, policies, or payment status. If data is missing, say so."},
            {"role": "user", "content": chat.message},
        ],
        "temperature": 0.4,
    }
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        try:
            response = await client.post(f"{AI_BASE_URL.rstrip('/')}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return {"answer": answer, "model": AI_MODEL}
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail=f"AI provider returned HTTP {exc.response.status_code}. Check server configuration.")
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            raise HTTPException(status_code=502, detail="Could not get a valid response from the AI provider.")

@app.get("/api/admin/summary")
def admin_summary(x_admin_token: Optional[str] = Header(default=None)):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Admin token is not configured or is invalid.")
    with db() as conn:
        products_count = conn.execute("SELECT COUNT(*) n FROM products").fetchone()["n"]
        orders = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(total),0) total FROM orders").fetchone()
        return {"products": products_count, "orders": orders["n"], "order_value_pending_payment": round(orders["total"], 2),
                "currency": CURRENCY, "note": "Order value is not collected revenue; payment integration is not enabled."}
