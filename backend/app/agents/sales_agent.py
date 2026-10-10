import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pymongo.database import Database

from app.schemas.sales_agent import (
    SalesAgentRequest,
    SalesAgentResponse,
)
from app.services.sales_intelligence_service import SalesIntelligenceTools


class SalesAgentState(TypedDict, total=False):
    request: dict[str, Any]
    intent: str
    periods: dict[str, Any]
    retrieved: dict[str, Any]
    metrics: dict[str, Any]
    products: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    forecasts: list[dict[str, Any]]
    summary: str
    data_period: str
    warnings: list[str]
    response: dict[str, Any]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _number_text(value: int | float) -> str:
    """Render integral quantities without a misleading trailing decimal."""
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _intent_for(request: dict[str, Any]) -> str:
    if request.get("analysis"):
        return request["analysis"]
    question = request["question"].lower()

    forecast_words = ("forecast", "likely to sell", "future demand", "next week")
    if any(word in question for word in forecast_words) and any(
        word in question for word in ("sell", "sales", "demand", "product")
    ):
        return "forecast"
    if any(
        word in question
        for word in ("declin", "trend", "decrease", "compared", "versus", " vs ")
    ):
        return "comparison"
    if any(word in question for word in ("best-selling", "best selling", "top-selling", "top selling", "top products")):
        return "top_products"
    if any(word in question for word in ("low-performing", "low performing", "underperform", "least selling", "slow-selling", "slow selling")):
        return "low_products"
    if request.get("product_id"):
        return "product_sales"
    return "summary"


