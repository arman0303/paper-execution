import json
import re
from typing import Optional, Dict, Any
from app.llm.base import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    """
    Intelligent offline test adapter for local execution, unit tests,
    and environments without paid API keys.
    """

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.0
    ) -> str:
        prompt_lower = prompt.lower()

        # 1. Query Understanding & Normalization
        if "normalize the following user question" in prompt_lower or "query understanding" in prompt_lower:
            # Extract the actual user query from the prompt
            q_match = re.search(r'user query:\s*"([^"]+)"', prompt, re.IGNORECASE)
            target_q = q_match.group(1).lower() if q_match else prompt_lower

            # Check for ambiguous or unsupported queries
            if "top subscribers" in target_q:
                return json.dumps({
                    "original_question": target_q,
                    "normalized_question": "Retrieve top ranking users by subscription metrics",
                    "main_clause": "retrieve top users",
                    "details": "",
                    "requested_entities": [{"label": "subscribers", "entity_type": "category"}],
                    "relevant_metrics": [],
                    "relevant_dimensions": [],
                    "candidate_tables": [],
                    "candidate_columns": [],
                    "operations": [],
                    "is_ambiguous": True,
                    "is_unsupported": False,
                    "clarification_message": "The term 'top subscribers' is ambiguous. Did you mean highest spending customers or most recent active customers?"
                })
            elif "predict the sales forecast" in target_q or "linear regression" in target_q:
                return json.dumps({
                    "original_question": target_q,
                    "normalized_question": "Predict future sales using machine learning",
                    "main_clause": "predict sales",
                    "details": "",
                    "requested_entities": [],
                    "relevant_metrics": [],
                    "relevant_dimensions": [],
                    "candidate_tables": [],
                    "candidate_columns": [],
                    "operations": [],
                    "is_ambiguous": False,
                    "is_unsupported": True,
                    "clarification_message": "Machine learning predictions and statistical forecasting are beyond SQL query capabilities."
                })
            elif "loyalty tier points" in target_q or "bonus tokens" in target_q:
                return json.dumps({
                    "original_question": target_q,
                    "normalized_question": "Query loyalty tier points and bonus tokens",
                    "main_clause": "query loyalty points",
                    "details": "",
                    "requested_entities": [{"label": "loyalty points", "entity_type": "metric"}],
                    "relevant_metrics": [],
                    "relevant_dimensions": [],
                    "candidate_tables": [],
                    "candidate_columns": [],
                    "operations": [],
                    "is_ambiguous": True,
                    "is_unsupported": True,
                    "clarification_message": "The database does not contain loyalty points or bonus token tables."
                })

            # Normal question understanding
            main_clause = "retrieve data"
            if "active customers" in prompt_lower:
                main_clause = "list active customers"
            elif "revenue" in prompt_lower or "sales" in prompt_lower:
                main_clause = "calculate total revenue"
            elif "products" in prompt_lower:
                main_clause = "list products"
            elif "orders" in prompt_lower:
                main_clause = "list orders"
            elif "payments" in prompt_lower:
                main_clause = "retrieve payments"

            return json.dumps({
                "original_question": prompt,
                "normalized_question": f"Normalized: {main_clause}",
                "main_clause": main_clause,
                "details": "standard query parameters",
                "requested_entities": [
                    {"label": "primary_entity", "entity_type": "category", "attributes": "standard"}
                ],
                "relevant_metrics": ["total_amount", "price", "quantity"],
                "relevant_dimensions": ["country", "category", "status"],
                "candidate_tables": ["customers", "orders", "products"],
                "candidate_columns": ["id", "name", "total_amount"],
                "operations": [{"operation": "SELECT", "target": "*", "condition": None}],
                "is_ambiguous": False,
                "is_unsupported": False,
                "clarification_message": None
            })

        # 2. Table Refinement via Business Rules (TB = LLM(N, R))
        if "refine table selection based on business rules" in prompt_lower or "tb = llm(n, r)" in prompt_lower:
            tables = []
            if "revenue" in prompt_lower or "sales" in prompt_lower or "spent" in prompt_lower or "order" in prompt_lower:
                tables.append("orders")
            if "customer" in prompt_lower or "buyer" in prompt_lower:
                tables.append("customers")
            if "product" in prompt_lower or "item" in prompt_lower or "inventory" in prompt_lower:
                tables.append("products")
            if "payment" in prompt_lower or "credit card" in prompt_lower or "paypal" in prompt_lower:
                tables.append("payments")
            if not tables:
                tables = ["orders"]
            return json.dumps({"tables": tables, "reasoning": "Derived from business rules and entities."})

        # 3. Final Table Refinement (TR = LLM(N, Instr_Domain, R, Candidates))
        if "final table refinement" in prompt_lower or "table refining prompt" in prompt_lower:
            selected_tables = ["orders"]
            justifications = {"orders": "Primary order transaction record"}
            if "customer" in prompt_lower or "buyer" in prompt_lower or "user" in prompt_lower:
                selected_tables.append("customers")
                justifications["customers"] = "Contains customer names and geographic fields"
            if "product" in prompt_lower or "item" in prompt_lower:
                selected_tables.append("products")
                justifications["products"] = "Contains product descriptions and prices"
                if "order" in prompt_lower:
                    selected_tables.append("order_items")
                    justifications["order_items"] = "Junction bridge table linking orders to products"
            if "payment" in prompt_lower:
                selected_tables.append("payments")
                justifications["payments"] = "Contains payment method and status settlement records"

            return json.dumps({
                "refined_tables": list(set(selected_tables)),
                "justifications": justifications,
                "join_plan": "Joined along foreign key constraints"
            })

        # 4. Entity Extraction & Voting
        if "extract entities from the following table documentation" in prompt_lower:
            return json.dumps({
                "entities": ["order", "customer", "product", "price", "status", "country", "amount"]
            })

        # 5. Question Paraphrasing / Variations
        if "generate 3 question variations" in prompt_lower:
            return json.dumps([
                "How can I view the relevant data records?",
                "Provide a summary report matching the criteria.",
                "Extract the matching records from the database."
            ])

        # 6. SQL Generation & Baseline Generation
        if any(term in prompt_lower for term in [
            "expert sql generator",
            "synthesize an accurate",
            "generate an accurate sql query",
            "sql code generation",
            "generating standard sqlite sql queries",
            "generating standard sqlite queries",
            "generating standard sql queries"
        ]):
            # Deterministic generation for common patterns
            is_baseline = "generating standard" in prompt_lower and "expert sql generator" not in prompt_lower
            sql = "SELECT * FROM orders LIMIT 10;"
            explanation = "Default query"
            tables = ["orders"]

            if "active customers" in prompt_lower and "uk" in prompt_lower:
                sql = "SELECT id, name, email, city FROM customers WHERE country = 'UK' AND status = 'active';"
                explanation = "Select active customers located in the UK."
                tables = ["customers"]
            elif "active customers" in prompt_lower and "usa" in prompt_lower:
                sql = "SELECT id, name, email, city FROM customers WHERE country = 'USA' AND status = 'active';"
                explanation = "Select active customers located in the USA."
                tables = ["customers"]
            elif "total number of products in stock" in prompt_lower:
                sql = "SELECT SUM(stock_quantity) AS total_inventory FROM products WHERE is_active = 1;"
                explanation = "Sum of stock quantities across active products."
                tables = ["products"]
            elif "total spending for each customer" in prompt_lower or "spending" in prompt_lower:
                sql = "SELECT c.id, c.name, SUM(o.total_amount) AS total_spent FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'completed' GROUP BY c.id, c.name ORDER BY total_spent DESC;"
                explanation = "Calculate total customer expenditure on completed orders."
                tables = ["customers", "orders"]
            elif "greater than 200" in prompt_lower or "> 200" in prompt_lower:
                sql = "SELECT id, customer_id, order_date, total_amount FROM orders WHERE status = 'completed' AND total_amount > 200 ORDER BY total_amount DESC;"
                explanation = "Find completed orders exceeding 200 dollars."
                tables = ["orders"]
            elif "best-selling products" in prompt_lower or "top 2" in prompt_lower:
                sql = "SELECT p.id, p.name, SUM(oi.quantity) AS total_sold FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id, p.name ORDER BY total_sold DESC LIMIT 2;"
                explanation = "Top 2 products by quantity sold across orders."
                tables = ["products", "order_items"]
            elif "average transaction value" in prompt_lower and "london" in prompt_lower:
                sql = "SELECT ROUND(AVG(total_amount), 2) AS avg_order_value FROM orders WHERE status = 'completed' AND shipping_city = 'London';"
                explanation = "Average completed order amount in London."
                tables = ["orders"]
            elif "paypal" in prompt_lower:
                sql = "SELECT id, order_id, amount, status, payment_date FROM payments WHERE payment_method = 'paypal';"
                explanation = "List payments executed with PayPal."
                tables = ["payments"]
            elif "total revenue" in prompt_lower:
                sql = "SELECT SUM(total_amount) AS total_revenue FROM orders WHERE status = 'completed';"
                explanation = "Gross completed order sales."
                tables = ["orders"]

            return json.dumps({
                "sql": sql,
                "explanation": explanation,
                "referenced_tables": tables,
                "referenced_columns": ["id"],
                "filters_applied": ["status = 'completed'"],
                "aggregations_applied": ["SUM", "AVG"],
                "warnings": []
            })

        # Generic default JSON or text
        if json_mode:
            return json.dumps({"status": "ok", "message": "Mock completion"})
        return "Mock response"
