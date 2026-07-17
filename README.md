# 🚀 PromoInsight AI

> **A reliable, schema-aware conversational analytics assistant for FMCG promotion, sales, and inventory intelligence**

PromoInsight AI is a conversational analytics system built for FMCG beverage businesses. It allows users to ask natural-language questions about sales, promotions, products, regions, categories, brands, and inventory, and receive validated, business-friendly insights.

Unlike a general-purpose chatbot, PromoInsight AI does not allow the AI layer to independently calculate business figures or execute unrestricted SQL. The AI layer is used only to understand the user’s request and create a structured analytical plan. All calculations are performed through deterministic, parameterized SQL and Python logic.

---

## 🎯 Business Problem

FMCG business teams often depend on analysts for repeated questions such as:

- Which region generated the highest sales?
- Which category performed best during promotions?
- What percentage of revenue came from a specific category?
- Did inventory decrease during a campaign?
- Which products may face stockout risk?
- Were there unusual sales spikes?

This dependency can delay decision-making and create inconsistent interpretations across teams.

PromoInsight AI provides a governed self-service analytics interface that delivers faster, transparent, and reproducible answers.

---

## ✨ Key Features

- 🗣️ Natural-language analytical question processing
- 🧠 Schema-aware metric and dimension resolution
- 📊 Sales, revenue, units, pricing, growth, and contribution analysis
- 🌍 Region, category, brand, product, and promotion comparisons
- 📈 Ranking, comparison, trend, and anomaly analysis
- 🎯 Promotion uplift and campaign-performance analysis
- 📦 Inventory movement, stockout-risk, and excess-stock analysis
- ✅ Data-quality and completeness checks
- 🔁 Follow-up question support
- 🔒 Parameterized and read-only SQL execution
- 🔍 Query-plan, SQL, and result transparency
- 💬 Business-friendly response generation

---

## 🏗️ System Architecture

```text
Natural-Language Question
          ↓
Schema-Aware Intent Resolution
          ↓
Structured Query Plan
          ↓
Schema and Business-Rule Validation
          ↓
Parameterized SQL Compilation
          ↓
Read-Only SQLite Execution
          ↓
Result and Claim Validation
          ↓
Business-Friendly Insight
```

### Core Design Principle

The AI layer is responsible for:

- Understanding the user’s question
- Identifying the analytical intent
- Resolving metrics, dimensions, filters, and time periods
- Producing a structured query plan
- Converting verified results into natural language

The AI layer is not responsible for:

- Calculating business figures
- Executing unrestricted SQL
- Inventing missing values
- Producing unsupported conclusions
- Presenting correlation as proven causation

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| User Interface | Streamlit |
| Programming Language | Python |
| Database | SQLite |
| Data Processing | Pandas |
| Validation | Pydantic |
| Visualisation | Plotly |
| Testing | Pytest |
| Version Control | Git and GitHub |

---

## 🗂️ Dataset

The project uses a reproducible synthetic FMCG beverage dataset containing:

- Product master data
- Region master data
- Promotion details
- Sales transactions
- Inventory records

**Dataset period:** 1 July 2025 to 30 June 2026

The dataset is created only for demonstration and assessment purposes. It does not represent a real company or contain confidential business information.

---

## 📁 Project Structure

```text
PromoInsight-AI/
│
├── app.py
├── generate_data.py
├── setup_database.py
├── requirements.txt
├── pytest.ini
│
├── data/
│   ├── products.csv
│   ├── regions.csv
│   ├── promotions.csv
│   ├── sales.csv
│   └── inventory.csv
│
├── database/
│   └── promoinsight.db
│
├── src/
│   ├── __init__.py
│   ├── analytics_engine.py
│   ├── anomaly_detection.py
│   ├── chart_generator.py
│   ├── config.py
│   ├── data_quality.py
│   ├── llm_query_planner.py
│   ├── metadata_catalog.py
│   ├── metric_catalog.py
│   ├── models.py
│   ├── promotion_analysis.py
│   ├── query_validator.py
│   ├── response_generator.py
│   ├── result_validator.py
│   ├── rule_based_parser.py
│   ├── schema_context.py
│   ├── sql_compiler.py
│   ├── sql_executor.py
│   └── utils.py
│
├── tests/
├── examples/
└── docs/
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/G-Sneha08/PromoInsight-AI.git
cd PromoInsight-AI
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS or Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🗄️ Database Setup

The generated SQLite database is already included at:

```text
database/promoinsight.db
```

To regenerate the synthetic dataset and rebuild the database:

```bash
python generate_data.py
python setup_database.py
```

---

## ▶️ Run the Application

```bash
python -m streamlit run app.py
```

Open the application in your browser at:

```text
http://localhost:8501
```

---

## 💡 Example Questions

```text
Which region generated the highest sales last month?

Which brand earned the most revenue in the South region?

What percentage of total revenue came from Fruit Juice?

Which product sold the most units last quarter?

Which promotion had the highest uplift?

Compare total sales across all regions.

Which products may face stockout risk?

How complete is the inventory dataset?

Were there unusual sales spikes last month?

Show monthly sales for Energy Drinks.
```

These examples are not hardcoded. The system dynamically resolves supported combinations of analytical operations, metrics, dimensions, filters, rankings, and time periods.

---

## 🔁 Follow-Up Question Support

PromoInsight AI supports conversational context.

```text
User: Which region generated the highest sales last quarter?

User: What about Energy Drinks only?

User: Show it monthly.
```

The system preserves valid context such as the selected metric, time period, filters, and resolved business entity when appropriate.

---

## 🧪 Testing

Run the complete test suite:

```bash
python -m pytest -v
```

The tests cover:

- Query-plan generation
- Metric and dimension resolution
- Schema validation
- SQL compilation
- SQL injection protection
- Read-only database execution
- Promotion analysis
- Inventory analysis
- Data-quality checks
- Result validation
- Response formatting
- Follow-up question handling
- End-to-end analytical workflows

---

## 🔐 Reliability and Safety

PromoInsight AI includes the following controls:

- Parameterized SQL queries
- Read-only database access
- Allow-listed tables, columns, joins, and operators
- Schema and metric validation
- Query-plan consistency checks
- Unsupported-question handling
- Clarification for ambiguous requests
- Result-grounded natural-language responses
- Blocking of unsupported numerical claims
- Non-causal language for promotion analysis
- Data-quality and sufficiency warnings

---

## ⚠️ Limitations

- The project uses synthetic data.
- The system operates only on the available schema and metric catalogue.
- Promotion uplift indicates association with a selected baseline and does not prove causation.
- Exact forecasting and future revenue prediction are outside the current scope.
- Complex analytical questions may require clarification when the metric or comparison target is ambiguous.

---

## 📋 Assessment Details

**Assessment:** OneTapp Consulting – Assessment Round 1  
**Specialisation:** AI/ML Engineer  
**Candidate:** G Sneha  
**College:** REVA University  
**SRN:** R23EJ040  

---

## 🔗 Repository

[View PromoInsight AI on GitHub](https://github.com/G-Sneha08/PromoInsight-AI)

---

## 👩‍💻 Author

**G Sneha**  
B.Tech in Computer Science and Information Technology  
REVA University  

GitHub: [G-Sneha08](https://github.com/G-Sneha08)
