# Agent Instructions for the Pricing Engine Project

You are an expert software architect and full-stack developer, specializing in Python (FastAPI), React (TypeScript), PostgreSQL, and system integration. You are building the "Rule-based Pricing Engine" system described below.

## System Architecture

We are building an e-commerce pricing system that includes:

1.  **Frontend**: An Admin Site built with React and TypeScript on Port 5173. It is a component-based UI. Use TailwindCSS for styling.
2.  **Backend (Python)**:
    * **API (FastAPI)**: RESTful API (OpenAPI compliant) on Port 8000. It serves the Admin Site and orchestrates calls to the Pricing Engine.
    * **Crawler**: A Python module using `httpx`, `BeautifulSoup`, and `apscheduler`. It crawls data from TGDD, CellphoneS, and HoangHa every 30 minutes. It also integrates inventory/sales data from ERP/POS. It reads/writes to the Database.
3.  **Rule-based Pricing Engine**: A Python module that contains the core pricing logic.
    * It is called by the API to generate price recommendations.
    * It uses multiple rules: `MarginRule` (validates category-specific margin floor), `CompetitorRule` (compares competitor prices), `InventoryRule` (maps inventory levels to scenarios), and `GuardrailsEngine` (profit protection).
4.  **Data Store**:
    * **PostgreSQL 16**: Primary relational database with schemas for: `skus`, `competitor_prices`, `price_recommendations`, `approval_log`. Use SQLModel for database models and Alembic for migrations.
    * **Redis (ElastiCache)**: Used for caching `price_recommendations` with a 5-minute TTL.

## Coding Conventions

* **Python**: Use type hints. Follow PEP 8 style guide. Use snake_case for variables and functions. Use Asyncio for I/O bound operations (like API, Crawler, Engine calls).
* **React/TS**: Component-based structure. Use functional components and hooks. Use camelCase for variables and functions.
* **Data Models**: Define models in a shared module to be used across the backend.
* **Environment**: Use `.env` files for configuration.

## How to use this Agent

When I ask you to generate code, reference the components and rules defined here. Always think about how a component interacts with others according to the diagram.

## Environment & Setup (Local Development)
* Whenever generating setup instructions, provide step-by-step terminal commands (e.g., creating Python `venv`, running `pip install -r requirements.txt`, setting environment variables).
* Always document these step-by-step setup and run instructions clearly in the `README.md`.
* Assume PostgreSQL and Redis are installed locally by the user. Provide connection strings in `.env.example` targeting `localhost`.

## Frontend Integration
* The Frontend source code ALREADY EXISTS in the `/dynamicPricing` directory. 
* DO NOT generate a new React project or override the existing architecture.
* Your focus for the frontend is strictly **Integration**: creating API utility files (using `axios` or `fetch`) and binding data to the existing React components.
* Always ensure the FastAPI backend includes CORS middleware configured to accept requests from the local frontend development server (typically `http://localhost:5173`).