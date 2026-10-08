from fastapi import APIRouter
from app.api.routes import orders, branches, pricing

from app.api.routes import analytics, audit, auth, categories, customers, employees, insights, inventory, probability, products, reports, sales, statistics, users

api_router = APIRouter()
api_router.include_router(pricing.router)
api_router.include_router(orders.router)
api_router.include_router(branches.router)
for route_module in (auth, users, customers, employees, categories, products, sales, inventory, statistics, probability, analytics, insights, reports, audit):
    api_router.include_router(route_module.router)

