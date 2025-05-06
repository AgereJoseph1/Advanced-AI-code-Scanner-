import ast
import sqlparse
import streamlit as st
import pandas as pd
import openai
from typing import List, Dict, Tuple
import os

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------------- SCRIPT ANALYSIS UTILS -----------------------------

def extract_python_entities(script: str) -> Dict:
    tree = ast.parse(script)
    functions, variables, file_paths, configs = [], [], [], []
    sql_variables = {}
    assignments = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if targets:
                assignments[targets[0]] = ast.unparse(node.value)

                if isinstance(node.value, ast.Constant):
                    val = node.value.value
                    if isinstance(val, str):
                        if '/' in val or '\\' in val:
                            file_paths.append(val)
                        elif 'TABLE' in val.upper():
                            configs.append(val)
                elif isinstance(node.value, ast.Subscript):
                    configs.append(ast.unparse(node.value))

            variables.extend(targets)

        elif isinstance(node, ast.Expr):
            # Check if it's a spark.sql(<some_variable>)
            if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'attr') and node.value.func.attr == 'sql':
                if node.value.args:
                    arg = node.value.args[0]
                    if isinstance(arg, ast.Name):
                        sql_variables[arg.id] = assignments.get(arg.id, '')

    return {
        "functions": list(set(functions)),
        "variables": list(set(variables)),
        "file_paths": list(set(file_paths)),
        "configs": list(set(configs)),
        "sql_vars": sql_variables
    }

def extract_inline_sql(script: str) -> List[str]:
    return [line.strip() for line in script.split('\n') if 'SELECT' in line.upper() or 'create table' in line.lower()]

def parse_sql_tables(query: str) -> List[str]:
    parsed = sqlparse.parse(query)[0]
    tables = []
    from_seen = False
    for token in parsed.tokens:
        if token.ttype is sqlparse.tokens.Keyword and token.value.upper() in ("FROM", "JOIN"):
            from_seen = True
        elif from_seen:
            if isinstance(token, sqlparse.sql.Identifier):
                tables.append(token.get_real_name())
                from_seen = False
            elif isinstance(token, sqlparse.sql.IdentifierList):
                for identifier in token.get_identifiers():
                    tables.append(identifier.get_real_name())
                from_seen = False
    return tables

# ----------------------------- LLM UTILS ----------------------------------

def gpt_summarize_logic(sql: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a data analyst helping banks understand SQL logic."},
                {"role": "user", "content": f"Explain this SQL logic in simple terms for business understanding: {sql}"}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Error from LLM: {str(e)}"

# ---------------------------- STREAMLIT UI --------------------------------

st.title("Universal Scanner MVP")
st.write("Upload a Python or PySpark script to analyze and extract data lineage and logic.")

uploaded_file = st.file_uploader("Choose your Python/PySpark script", type=["py"])

if uploaded_file:
    script_text = uploaded_file.read().decode("utf-8")

    st.subheader("🔍 Extracting Entities...")
    entities = extract_python_entities(script_text)
    st.write(entities)

    st.subheader("📊 Extracting SQL Queries...")
    sql_queries = extract_inline_sql(script_text)
    sql_queries.extend(list(entities.get("sql_vars", {}).values()))
    st.write(sql_queries)

    table_data = []
    logic_data = []

    for query in sql_queries:
        if not query.strip():
            continue
        tables = parse_sql_tables(query)
        explanation = gpt_summarize_logic(query)

        for table in tables:
            table_data.append({
                "Entity Type": "Table",
                "Name": table,
                "Used In Query": query
            })

        logic_data.append({
            "SQL": query,
            "Business Explanation": explanation
        })

    df_entities = pd.DataFrame(table_data +
                               [{"Entity Type": "File", "Name": path, "Used In Query": ""} for path in entities['file_paths']] +
                               [{"Entity Type": "Config", "Name": cfg, "Used In Query": ""} for cfg in entities['configs']])

    df_logic = pd.DataFrame(logic_data)

    st.subheader("📥 Download Results")
    with pd.ExcelWriter("universal_scanner_output.xlsx") as writer:
        df_entities.to_excel(writer, sheet_name="Entities", index=False)
        df_logic.to_excel(writer, sheet_name="Transformations", index=False)

    with open("universal_scanner_output.xlsx", "rb") as f:
        st.download_button("Download Excel Output", data=f, file_name="universal_scanner_output.xlsx")
