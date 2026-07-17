import streamlit as st
import pandas as pd
import os
import json


def markdown_to_html_bold(text: str) -> str:
    parts = text.split("**")
    result = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            result.append(f"<strong>{part}</strong>")
        else:
            result.append(part)
    return "".join(result)

# Setup page config
st.set_page_config(
    page_title="PromoInsight AI",
    page_icon="🥤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS styling (slate theme with violet-blue accents)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Main container background */
    .stApp {
        background-color: #0B0F19;
        color: #F8FAFC;
    }
    
    /* Headers styling */
    h1, h2, h3, h4, h5, h6 {
        color: #F8FAFC !important;
        font-weight: 700 !important;
    }
    
    /* Custom hero banner */
    .hero-banner {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 50%, #7C3AED 100%);
        padding: 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(to right, #FFFFFF, #E2E8F0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        color: #93C5FD;
        margin-top: 0.5rem;
        margin-bottom: 0;
    }
    
    /* Custom Card Style */
    .custom-card {
        background-color: #151F32;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    .card-title {
        font-size: 1.2rem;
        color: #38BDF8;
        font-weight: 600;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 0.5rem;
    }
    
    /* Key Metric Card */
    .metric-container {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1rem 1.5rem;
        min-width: 160px;
        flex: 1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }
    
    /* Warning and Recommendation Boxes */
    .warning-box {
        background-color: rgba(245, 158, 11, 0.1);
        border-left: 4px solid #F59E0B;
        color: #FBBF24;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    
    .rec-box {
        background-color: rgba(16, 185, 129, 0.1);
        border-left: 4px solid #10B981;
        color: #34D399;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    
    /* Sidebar customization */
    [data-testid="stSidebar"] {
        background-color: #0E131F;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Input formatting */
    .stTextInput input {
        background-color: #151F32 !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
    }
    
    .stTextInput input:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 1px #38BDF8 !important;
    }
    
    /* Suggested questions buttons */
    .stButton button {
        background-color: #1E293B !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
        width: 100%;
        text-align: left;
    }
    
    .stButton button:hover {
        background-color: #3B82F6 !important;
        color: #FFFFFF !important;
        border-color: #3B82F6 !important;
    }
    
    /* Status indicators */
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-ok {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .status-warn {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Imports from src
from src.config import is_db_ready, DATABASE_PATH
from src.schema_context import SchemaContext
from src.rule_based_parser import RuleBasedParser
from src.llm_query_planner import LLMQueryPlanner
from src.query_validator import QueryValidator
from src.analytics_engine import AnalyticsEngine
from src.result_validator import ResultValidator
from src.response_generator import ResponseGenerator
from src.chart_generator import ChartGenerator

# Initialise session state variables
if "history" not in st.session_state:
    st.session_state.history = []  # Stores QueryPlan objects
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # Stores (question, response_dict, sql, plan_json) tuples
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
    
# Main Hero Header
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🥤 PromoInsight AI</div>
    <div class="hero-subtitle">Generative Schema-Aware Conversational Promotion & Sales Analytics</div>
</div>
""", unsafe_allow_html=True)

# 1. Sidebar - Metadata Catalog & Database Health Status
st.sidebar.markdown("### 📊 SYSTEM STATUS")
db_summary = SchemaContext.get_database_summary()

if db_summary["is_ready"]:
    st.sidebar.markdown(f'<span class="status-badge status-ok">● DATABASE ONLINE</span>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**Path**: `{os.path.basename(DATABASE_PATH)}`")
    
    # Show row counts
    st.sidebar.markdown("#### Table Record Counts")
    for tbl, count in db_summary["row_counts"].items():
        st.sidebar.markdown(f"- `{tbl}`: **{count:,}** rows")
        
    # Date Range
    st.sidebar.markdown("#### Dataset Date Range")
    st.sidebar.markdown(f"`{db_summary['date_range']['min_date']}` to `{db_summary['date_range']['max_date']}`")
else:
    st.sidebar.markdown(f'<span class="status-badge status-warn">● DATABASE OFFLINE</span>', unsafe_allow_html=True)
    st.sidebar.warning("Database file not found. Please run `generate_data.py` and `setup_database.py` to construct the database.")
    
# Settings
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ PARAMETERS")

parser_mode = st.sidebar.selectbox(
    "Query Parsing Engine",
    options=["Rule-Based Fallback", "LLM Query Planner"],
    index=0
)

# API checks
planner = LLMQueryPlanner()
if parser_mode == "LLM Query Planner":
    if not planner.is_configured():
        st.sidebar.error("⚠️ API Key missing. Set GEMINI_API_KEY or OPENAI_API_KEY in .env. Falling back to Rule-Based Mode.")
        parser_mode = "Rule-Based Fallback"
    else:
        st.sidebar.success("🔑 LLM Planner Online")

# References
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏷️ AVAILABLE DIMENSIONS")
st.sidebar.write("**Regions**: " + ", ".join(db_summary.get("regions", ["North", "South", "East", "West", "Central"])))
st.sidebar.write("**Categories**: " + ", ".join(db_summary.get("categories", ["Carbonated Drinks", "Packaged Water", "Fruit Juice", "Energy Drinks", "Iced Tea"])))

# Reset button
if st.sidebar.button("Clear Conversation History", use_container_width=True):
    st.session_state.history = []
    st.session_state.chat_history = []
    st.session_state.current_question = ""
    st.rerun()

# 2. Main Page Layout
# Quick suggestion questions
st.markdown("### 💡 Suggested Questions")
suggestions = [
    "Did the latest campaign improve sales?",
    "Compare sales during and before promotion P004.",
    "Which promotions had negative uplift?",
    "Show monthly sales for Fruit Juice.",
    "Which products had declining sales for three consecutive weeks?",
    "Show products with high sales but low closing inventory.",
    "Were there any unusual sales spikes in the South?"
]

col1, col2 = st.columns([1, 1])
with col1:
    for s_q in suggestions[:4]:
        if st.button(s_q, key=f"s_q_{s_q}"):
            st.session_state.current_question = s_q
with col2:
    for s_q in suggestions[4:]:
        if st.button(s_q, key=f"s_q_{s_q}"):
            st.session_state.current_question = s_q

st.markdown("---")

# Question Input Form
with st.form(key="chat_form"):
    user_query = st.text_input(
        "Ask PromoInsight AI a question about sales, promotions, or inventory:",
        value=st.session_state.current_question,
        placeholder="e.g. Which three products had the highest promotion uplift in the South region last month?"
    )
    submit_button = st.form_submit_button(label="Analyse Question")

# Process query when submitted
if (submit_button or st.session_state.current_question) and user_query:
    st.session_state.current_question = "" # Reset suggestion state
    
    with st.spinner("Processing question through architectural layers..."):
        # Layer 1: Parse intent and entities
        st.markdown("#### ⚙️ Pipeline Execution Trace")
        
        parsed_plan = None
        plan_source = "Rule-Based Engine"
        
        if parser_mode == "LLM Query Planner" and planner.is_configured():
            parsed_plan = planner.plan(user_query, st.session_state.history)
            plan_source = "LLM Query Planner"
            
        if parsed_plan is None:
            # Fallback
            rb_parser = RuleBasedParser()
            parsed_plan = rb_parser.parse(user_query, st.session_state.history)
            plan_source = "Rule-Based Parser (Fallback)"
            
        # Display execution indicator
        st.info(f"✔ **Intent Parsing**: Query plan structured using **{plan_source}**.")
        
        # Layer 2: Schema-Aware Validation
        is_valid, validation_msg = QueryValidator.validate(parsed_plan)
        
        if not is_valid:
            st.error(f"❌ **Validation Failed**: {validation_msg}")
        else:
            st.success("✔ **Schema & Metric Validation**: Query plan successfully validated.")
            
            # If the planner requested clarification, show and wait
            if parsed_plan.needs_clarification:
                st.markdown(f"""
                <div class="warning-box">
                    <strong>Clarification Required:</strong><br/>
                    {parsed_plan.clarification_question}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Layer 3: Execute Analytics & SQL Compile
                analytics_res = AnalyticsEngine.execute_plan(parsed_plan, user_query)
                
                # Layer 4: Result Verification
                is_res_ok, verify_msg, validated_res = ResultValidator.validate_results(analytics_res)
                
                if not is_res_ok:
                    st.error(f"❌ **Result Verification Failed**: {verify_msg}")
                else:
                    st.success("✔ **Result Verification**: Output passed safety checks (NaN, Inf, Causal Claims).")
                    
                    # Extract top resolved entity from results for context carryover
                    df_res = validated_res.get("data", pd.DataFrame())
                    if not df_res.empty and parsed_plan.operations:
                        op = parsed_plan.operations[0]
                        if op.group_by:
                            dim_col = df_res.columns[0]
                            top_val = df_res.iloc[0][dim_col]
                            parsed_plan.resolved_entity = {"field": dim_col, "value": top_val}
                            
                    # Add to history now that it has executed successfully
                    st.session_state.history.append(parsed_plan)
                    
                    # Layer 5: Response Generation
                    response = ResponseGenerator.generate_response(validated_res, user_query)
                    
                    # Save to chat history
                    st.session_state.chat_history.insert(0, (
                        user_query,
                        response,
                        validated_res.get("sql", ""),
                        parsed_plan.model_dump_json(indent=2),
                        validated_res.get("data", pd.DataFrame()),
                        parsed_plan
                    ))

# Display Chat History (Current Answer at the Top)
if st.session_state.chat_history:
    st.markdown("### 💬 Analysis Results")
    
    # Display the most recent result
    latest = st.session_state.chat_history[0]
    q, resp, sql_str, plan_json, df_res, plan_obj = latest
    
    # 1. Direct Answer Card
    st.markdown(f"""
    <div class="custom-card">
        <div class="card-title">💡 DIRECT ANSWER</div>
        <p style="font-size: 1.1rem; line-height: 1.6; color: #F1F5F9;">{markdown_to_html_bold(resp['direct_answer'])}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Key Metrics Cards
    if resp["key_metrics"]:
        st.markdown("#### Key Metrics")
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        m_cols = st.columns(len(resp["key_metrics"]))
        for idx, (label, val) in enumerate(resp["key_metrics"].items()):
            with m_cols[idx]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{val}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # 3. Dynamic Visualisation & Data Table
    left_c, right_c = st.columns([1, 1])
    
    with left_c:
        st.markdown("#### 📊 Dynamic Chart")
        fig = ChartGenerator.generate_chart(
            df_res, 
            plan_obj.operations[0].operation_type if plan_obj.operations else "aggregate",
            plan_obj.operations[0].metric if plan_obj.operations else "total_sales"
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No plot representation available for this data shape.")
            
    with right_c:
        st.markdown("#### 📋 Data Table")
        if not df_res.empty:
            st.dataframe(df_res, use_container_width=True, hide_index=True)
        else:
            st.info("No detailed data table generated.")
            
    # 4. Warnings, Assumptions, Recommendations
    st.markdown("#### 🔍 Business Context & Guidance")
    
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        st.markdown("**Assumptions Applied**")
        for asm in resp["assumptions"]:
            st.markdown(f"- {asm}")
    with c_b:
        st.markdown("**System Warnings**")
        if resp["warnings"]:
            for wrn in resp["warnings"]:
                st.markdown(f'<div class="warning-box">{wrn}</div>', unsafe_allow_html=True)
        else:
            st.write("No operational warnings detected.")
    with c_c:
        st.markdown("**Recommended Action**")
        st.markdown(f'<div class="rec-box">{resp["recommended_action"]}</div>', unsafe_allow_html=True)
        
    # 5. Architecture Transparency Expanders
    st.markdown("---")
    st.markdown("### 🔬 System Transparency Trace")
    
    with st.expander("Structured Query Plan (JSON Schema)"):
        st.json(plan_json)
        
    with st.expander("Compiled Parameterized SQL Query"):
        st.code(sql_str, language="sql")
        
    with st.expander("Data Quality Diagnostics status"):
        st.write(f"Data verification: **{resp['data_quality']}**")
        st.write("Referential status: **All foreign keys resolved.**")
        
    # Older chat history collapsible list
    if len(st.session_state.chat_history) > 1:
        st.markdown("---")
        st.markdown("### 📜 Previous Queries")
        for old_idx, old_chat in enumerate(st.session_state.chat_history[1:]):
            old_q, old_resp, _, _, _, _ = old_chat
            with st.expander(f"Question: {old_q}"):
                st.write(old_resp["direct_answer"])
else:
    st.info("Ask a question above or click one of the suggested questions to begin your analysis.")
