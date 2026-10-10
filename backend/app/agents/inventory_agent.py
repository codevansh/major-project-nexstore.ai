import json
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pymongo.database import Database

from app.schemas.inventory_agent import (
    InventoryAgentRequest,
    InventoryAgentResponse,
)
from app.services.inventory_intelligence_service import (
    OVERSTOCK_COVERAGE_DAYS,
    InventoryIntelligenceTools,
)


class InventoryAgentState(TypedDict, total=False):
    request: dict[str, Any]
    evidence: list[dict[str, Any]]
    evaluated: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    warnings: list[str]
    answer: str


def _as_nonnegative_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if result >= 0 else None


def _risk_level(status: str, coverage: float | None, horizon: int) -> str:
    if status == "STOCKOUT" or (coverage is not None and coverage <= horizon):
        return "HIGH"
    if status == "LOW_STOCK" or (
        coverage is not None and coverage <= horizon * 2
    ):
        return "MEDIUM"
    return "LOW"


class InventoryIntelligenceAgent:
    """LangGraph inventory workflow; stock facts are calculated from MongoDB data."""

    name = "Inventory Intelligence Agent"

    def __init__(
        self,
        db: Database,
        *,
        tools: InventoryIntelligenceTools | None = None,
        llm: Any | None = None,
    ):
        self.tools = tools or InventoryIntelligenceTools(db)
        # The repository currently has no LLM provider configuration. This hook
        # supports an injected summarizer while keeping its prose out of all
        # inventory facts and calculations.
        self.llm = llm
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(InventoryAgentState)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("evaluate", self._evaluate)
        workflow.add_node("recommend", self._recommend)
        workflow.add_node("validate", self._validate)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "evaluate")
        workflow.add_edge("evaluate", "recommend")
        workflow.add_edge("recommend", "validate")
        workflow.add_edge("validate", END)
        return workflow.compile()

    def _retrieve(self, state: InventoryAgentState) -> dict[str, Any]:
        request = state["request"]
        store_id = request.get("store_id")
        product_filter = request.get("product_id")
        horizon = request["horizon_days"]
        evidence: list[dict[str, Any]] = []
        warnings = list(state.get("warnings", []))

        inventory_records = self.tools.get_inventory(store_id)
        if not inventory_records:
            location = f" for store {store_id}" if store_id else ""
            warnings.append(f"No inventory records were found{location}.")

        for inventory in inventory_records:
            product_id = str(inventory.get("product_id", ""))
            if product_filter and product_filter != product_id:
                continue
            product = self.tools.get_product_details(product_id)
            if product is None:
                warnings.append(
                    f"Skipped inventory for product {product_id}: product details were not found."
                )
                continue

            scoped_store = str(inventory.get("store_id", ""))
            sales_history = self.tools.get_sales_history(
                product_id,
                store_id=scoped_store,
            )
            forecast = self.tools.get_demand_forecast(
                product_id,
                horizon,
                store_id=scoped_store,
                history=sales_history,
            )
            if forecast["method"] == "unavailable":
                warnings.append(
                    f"Forecast unavailable for {product.get('name') or product_id}: "
                    "fewer than 3 distinct sales days were recorded in the 90-day history window."
                )
            coverage = self.tools.calculate_stock_coverage(
                product_id,
                store_id=scoped_store,
                forecast=forecast,
            )
            reorder_quantity = self.tools.calculate_reorder_quantity(
                product_id,
                horizon,
                store_id=scoped_store,
                forecast=forecast,
                inventory_record=inventory,
                product_details=product,
            )
            evidence.append(
                {
                    "inventory": inventory,
                    "product": product,
                    "forecast": forecast,
                    "coverage": coverage,
                    "reorder_quantity": reorder_quantity,
                }
            )

        if product_filter and not evidence:
            warnings.append(
                f"No inventory record was found for product {product_filter} in the requested store."
            )
        return {"evidence": evidence, "warnings": warnings}

    def _evaluate(self, state: InventoryAgentState) -> dict[str, Any]:
        horizon = state["request"]["horizon_days"]
        evaluated: list[dict[str, Any]] = []
        warnings = list(state.get("warnings", []))

        for row in state.get("evidence", []):
            inventory = row["inventory"]
            product = row["product"]
            stock = inventory.get("stock", {})
            available = _as_nonnegative_int(stock.get("available"))
            if available is None:
                warnings.append(
                    f"Skipped product {inventory.get('product_id')}: available stock is missing or invalid."
                )
                continue

            thresholds = inventory.get("thresholds", {})
            reorder_level = _as_nonnegative_int(thresholds.get("reorder_level"))
            coverage = row["coverage"].get("coverage_days")

            if available == 0:
                status = "STOCKOUT"
            elif reorder_level is not None and available <= reorder_level:
                status = "LOW_STOCK"
            elif coverage is not None and coverage <= horizon * 2:
                status = "AT_RISK"
            elif coverage is not None and coverage > OVERSTOCK_COVERAGE_DAYS:
                status = "OVERSTOCK"
            else:
                status = "HEALTHY"

            evaluated.append(
                {
                    **row,
                    "current_stock": available,
                    "reorder_level": reorder_level,
                    "status": status,
                    "risk_level": _risk_level(status, coverage, horizon),
                    "product_id": str(inventory.get("product_id", "")),
                    "product_name": str(product.get("name") or "Unknown product"),
                    "store_id": str(inventory.get("store_id", "")),
                }
            )

        return {"evaluated": evaluated, "warnings": warnings}

    def _recommend(self, state: InventoryAgentState) -> dict[str, Any]:
        horizon = state["request"]["horizon_days"]
        recommendations: list[dict[str, Any]] = []

        for row in state.get("evaluated", []):
            status = row["status"]
            if status == "HEALTHY":
                continue

            forecast = row["forecast"]
            coverage = row["coverage"].get("coverage_days")
            reorder_level = row["reorder_level"]
            current_stock = row["current_stock"]
            predicted_demand = forecast.get("predicted_units")
            recommended_quantity = row["reorder_quantity"]

            if status == "STOCKOUT":
                reason = f"Available stock is 0 in store {row['store_id']}."
            elif status == "LOW_STOCK":
                reason = (
                    f"Available stock is {current_stock}, at or below the configured "
                    f"reorder level of {reorder_level}."
                )
            elif status == "AT_RISK":
                reason = (
                    f"Estimated stock coverage is {coverage} days, within twice the "
                    f"requested {horizon}-day planning horizon."
                )
            else:
                reason = (
                    f"Available stock is {current_stock}; estimated stock coverage is "
                    f"{coverage} days, above the "
                    f"{OVERSTOCK_COVERAGE_DAYS}-day overstock review threshold."
                )

            if forecast["method"] == "unavailable":
                reason += (
                    " Forecast unavailable: fewer than 3 distinct sales days were "
                    "recorded in the 90-day history window."
                )
            elif predicted_demand is not None:
                reason += (
                    f" Completed sales history estimates {predicted_demand} units of "
                    f"demand over the next {horizon} days."
                )

            if status == "OVERSTOCK":
                recommended_quantity = 0
                reason += " Recommended reorder quantity is 0 while excess stock is reviewed."
            elif recommended_quantity is None:
                reason += " A reorder quantity could not be calculated from available data."
            elif forecast["method"] == "unavailable":
                reason += (
                    f" Suggested reorder quantity {recommended_quantity} uses the "
                    "quantity configured on this inventory record."
                )
            else:
                reason += (
                    f" Suggested reorder quantity is {recommended_quantity}, "
                    "calculated against the available stock and forecast demand."
                )

            recommendations.append(
                {
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "store_id": row["store_id"],
                    "current_stock": current_stock,
                    "average_daily_demand": forecast.get("average_daily_demand"),
                    "predicted_demand": predicted_demand,
                    "horizon_days": horizon,
                    "stock_coverage_days": coverage,
                    "inventory_status": status,
                    "risk_level": row["risk_level"],
                    "recommended_reorder_quantity": recommended_quantity,
                    "forecast_method": forecast["method"],
                    "reason": reason,
                    "requires_human_approval": True,
                }
            )

        return {"recommendations": recommendations}

    def _validate(self, state: InventoryAgentState) -> dict[str, Any]:
        recommendations = state.get("recommendations", [])
        if not recommendations:
            answer = "No products currently meet the inventory risk or overstock rules."
        else:
            count = len(recommendations)
            names = ", ".join(item["product_name"] for item in recommendations[:5])
            suffix = "" if count <= 5 else f", and {count - 5} more"
            answer = f"Found {count} product(s) needing inventory attention: {names}{suffix}."

        if self.llm is not None:
            try:
                # Optional prose only. Deterministic recommendation values and
                # reasons remain the response's source of truth.
                prompt = {
                    "question": state["request"]["question"],
                    "recommendations": recommendations,
                    "instruction": (
                        "Give a brief conversational lead-in. Do not add facts, "
                        "quantities, forecasts, or recommendations."
                    ),
                }
                result = self.llm.invoke(
                    json.dumps(prompt, ensure_ascii=False)
                )
                content = getattr(result, "content", None)
                if isinstance(content, str) and content.strip() and not any(
                    character.isdigit() for character in content
                ):
                    answer = f"{content.strip()} {answer}"
            except Exception:
                # Chat is optional: a model outage never blocks verified data.
                pass

        return {"answer": answer}

    def run(self, request: InventoryAgentRequest) -> dict[str, Any]:
        state = self.graph.invoke(
            {
                "request": request.model_dump(),
                "evidence": [],
                "evaluated": [],
                "recommendations": [],
                "warnings": [],
                "answer": "",
            }
        )
        response = InventoryAgentResponse.model_validate(
            {
                "agent": self.name,
                "question": request.question,
                "answer": state["answer"],
                "recommendations": state["recommendations"],
                "warnings": state.get("warnings", []),
                "human_approval_required": True,
            }
        )
        return response.model_dump(mode="json")