class SalesIntelligenceAgent:
    """LangGraph workflow for explainable sales analysis over completed orders."""

    name = "Sales Intelligence Agent"

    def __init__(
        self,
        db: Database,
        *,
        tools: SalesIntelligenceTools | None = None,
        llm: Any | None = None,
        now: datetime | None = None,
    ):
        self.tools = tools or SalesIntelligenceTools(db, now=now)
        self.db = db
        self.llm = llm
        self.now = _utc(now or datetime.now(timezone.utc))
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(SalesAgentState)
        workflow.add_node("identify", self._identify)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("calculate", self._calculate)
        workflow.add_node("explain", self._explain)
        workflow.add_node("validate", self._validate)
        workflow.set_entry_point("identify")
        workflow.add_edge("identify", "retrieve")
        workflow.add_edge("retrieve", "calculate")
        workflow.add_edge("calculate", "explain")
        workflow.add_edge("explain", "validate")
        workflow.add_edge("validate", END)
        return workflow.compile()

    def _identify(self, state: SalesAgentState) -> dict[str, Any]:
        request = state["request"]
        intent = _intent_for(request)
        question = request["question"].lower()
        start = request.get("start_date")
        end = request.get("end_date")

        if start is not None and end is not None:
            current_start, current_end = _utc(start), _utc(end)
        elif intent == "summary" and any(
            phrase in question for phrase in ("this month", "month to date")
        ):
            current_end = self.now
            current_start = self.now.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            match = re.search(r"(?:last|past)\s+(\d{1,3})\s+days?", question)
            period_days = int(match.group(1)) if match else 7
            current_end = self.now
            current_start = current_end - timedelta(days=period_days)

        previous_end = current_start - timedelta(microseconds=1)
        previous_start = previous_end - (current_end - current_start)
        label = self._period_label(question, current_start, current_end)
        periods = {
            "current_start": current_start,
            "current_end": current_end,
            "previous_start": previous_start,
            "previous_end": previous_end,
            "label": label,
            "comparison_label": (
                f"{label} versus preceding period "
                f"({previous_start.date().isoformat()} to {previous_end.date().isoformat()})"
            ),
        }
        return {"intent": intent, "periods": periods, "warnings": []}

    @staticmethod
    def _period_label(question: str, start: datetime, end: datetime) -> str:
        if "this month" in question or "month to date" in question:
            return f"Month to date ({start.date().isoformat()} to {end.date().isoformat()})"
        if start.hour == end.hour and start.minute == end.minute:
            days = max(1, round((end - start).total_seconds() / 86400))
            return f"Last {days} days ({start.date().isoformat()} to {end.date().isoformat()})"
        return f"{start.date().isoformat()} to {end.date().isoformat()}"

    def _retrieve(self, state: SalesAgentState) -> dict[str, Any]:
        request = state["request"]
        periods = state["periods"]
        intent = state["intent"]
        current_start = periods["current_start"]
        current_end = periods["current_end"]
        previous_start = periods["previous_start"]
        previous_end = periods["previous_end"]
        store_id = request.get("store_id")

        retrieved: dict[str, Any] = {
            "current_summary": self.tools.get_sales_summary(
                current_start, current_end, store_id
            ),
        }
        if intent == "comparison":
            retrieved["comparison"] = self.tools.compare_sales_periods(
                current_start,
                current_end,
                previous_start,
                previous_end,
                store_id,
            )
            retrieved["product_comparisons"] = self.tools.compare_product_sales_periods(
                current_start,
                current_end,
                previous_start,
                previous_end,
                store_id,
            )
        elif intent == "top_products":
            retrieved["top_products"] = self.tools.get_top_selling_products(
                request["limit"], current_start, current_end, store_id
            )
        elif intent == "low_products":
            retrieved["low_products"] = self.tools.get_low_performing_products(
                request["limit"], current_start, current_end, store_id
            )
        elif intent == "product_sales":
            retrieved["product_sales"] = self.tools.get_product_sales(
                request["product_id"], current_start, current_end, store_id
            )
        elif intent == "forecast":
            if request.get("product_id"):
                product_ids = [request["product_id"]]
            else:
                lookback_start = self.now - timedelta(days=90)
                lookback_products = self.tools.get_top_selling_products(
                    request["limit"], lookback_start, self.now, store_id
                )
                product_ids = [row["product_id"] for row in lookback_products]
            forecasts = []
            for product_id in product_ids:
                forecast = self.tools.get_demand_forecast(
                    product_id,
                    request["horizon_days"],
                    store_id,
                )
                product = self.tools.forecast_tools.get_product_details(product_id)
                forecast_reason = (
                    f"Historical sales recorded {forecast['history_units']} units over "
                    f"{forecast['history_days']} distinct sales days in the 90-day window."
                    if forecast["method"] == "historical_average"
                    else (
                        f"Only {forecast['history_days']} distinct sales days are "
                        "available; at least 3 are required for the historical baseline."
                    )
                )
                forecasts.append(
                    {
                        **forecast,
                        "product_name": (
                            (product or {}).get("name")
                            or next(
                                (
                                    row["product_name"]
                                    for row in retrieved.get("top_products", [])
                                    if row["product_id"] == product_id
                                ),
                                product_id,
                            )
                        ),
                        "reason": forecast_reason,
                    }
                )
                if forecast["method"] == "unavailable":
                    state.setdefault("warnings", []).append(
                        f"Demand forecast is unavailable for {product_id} because sales history is insufficient."
                    )
            retrieved["forecasts"] = forecasts

        return {"retrieved": retrieved, "warnings": state.get("warnings", [])}

    def _calculate(self, state: SalesAgentState) -> dict[str, Any]:
        retrieved = state["retrieved"]
        intent = state["intent"]
        current = retrieved["current_summary"]
        comparison = retrieved.get("comparison")
        if comparison:
            current = comparison["current_period"]
            previous = comparison["previous_period"]
            metrics = {
                "current_period_revenue": current["revenue"],
                "current_period_units_sold": current["units_sold"],
                "current_period_order_count": current["order_count"],
                "current_period_average_order_value": current["average_order_value"],
                "previous_period_revenue": previous["revenue"],
                "previous_period_units_sold": previous["units_sold"],
                "previous_period_order_count": previous["order_count"],
                "previous_period_average_order_value": previous["average_order_value"],
                "revenue_change": comparison["revenue_change"],
                "revenue_change_percent": comparison["revenue_change_percent"],
                "units_change": comparison["units_change"],
                "units_change_percent": comparison["units_change_percent"],
            }
        else:
            metrics = {
                "current_period_revenue": current["revenue"],
                "current_period_units_sold": current["units_sold"],
                "current_period_order_count": current["order_count"],
                "current_period_average_order_value": current["average_order_value"],
            }

        insights = []
        if intent == "comparison":
            for row in retrieved.get("product_comparisons", []):
                if row["trend"] == "STABLE":
                    continue
                difference = row["current_units_sold"] - row["previous_units_sold"]
                direction = "increased" if difference > 0 else "decreased"
                reason = (
                    f"Units sold {direction} from {_number_text(row['previous_units_sold'])} to "
                    f"{_number_text(row['current_units_sold'])} "
                    f"({_number_text(abs(difference))} units {direction}); revenue changed from "
                    f"{row['previous_revenue']:.2f} to {row['current_revenue']:.2f}."
                )
                insights.append({**row, "reason": reason})

        if current["order_count"] == 0:
            state.setdefault("warnings", []).append(
                "No completed sales were found in the current reporting period."
            )
        if comparison and comparison["previous_period"]["order_count"] == 0:
            state.setdefault("warnings", []).append(
                "No completed sales were found in the comparison period; percentage changes may be unavailable."
            )

        products: list[dict] = []
        if intent == "top_products":
            products = retrieved.get("top_products", [])
        elif intent == "low_products":
            products = retrieved.get("low_products", [])

        return {
            "metrics": metrics,
            "products": products,
            "insights": insights,
            "forecasts": retrieved.get("forecasts", []),
            "warnings": state.get("warnings", []),
        }

    def _explain(self, state: SalesAgentState) -> dict[str, Any]:
        intent = state["intent"]
        metrics = state["metrics"]
        periods = state["periods"]
        products = state.get("products", [])
        insights = state.get("insights", [])
        forecasts = state.get("forecasts", [])

        if intent == "comparison":
            current_revenue = metrics["current_period_revenue"]
            previous_revenue = metrics["previous_period_revenue"] or 0
            change = metrics["revenue_change"] or 0
            percent = metrics["revenue_change_percent"]
            if percent is None:
                summary = (
                    f"Current revenue was {current_revenue:.2f}; previous-period revenue "
                    f"was {previous_revenue:.2f}. Percentage change is unavailable "
                    "because the previous-period revenue baseline was zero."
                )
            elif change < 0:
                summary = (
                    f"Revenue declined by {abs(change):.2f} ({abs(percent):.2f}%) "
                    f"from {previous_revenue:.2f} to {current_revenue:.2f}."
                )
            elif change > 0:
                summary = (
                    f"Revenue increased by {change:.2f} ({percent:.2f}%) "
                    f"from {previous_revenue:.2f} to {current_revenue:.2f}."
                )
            else:
                summary = f"Revenue was unchanged at {current_revenue:.2f}."
            if insights:
                declines = [row for row in insights if row["trend"] == "DECLINING"]
                if declines:
                    evidence = "; ".join(
                        f"{row['product_name']} {row['previous_units_sold']} to "
                        f"{row['current_units_sold']} units"
                        for row in declines[:3]
                    )
                    summary += (
                        f" Measured product declines: {evidence}. These changes are "
                        "evidence, not proof of why total revenue changed."
                    )
            if change < 0 and not any(
                row["trend"] == "DECLINING" for row in insights
            ):
                summary += " Product-level data does not identify a specific driver."
            data_period = periods["comparison_label"]
        elif intent == "top_products":
            if products:
                listing = "; ".join(
                    f"{row['product_name']} ({row['units_sold']} units)"
                    for row in products[:5]
                )
                summary = f"Top-selling products for this period: {listing}."
            else:
                summary = "No product sales were recorded in this period."
            data_period = periods["label"]
        elif intent == "low_products":
            if products:
                listing = "; ".join(
                    f"{row['product_name']} ({row['units_sold']} units)"
                    for row in products[:5]
                )
                summary = f"Lowest unit sales in this period: {listing}."
            else:
                summary = "No completed sales were available to rank products."
            data_period = periods["label"]
        elif intent == "product_sales":
            row = state["retrieved"]["product_sales"]
            summary = (
                f"{row['product_name']} recorded {row['units_sold']} units across "
                f"{row['order_count']} completed orders, with revenue of {row['revenue']:.2f}."
            )
            data_period = periods["label"]
        elif intent == "forecast":
            available = [row for row in forecasts if row["predicted_units"] is not None]
            if available:
                summary = "Historical-sales demand estimates are available for " + ", ".join(
                    f"{row['product_name']} ({row['predicted_units']} units over "
                    f"{row['horizon_days']} days)"
                    for row in available[:5]
                ) + ". These are historical-average baselines, not ML model outputs."
            else:
                summary = (
                    "A demand prediction is unavailable because this project has no "
                    "configured ML model and recorded sales history is insufficient "
                    "for the historical-average baseline."
                )
            data_period = f"Next {state['request']['horizon_days']} days; forecast based on 90-day sales history"
        else:
            summary = (
                f"Revenue was {metrics['current_period_revenue']:.2f} across "
                f"{metrics['current_period_order_count']} completed orders, with "
                f"{metrics['current_period_units_sold']} units sold. Average order "
                f"value was {metrics['current_period_average_order_value']:.2f}."
            )
            data_period = periods["label"]

        if self.llm is not None:
            try:
                prompt = {
                    "question": state["request"]["question"],
                    "summary": summary,
                    "instruction": "Add a short plain-language lead-in only. Do not add facts or numbers.",
                }
                result = self.llm.invoke(json.dumps(prompt, ensure_ascii=False))
                lead_in = getattr(result, "content", None)
                if isinstance(lead_in, str) and lead_in.strip() and not any(
                    character.isdigit() for character in lead_in
                ):
                    summary = f"{lead_in.strip()} {summary}"
            except Exception:
                # LLM-generated prose is optional; stored data remains authoritative.
                pass

        return {"summary": summary, "data_period": data_period}

    def _validate(self, state: SalesAgentState) -> dict[str, Any]:
        response = SalesAgentResponse.model_validate(
            {
                "agent": self.name,
                "summary": state["summary"],
                "metrics": state["metrics"],
                "product_sales": state["retrieved"].get("product_sales"),
                "top_selling_products": state.get("products", [])
                if state["intent"] == "top_products"
                else [],
                "low_performing_products": state.get("products", [])
                if state["intent"] == "low_products"
                else [],
                "insights": state.get("insights", []),
                "forecasts": state.get("forecasts", []),
                "data_period": state["data_period"],
                "warnings": state.get("warnings", []),
            }
        )
        return {"response": response.model_dump(mode="json")}

    def run(self, request: SalesAgentRequest) -> dict[str, Any]:
        state = self.graph.invoke(
            {
                "request": request.model_dump(),
                "warnings": [],
            }
        )
        return state["response"]
