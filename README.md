# CartPilot AI: Your Intelligent Shopping and Payment Agent

CartPilot AI is an AI-powered shopping assistant built for a hackathon.
It helps users search products in natural language, browse a catalog,
get recommendations and manage a cart.

## Current status: Day 1 foundation

| Feature | Status |
|---|---|
| Product catalog (20 sample products, search, filters, sorting) | Working |
| Shopping cart (quantities, totals, server-side validation) | Working |
| AI shopping assistant | **Demo only.** Rule-based logic, *not* a real LLM |
| Gemini AI integration | Not implemented yet (planned) |
| PayPal Sandbox payments | Not implemented yet (planned). Checkout button is a placeholder |

## Tech stack

- **Frontend:** React 18, Vite, JavaScript, Axios, React Router, Lucide React, custom responsive CSS
- **Backend:** Python, FastAPI, SQLAlchemy, SQLite, Pydantic

## Project structure

```
CartPilotAI/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app, CORS, startup (create tables + seed)
│       ├── database.py      # SQLite engine and session
│       ├── models/          # Product table + Pydantic schemas
│       ├── routes/          # products, chat, cart endpoints
│       └── services/        # seed data, rule-based chat, cart validation
└── frontend/
    ├── .env.example
    └── src/
        ├── components/      # Navbar, ProductCard, SearchBar, ...
        ├── context/         # CartContext (shared cart state)
        ├── pages/           # Home, Catalog, Assistant, Cart
        ├── services/api.js  # All Axios calls to the backend
        └── utils/format.js  # Price formatting
```

## Prerequisites

- Python 3.9+ (`python --version`)
- Node.js 18+ (`node --version`)
- VS Code (recommended)

## Setup on Windows (PowerShell)

Open **two** PowerShell windows: one for the backend, one for the frontend.

### 1. Backend

```powershell
cd CartPilotAI\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

> If PowerShell says *"running scripts is disabled on this system"*, run this once and try again:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

The first start creates `cartpilot.db` and seeds 20 sample products automatically.
Backend: http://localhost:8000 · Swagger docs: http://localhost:8000/docs

### 2. Frontend

```powershell
cd CartPilotAI\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173

### Reset the database (optional)

```powershell
cd CartPilotAI\backend
.\venv\Scripts\Activate.ps1
python -m app.services.seed
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Health check (also tests the database) |
| GET | `/api/products` | All products. Optional: `q`, `category`, `sort` (`price_asc`, `price_desc`, `rating`) |
| GET | `/api/products/{product_id}` | One product (404 if missing) |
| GET | `/api/categories` | Distinct categories |
| POST | `/api/chat` | Demo assistant: `{ "message": "..." }` |
| POST | `/api/cart/validate` | Re-checks IDs, quantities, stock and prices |

## Testing the API with Swagger

1. Start the backend and open http://localhost:8000/docs
2. Click an endpoint, then **Try it out**, then **Execute**.

**`GET /health`**: expect `{"status":"ok","database":"connected"}`.

**`GET /api/products`**: expect 20 products. Try `category` = `Laptops`, or `sort` = `price_asc`.

**`GET /api/products/{product_id}`**: use `1` (200 OK), then `999` (404 "Product 999 not found").

**`POST /api/chat`** body:
```json
{ "message": "Find me a laptop under ₹60,000 for programming." }
```
Expect laptops priced at or below ₹60,000 (Lenovo IdeaPad first).

**`POST /api/cart/validate`**: a valid cart:
```json
{ "items": [ { "product_id": 1, "quantity": 2, "price": 58990 } ] }
```
Expect `"valid": true`. Then try these to see errors:
```json
{ "items": [ { "product_id": 1, "quantity": 1, "price": 100 } ] }
```
→ price mismatch
```json
{ "items": [ { "product_id": 11, "quantity": 1, "price": 24900 } ] }
```
→ out of stock (product 11 is AirPods Pro, stock 0)
```json
{ "items": [ { "product_id": 9999, "quantity": 1, "price": 10 } ] }
```
→ product not found

## Day 1 testing checklist

**Backend**
- [ ] `uvicorn` starts without errors and `cartpilot.db` is created
- [ ] `/health` returns `ok`
- [ ] `/api/products` returns 20 products; `q`, `category` and `sort` work
- [ ] `/api/products/999` returns 404
- [ ] `/api/categories` returns 5 categories
- [ ] `/api/chat` returns laptops under ₹60,000 for the example prompt
- [ ] `/api/cart/validate` detects price mismatch, out-of-stock and unknown product

**Frontend**
- [ ] Home page loads with hero, stats, featured and recommended products
- [ ] Home search sends you to the assistant and a reply appears
- [ ] Catalog shows 20 products; search, category tabs and price sorting work
- [ ] "Add to Cart" updates the cart badge; out-of-stock item is disabled
- [ ] Cart: +/− quantity, remove, subtotal and total update correctly
- [ ] Cart shows "Prices and stock verified by the server"
- [ ] Checkout button only shows an "isn't available yet" notice (no fake payment)
- [ ] Assistant page: example prompts work and "Demo assistant" label is visible
- [ ] Stop the backend: pages show a clear error message with a retry button
- [ ] Layout works on desktop, tablet and mobile widths (use browser dev tools)

## Roadmap

- **Day 2:** Gemini AI integration (backend only, key stored in `backend/.env`)
- **Day 3:** Product comparison and personalized recommendations
- **Day 4:** PayPal Sandbox checkout
- **Day 5:** Polish, demo preparation

## Security notes

- Never put API keys or secrets in frontend code. Anything starting with `VITE_` is public.
- `.env` files are ignored by Git. Commit only `.env.example`.
- The cart is re-validated on the server; never trust prices sent from the browser.

## License

MIT, see [LICENSE](LICENSE).