import sys
from pathlib import Path

# Ensure project root is in sys.path so 'app' can be imported when running via Streamlit
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import streamlit as st
import pandas as pd
from app.pipeline import DatricsText2SQLPipeline
from app.config import settings
from app.schemas.sql import SQLGenerationStrategy

st.set_page_config(
    page_title="Datrics Text2SQL Studio",
    page_icon="🔍",
    layout="wide"
)

# Initialize Pipeline Cache
@st.cache_resource
def load_pipeline():
    return DatricsText2SQLPipeline()

pipeline = load_pipeline()

# Title and header
st.title("⚡ Datrics Text2SQL Framework")
st.caption("Research implementation of *arXiv:2506.12234v1* with RAG, Progressive Retrieval, and AST Safety Validation")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration & Knowledge Base")
    st.info(f"**LLM Provider**: `{settings.LLM_PROVIDER.upper()}`\n\n**Embedding**: `{settings.EMBEDDING_MODEL_NAME}`\n\n**Database**: SQLite (`{Path(settings.DATABASE_PATH).name}`)")

    st.subheader("Knowledge Base Actions")
    if st.button("🔄 Rebuild Knowledge Base", use_container_width=True):
        with st.spinner("Re-indexing table docs and Q-SQL examples into ChromaDB..."):
            stats = pipeline.indexing_pipeline.index_all()
            st.success(f"Indexed {stats['indexed_tables']} tables & {stats['indexed_examples']} examples!")

    st.markdown("---")
    st.subheader("Upload Q-SQL Examples")
    uploaded_file = st.file_uploader("Upload new examples (JSON format)", type=["json"])
    if uploaded_file is not None:
        try:
            new_data = json.load(uploaded_file)
            st.success(f"Loaded {len(new_data)} examples. Click Rebuild Knowledge Base to commit.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

# Main Tabs
tab_query, tab_schema, tab_examples, tab_rules = st.tabs([
    "💬 Query Generator", "🗄️ Database Documentation", "📚 Q-SQL Knowledge Base", "⚖️ Business Rules"
])

# -------------------------------------------------------------
# TAB 1: Query Generator
# -------------------------------------------------------------
with tab_query:
    col_input, col_preset = st.columns([3, 1])
    with col_preset:
        preset_q = st.selectbox(
            "Quick Example Prompts:",
            [
                "Custom query...",
                "Show all active customers in the USA.",
                "What is the total revenue generated from completed orders?",
                "Find the top 3 customers by total spending on completed orders.",
                "List all products that are currently in stock and active.",
                "Calculate total amount collected per payment method.",
                "Show me top subscribers", # Ambiguous test
                "Predict the sales forecast for next quarter using linear regression." # Unsupported test
            ]
        )

    with col_input:
        default_val = "" if preset_q == "Custom query..." else preset_q
        user_query = st.text_input(
            "Enter your natural language question:",
            value=default_val,
            placeholder="e.g. Find total spending for each customer on completed orders"
        )
        submit_btn = st.button("Generate & Execute SQL", type="primary")

    if submit_btn and user_query:
        with st.spinner("Processing through Datrics RAG pipeline..."):
            response = pipeline.process_query(user_query)

        # Clarification warning if query was ambiguous or unsupported
        if response.clarification_requested:
            st.warning(f"⚠️ **Clarification Requested**: {response.clarification_requested}")

        # Strategy and Status Badges
        col_badge1, col_badge2, col_badge3 = st.columns(3)
        with col_badge1:
            st.metric("Generation Strategy", response.strategy_used.value)
        with col_badge2:
            val_status = response.validation.status.value if response.validation else "SKIPPED"
            st.metric("AST Validation Status", val_status)
        with col_badge3:
            exec_time = f"{response.execution.execution_time_ms} ms" if response.execution else "N/A"
            st.metric("Execution Time", exec_time)

        # Generated SQL & Explanation
        st.subheader("Generated SQL Query")
        st.code(response.sql or "-- No SQL generated (Clarification requested)", language="sql")

        st.subheader("Query Explanation & Rationale")
        st.write(response.explanation)

        # Tabular Execution Results
        if response.execution and response.execution.success:
            st.subheader(f"Query Results ({response.execution.row_count} rows)")
            if response.execution.rows:
                df = pd.DataFrame(response.execution.rows, columns=response.execution.columns)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Query returned 0 rows.")
        elif response.execution and not response.execution.success:
            st.error(f"Execution Error: {response.execution.error_message}")

        # Diagnostics Expander
        with st.expander("🛠️ Pipeline Diagnostics & Context"):
            st.markdown(f"**Referenced Tables:** `{response.referenced_tables}`")
            st.markdown(f"**Retrieved Examples Used:** `{response.relevant_examples_used}`")
            if response.warnings:
                st.markdown(f"**Warnings:** {response.warnings}")

# -------------------------------------------------------------
# TAB 2: Database Documentation
# -------------------------------------------------------------
with tab_schema:
    st.header("Structured Database Documentation (JSON)")
    st.caption("Extracted via schema introspection and multi-run entity voting")

    for tbl_name, doc in pipeline.indexing_pipeline.table_docs.items():
        with st.expander(f"📁 Table: `{tbl_name}` — {doc.summary}", expanded=False):
            st.markdown(f"**Purpose:** {doc.purpose}")
            st.markdown(f"**Dependencies:** {doc.dependencies_thoughts}")
            st.markdown(f"**Keys:** `{doc.keys}` | **Connected Tables:** `{doc.connected_tables}`")
            st.markdown(f"**Strong Entities (Voted):** `{doc.strong_entities}`")

            col_df = pd.DataFrame([{"Column": c.column, "Description": c.description} for c in doc.columns])
            st.table(col_df)

# -------------------------------------------------------------
# TAB 3: Knowledge Base
# -------------------------------------------------------------
with tab_examples:
    st.header("Indexed Question–SQL Example Pairs")
    st.caption("Normalized examples stored across 7 vector representations in ChromaDB")

    ex_list = list(pipeline.indexing_pipeline.train_examples.values())
    for ex in ex_list:
        with st.expander(f"🏷️ [{ex.id}] {ex.question}"):
            st.code(ex.sql, language="sql")
            st.markdown(f"**Normalized:** `{ex.normalized_question}`")
            st.markdown(f"**Main Clause:** `{ex.main_clause}`")
            st.markdown(f"**Tables:** `{ex.tables}`")
            if ex.variations:
                st.markdown("**Paraphrased Variations:**")
                for v in ex.variations:
                    st.markdown(f"- {v}")

# -------------------------------------------------------------
# TAB 4: Business Rules
# -------------------------------------------------------------
with tab_rules:
    st.header("Domain-Specific Business Rules (R)")
    st.caption("Business logic integrated into table refinement and SQL generation")

    for rule in pipeline.indexing_pipeline.business_rules:
        st.markdown(f"- **{rule['name']}**: {rule['rule']} (Tables: `{rule['applicable_tables']}`)")
