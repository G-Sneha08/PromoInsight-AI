# PromoInsight AI

**OneTapp Consulting AI/ML Engineer Assessment Submission**  
PromoInsight AI is a conversational analytics assistant designed for FMCG beverages company business users. It converts natural-language business questions about sales, promotions, categories, regions, trends, and inventory into structured, validated query plans, translates them into parameterised, read-only SQL, and validates the data results to generate grounded business responses.

---

## Architecture Overview

PromoInsight AI implements a multi-layered, schema-aware pipeline:

```
User Question
  │
  ▼
Schema & Metric Context Retrieval ──────► [Metadata/Metric Catalog]
  │
  ▼
Intent Parsing (LLM or Rule-Based) ──────► [Pydantic Structured Plan]
  │
  ▼
Schema-Aware Validation (Limits, Feasibility)
  │
  ▼
Deterministic SQL Compilation ────────► [Parameterized SQL & Parameters]
  │
  ▼
Read-Only SQL Connection Execution ───► [Pandas DataFrames]
  │
  ▼
Specialized Calculations Intercept (Uplift, Anomalies, Quality)
  │
  ▼
Result & Language Validation (NaN/Inf, Causal claim checks)
  │
  ▼
Grounded Response & Dynamic Chart ────► [Streamlit UI Card, Table, Plotly]
```

1. **User Question & Context**: The natural language question is processed along with context from prior conversation turns (enabling multi-turn follow-ups).
2. **Catalog & Context Retrieval**: Dynamic row counts, column values, and date ranges are pulled from SQLite to ground the parser.
3. **Intent Parsing**: Generates a Pydantic `QueryPlan` object containing reusable analytical operations. Uses an LLM (Gemini or OpenAI) if configured, or a rule-based regex lookup.
4. **Schema-Aware Validation**: Inspects the plan to verify column references, operator types, table joins, and parameter limits.
5. **Deterministic SQL Compiler**: Translates operations into parameterised SQL (`?` placeholders) and returns separate parameters.
6. **Read-Only SQLite Execution**: Connects to `database/promoinsight.db` in read-only mode (`mode=ro`).
7. **Specialized Calculation Layers**: Processes metrics like baseline sales, rolling Z-score anomalies, and completeness scores.
8. **Result & Language Validation**: Replaces NaN/Inf values, computes coverage completeness, and sanitizes causal words (like "caused by") to associative language (like "associated with").
9. **Grounded Response & Charting**: Outputs structured direct answers, metric cards, Plotly charts, warnings, and recommended actions.

---

## Database Design

The system runs on SQLite. The database schema at `database/promoinsight.db` includes:

- **products**: `product_id` (PK), `product_name`, `category`, `brand`, `pack_size`, `unit_price`
- **regions**: `region_id` (PK), `region_name`, `state_group`
- **promotions**: `promotion_id` (PK), `promotion_name`, `promotion_type`, `discount_percentage`, `start_date`, `end_date`, `product_id` (FK), `region_id` (FK)
- **sales**: `sale_id` (PK), `sale_date`, `product_id` (FK), `region_id` (FK), `units_sold`, `sales_amount`, `promotion_id` (FK, Nullable)
- **inventory**: `inventory_id` (PK), `snapshot_date`, `product_id` (FK), `region_id` (FK), `opening_inventory`, `received_units`, `closing_inventory`

Indexes are defined on date and product/region key combinations to speed up aggregate joins.

---

## Official Metric Catalog

PromoInsight AI implements calculations based on strict business formulas:

