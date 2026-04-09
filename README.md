# StockPilot

**Intelligent Inventory Management System**

StockPilot is a modern, full-featured inventory management platform built with Python and FastAPI. It provides real-time stock tracking, automated alerts, role-based access control, and comprehensive reporting to streamline warehouse and inventory operations.

---

## Features

- **Dashboard & Analytics** — Real-time overview of stock levels, recent activity, and key metrics
- **Product Management** — Full CRUD for products with categories, SKUs, and image support
- **Inventory Tracking** — Track stock movements (inbound, outbound, adjustments) with audit trails
- **Warehouse Management** — Manage multiple warehouse locations and storage zones
- **Low Stock Alerts** — Automated notifications when inventory falls below configurable thresholds
- **Order Management** — Create and track purchase orders and sales orders
- **Supplier Management** — Maintain supplier directory with contact details and performance metrics
- **Role-Based Access Control** — Granular permissions for Super Admin, Manager, Staff, and Viewer roles
- **Search & Filtering** — Full-text search across products, orders, and suppliers
- **Reporting & Export** — Generate inventory reports with CSV/PDF export capabilities
- **Audit Logging** — Complete history of all inventory changes with user attribution
- **RESTful API** — Fully documented API endpoints with OpenAPI/Swagger UI

---

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| **Backend**    | Python 3.12, FastAPI                |
| **Database**   | SQLite (dev) / PostgreSQL (prod)    |
| **ORM**        | SQLAlchemy 2.0 (async)             |
| **Auth**       | JWT (python-jose), bcrypt           |
| **Validation** | Pydantic v2                         |
| **Templates**  | Jinja2, Tailwind CSS                |
| **Server**     | Uvicorn (ASGI)                      |
| **Deployment** | Vercel / Docker                     |

---

## Folder Structure

```
stockpilot/
├── app/
│   ├── core/
│   │   ├── config.py          # Application settings (Pydantic BaseSettings)
│   │   ├── database.py        # Async SQLAlchemy engine & session factory
│   │   ├── security.py        # JWT token creation/verification, password hashing
│   │   └── __init__.py
│   ├── models/
│   │   ├── user.py            # User model
│   │   ├── product.py         # Product model
│   │   ├── category.py        # Category model
│   │   ├── warehouse.py       # Warehouse model
│   │   ├── inventory.py       # Inventory & stock movement models
│   │   ├── order.py           # Order & order item models
│   │   ├── supplier.py        # Supplier model
│   │   ├── audit_log.py       # Audit log model
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── user.py            # User request/response schemas
│   │   ├── product.py         # Product schemas
│   │   ├── category.py        # Category schemas
│   │   ├── warehouse.py       # Warehouse schemas
│   │   ├── inventory.py       # Inventory schemas
│   │   ├── order.py           # Order schemas
│   │   ├── supplier.py        # Supplier schemas
│   │   ├── audit_log.py       # Audit log schemas
│   │   └── __init__.py
│   ├── services/
│   │   ├── user_service.py    # User business logic
│   │   ├── product_service.py # Product business logic
│   │   ├── inventory_service.py # Inventory operations
│   │   ├── order_service.py   # Order processing
│   │   └── __init__.py
│   ├── dependencies/
│   │   ├── auth.py            # Authentication dependencies (get_current_user)
│   │   └── __init__.py
│   ├── routers/
│   │   ├── auth.py            # Login, register, token refresh
│   │   ├── users.py           # User management endpoints
│   │   ├── products.py        # Product CRUD endpoints
│   │   ├── categories.py      # Category endpoints
│   │   ├── warehouses.py      # Warehouse endpoints
│   │   ├── inventory.py       # Inventory & stock movement endpoints
│   │   ├── orders.py          # Order endpoints
│   │   ├── suppliers.py       # Supplier endpoints
│   │   ├── dashboard.py       # Dashboard & reporting endpoints
│   │   └── __init__.py
│   ├── templates/
│   │   ├── base.html          # Base layout with Tailwind CSS
│   │   ├── dashboard/
│   │   ├── products/
│   │   ├── inventory/
│   │   ├── orders/
│   │   └── auth/
│   └── main.py                # FastAPI application entry point
├── .env                        # Environment variables (not committed)
├── .env.example                # Example environment variables
├── requirements.txt            # Python dependencies
├── vercel.json                 # Vercel deployment configuration
└── README.md                   # This file
```

---

## Setup Instructions

### Prerequisites

