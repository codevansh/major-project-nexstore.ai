from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.agents.inventory_agent import InventoryIntelligenceAgent
from app.agents.sales_agent import SalesIntelligenceAgent
from app.core.database import get_database
from app.schemas.inventory_agent import (
    InventoryAgentRequest,
    InventoryAgentResponse,
)
from app.schemas.sales_agent import SalesAgentRequest, SalesAgentResponse


router = APIRouter(prefix="/agents", tags=["AI Agents"])


@router.post(
    "/inventory",
    response_model=InventoryAgentResponse,
)
def ask_inventory_agent(
    request: InventoryAgentRequest,
    db: Database = Depends(get_database),
):
    """Return data-grounded inventory recommendations without changing stock."""
    try:
        return InventoryIntelligenceAgent(db).run(request)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Inventory intelligence is temporarily unavailable.",
        ) from exc


@router.post(
    "/sales",
    response_model=SalesAgentResponse,
)
def ask_sales_agent(
    request: SalesAgentRequest,
    db: Database = Depends(get_database),
):
    """Return data-grounded sales metrics and product trends."""
    try:
        return SalesIntelligenceAgent(db).run(request)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Sales intelligence is temporarily unavailable.",
        ) from exc