1. **Total Sales**: `SUM(sales_amount)`
2. **Total Units**: `SUM(units_sold)`
3. **Average Selling Price (ASP)**: `SUM(sales_amount) / SUM(units_sold)`
4. **Average Daily Sales**: `AVG(units_sold)` grouped daily.
5. **Sales Growth %**: `((Current - Prior) / Prior) * 100` (computed by shifting time intervals).
6. **Month-over-Month Growth**: Growth rate compared to the previous calendar month.
7. **Revenue Contribution %**: `(Group Sales / Total Sales) * 100`.
8. **Promotion Sales**: `SUM(sales_amount) WHERE promotion_id IS NOT NULL`.
9. **Baseline Sales**: Average sales of comparable non-promotional period.
10. **Promotion Uplift %**: `((Promotion Sales - Baseline Sales) / Baseline Sales) * 100`.
11. **Opening Inventory**: Stock level on the first day of the period.
12. **Closing Inventory**: Stock level on the last day of the period.
13. **Inventory Reduction %**: `((Opening - Closing) / Opening) * 100`.
14. **Sell-Through %**: `(Units Sold / (Opening + Received)) * 100`.
15. **Stockout Risk**: `% of days in period where closing inventory is 0`.
16. **Excess Inventory**: `Closing Stock - (Average Daily Sales * 30)`.
17. **Data Completeness %**: Ratio of non-null fields to total fields.

---

## Safety and Security Safeguards

- **No Raw SQL Execution**: The LLM is never allowed to generate raw SQL strings. It generates a structured operation plan that is compiled using hardcoded mappings.
- **SQL Injection Prevention**: Filter values are bound to query variables using `?` placeholders. Identifiers are checked against an allowlist of database table and column names.
- **Read-Only Mode**: SQLite connections are opened using the URI `file:promoinsight.db?mode=ro` to enforce read-only execution at the database level.
- **Causal Wording Sanitization**: Automatically scans text outputs and sanitizes causal verbs to ensure statements report correlation and association.
- **NaN / Infinite Protection**: Scans Pandas DataFrames and replaces undefined states with `0.0`.

---

## Setup & Running Instructions

Execute the following commands in sequence from your terminal:

```bash
# 1. Initialize virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic data CSVs
python generate_data.py

# 4. Initialize database and schemas
python setup_database.py

# 5. Run test suite
pytest

# 6. Launch Streamlit UI
streamlit run app.py
```

---

## Sample Questions & Context Follow-Ups

The application accepts a broad range of natural-language questions:

- **Aggregations**: "What was the average selling price of Energy Drinks?" or "Total sales in the South region last month?"
- **Comparisons**: "Compare North and West region revenue for the last quarter."
- **Rankings**: "Which five products generated the highest revenue?"
- **Trends**: "Show monthly sales for Fruit Juice."
- **Promotions**: "Did the latest campaign improve sales?" or "Compare sales during and before promotion P004."
- **Inventory Flow**: "Show products with high sales but low closing inventory."
- **Anomalies**: "Were there any unusual sales spikes in the South?"
- **Conversational Follow-ups**:
  - *Turn 1*: "What were total sales in the South region last month?"
  - *Turn 2*: "What about Fruit Juice only?" (Re-applies timeframe and metric, filtering only on Fruit Juice category).

### Ambiguous & Unsupported Queries
- **Ambiguity**: If a user asks "Which is the best product?", the system prompts: *"Should 'best' product be measured by total sales revenue, units sold, or promotional sales uplift?"*
- **Unsupported**: If a user asks "Show employee salaries in the North," the system returns: *"This question cannot be answered reliably from the currently available sales, promotion, product, region and inventory data."*

---

## Interview Explanation Reference

When presenting this project in an assessment interview, emphasize:
1. **Generic Operation Planner**: Highlight that the system isn't bound to seven fixed intents. By using 11 primitive operations (`aggregate`, `rank`, `trend`, etc.), it can answer thousands of unique, unseen question combinations.
2. **Determinism over LLM Hallucinations**: Explain that calculations (like uplift or inventory risk) are performed deterministically in Pandas/SQL rather than relying on an LLM to perform arithmetic.
3. **Database Security Sandboxing**: Describe the URI read-only connection strategy and parameter binding which prevents SQL injection attacks even if malicious prompts bypass the validation layers.