- Python 3.12+
- pip (Python package manager)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/stockpilot.git
cd stockpilot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update the values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see [Environment Variables](#environment-variables) below).

### 5. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:

- **App**: [http://localhost:8000](http://localhost:8000)
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Environment Variables

| Variable                | Description                              | Default                  | Required |
|-------------------------|------------------------------------------|--------------------------|----------|
| `APP_NAME`              | Application display name                 | `StockPilot`             | No       |
| `DEBUG`                 | Enable debug mode                        | `false`                  | No       |
| `SECRET_KEY`            | JWT signing secret (min 32 chars)        | —                        | **Yes**  |
| `DATABASE_URL`          | SQLAlchemy async database URL            | `sqlite+aiosqlite:///./stockpilot.db` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime (minutes) | `30`                    | No       |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | JWT refresh token lifetime (days)   | `7`                     | No       |
| `CORS_ORIGINS`          | Comma-separated allowed origins          | `http://localhost:3000`  | No       |
| `LOG_LEVEL`             | Logging level (DEBUG, INFO, WARNING)     | `INFO`                   | No       |
| `DEFAULT_ADMIN_EMAIL`   | Initial admin account email              | `admin@stockpilot.com`   | No       |
| `DEFAULT_ADMIN_PASSWORD`| Initial admin account password            | —                        | No       |

### Example `.env` File

```env
APP_NAME=StockPilot
DEBUG=false
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
DATABASE_URL=sqlite+aiosqlite:///./stockpilot.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
LOG_LEVEL=INFO
DEFAULT_ADMIN_EMAIL=admin@stockpilot.com
DEFAULT_ADMIN_PASSWORD=changeme123
```

---

## Deployment

### Vercel

1. Install the Vercel CLI:

   ```bash
   npm install -g vercel
   ```

2. Ensure `vercel.json` is present in the project root:

   ```json
   {
     "builds": [
       {
         "src": "app/main.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app/main.py"
       }
     ]
   }
   ```

3. Set environment variables in the Vercel dashboard under **Settings → Environment Variables**. At minimum, set:
   - `SECRET_KEY`
   - `DATABASE_URL` (use a hosted PostgreSQL provider such as Neon, Supabase, or Railway)

4. Deploy:

   ```bash
   vercel --prod
   ```

### Docker

1. Build the image:

   ```bash
   docker build -t stockpilot .
   ```

2. Run the container:

   ```bash
   docker run -d \
     --name stockpilot \
     -p 8000:8000 \
     --env-file .env \
     stockpilot
   ```

---

## Roles & Permissions

| Role           | Description                                                                 |
|----------------|-----------------------------------------------------------------------------|
| **Super Admin**| Full system access. Manage users, configure settings, view all data.        |
| **Manager**    | Manage products, inventory, orders, suppliers. View reports and dashboards. |
| **Staff**      | Create and process orders, record stock movements, view products.           |
| **Viewer**     | Read-only access to dashboards, products, and inventory levels.             |

---

## Usage Guide

### Getting Started

1. **Log in** with the default admin credentials (configured via environment variables) or register a new account.
2. **Set up categories** — Navigate to Categories and create product categories for your inventory.
3. **Add warehouses** — Define your warehouse locations under the Warehouses section.
4. **Add suppliers** — Register your suppliers with contact information.
5. **Create products** — Add products with SKU, description, category, and pricing details.
6. **Record inventory** — Use the Inventory section to record stock-in, stock-out, and adjustment movements.
7. **Manage orders** — Create purchase orders (inbound) and sales orders (outbound) to track procurement and fulfillment.
8. **Monitor dashboard** — Use the Dashboard for real-time visibility into stock levels, low-stock alerts, and recent activity.

### API Usage

All API endpoints are documented via Swagger UI at `/docs`. Authentication is required for most endpoints:

```bash
# Obtain an access token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@stockpilot.com", "password": "changeme123"}'

# Use the token in subsequent requests
curl http://localhost:8000/api/products \
  -H "Authorization: Bearer <your-access-token>"
```

---

## Development

### Running Tests

```bash
pytest --asyncio-mode=auto -v
```

### Code Formatting

```bash
# Install dev tools
pip install black isort

# Format code
black app/
isort app/
```

### Database Migrations

For production environments using PostgreSQL, use Alembic for schema migrations:

```bash
alembic init alembic
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## License

**Private** — All rights reserved. This software is proprietary and confidential. Unauthorized copying, distribution, or modification is strictly prohibited.