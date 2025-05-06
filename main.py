import ast
import os
import re
import sqlparse
import streamlit as st
import pandas as pd
import openai
from typing import List, Dict, Tuple, Set, Optional
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import zipfile
import tempfile

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------------- SCRIPT ANALYSIS UTILS -----------------------------

class DataFlowAnalyzer:
    """Class to analyze data flow in Python scripts"""
    
    def __init__(self):
        self.data_flow_graph = nx.DiGraph()
        self.all_entities = {
            "functions": set(),
            "variables": set(),
            "file_paths": set(),
            "configs": set(),
            "sql_queries": set(),
            "transformations": [],
            "dataframes": {},
            "source_target_mapping": []
        }
        self.script_mapping = {}
        
    def extract_python_entities(self, script: str, filename: str) -> Dict:
        """Extract entities from a Python script"""
        tree = ast.parse(script)
        functions, variables, file_paths, configs = [], [], [], []
        sql_variables = {}
        assignments = {}
        df_transformations = []
        dataframes = {}

        # First pass to collect all assignments
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                for target in targets:
                    # Store the exact assignment logic
                    assignments[target] = ast.unparse(node.value)
                    variables.append(target)
                    
                    # Check if it's a DataFrame creation or transformation
                    if isinstance(node.value, ast.Call):
                        func = node.value.func
                        if hasattr(func, 'attr'):
                            # Check for pd.read_csv, pd.read_excel, etc.
                            if hasattr(func, 'value') and hasattr(func.value, 'id') and func.value.id == 'pd' and func.attr.startswith('read_'):
                                # This is a source dataframe
                                dataframes[target] = {
                                    'type': 'source',
                                    'method': func.attr,
                                    'source': ast.unparse(node.value.args[0]) if node.value.args else 'unknown'
                                }
                            
                            # Check for DataFrame transformations
                            df_methods = ['groupby', 'filter', 'sort_values', 'merge', 'join', 'concat', 'apply', 'map', 'pivot', 'melt']
                            if any(func.attr == method for method in df_methods) and hasattr(func, 'value'):
                                source_df = ast.unparse(func.value)
                                df_transformations.append({
                                    'target': target,
                                    'source': source_df,
                                    'operation': func.attr,
                                    'details': ast.unparse(node.value)
                                })
                                # Track as a transformation dataframe
                                dataframes[target] = {
                                    'type': 'transformation',
                                    'method': func.attr,
                                    'source': source_df
                                }
                                
                # Special handling for file paths and configurations
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    val = node.value.value
                    if '/' in val or '\\' in val or '.csv' in val or '.xlsx' in val or '.txt' in val:
                        file_paths.append(val)
                    elif any(keyword in val.upper() for keyword in ['TABLE', 'CONFIG', 'PARAM', 'SETTING']):
                        configs.append(val)

        # Second pass for function definitions and SQL queries
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                # Analyze function body for data transformations
                self._analyze_function_body(node, assignments, df_transformations)
            
            # Detect SQL queries in string variables or direct calls
            elif isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    sql = node.value.value
                    if self._is_sql_query(sql):
                        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                        for target in targets:
                            sql_variables[target] = sql
            
            # Check for SQL in function calls like spark.sql() or execute_sql()
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if hasattr(call.func, 'attr') and call.func.attr in ['sql', 'execute', 'query']:
                    if call.args:
                        arg = call.args[0]
                        if isinstance(arg, ast.Name) and arg.id in assignments:
                            sql_variables[arg.id] = assignments[arg.id]
                        elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if self._is_sql_query(arg.value):
                                sql_variables[f"inline_sql_{len(sql_variables)}"] = arg.value

        # Extract business rules by analyzing complex if conditions
        business_rules = self._extract_business_rules(tree)
        
        # Store results for this specific file
        file_results = {
            "filename": filename,
            "functions": list(set(functions)),
            "variables": list(set(variables)),
            "file_paths": list(set(file_paths)),
            "configs": list(set(configs)),
            "sql_vars": sql_variables,
            "df_transformations": df_transformations,
            "dataframes": dataframes,
            "business_rules": business_rules
        }
        
        self.script_mapping[filename] = file_results
        
        # Update global entities
        self.all_entities["functions"].update(set(functions))
        self.all_entities["variables"].update(set(variables))
        self.all_entities["file_paths"].update(set(file_paths))
        self.all_entities["configs"].update(set(configs))
        self.all_entities["sql_queries"].update(set(sql_variables.values()))
        self.all_entities["transformations"].extend(df_transformations)
        
        # Update dataframes with filename context
        for df_name, df_info in dataframes.items():
            self.all_entities["dataframes"][f"{filename}:{df_name}"] = df_info
            
            # Add to source-target mapping
            if df_info['type'] == 'source':
                self.all_entities["source_target_mapping"].append({
                    'source_type': 'file',
                    'source': df_info['source'],
                    'target_type': 'dataframe',
                    'target': f"{filename}:{df_name}",
                    'operation': df_info['method'],
                    'filename': filename
                })
            elif df_info['type'] == 'transformation':
                self.all_entities["source_target_mapping"].append({
                    'source_type': 'dataframe',
                    'source': f"{filename}:{df_info['source']}",
                    'target_type': 'dataframe',
                    'target': f"{filename}:{df_name}",
                    'operation': df_info['method'],
                    'filename': filename
                })
        
        return file_results
    
    def _is_sql_query(self, text: str) -> bool:
        """Check if a string is likely to be an SQL query"""
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 
                       'CREATE TABLE', 'INSERT INTO', 'UPDATE', 'DELETE FROM']
        text_upper = text.upper()
        return any(keyword in text_upper for keyword in sql_keywords)
    
    def _analyze_function_body(self, func_node: ast.FunctionDef, assignments: Dict, df_transformations: List) -> None:
        """Analyze a function body for data transformations"""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                for target in targets:
                    # Look for DataFrame operations
                    if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'attr'):
                        func = node.value.func
                        df_methods = ['groupby', 'filter', 'sort_values', 'merge', 'join', 'concat', 'apply']
                        if any(func.attr == method for method in df_methods) and hasattr(func, 'value'):
                            source_df = ast.unparse(func.value)
                            df_transformations.append({
                                'target': target,
                                'source': source_df,
                                'operation': func.attr,
                                'details': ast.unparse(node.value),
                                'in_function': func_node.name
                            })
    
    def _extract_business_rules(self, tree: ast.AST) -> List[Dict]:
        """Extract business rules from conditionals in the code"""
        rules = []
        
        for node in ast.walk(tree):
            # Extract rules from if statements
            if isinstance(node, ast.If):
                rule = {
                    'type': 'condition',
                    'condition': ast.unparse(node.test),
                    'actions': [ast.unparse(stmt) for stmt in node.body if not isinstance(stmt, ast.If)]
                }
                rules.append(rule)
            
            # Extract rules from function calls that suggest business logic
            elif isinstance(node, ast.Call) and hasattr(node.func, 'attr'):
                rule_keywords = ['validate', 'check', 'enforce', 'calculate', 'compute', 'apply_rule']
                if any(keyword in node.func.attr.lower() for keyword in rule_keywords):
                    rule = {
                        'type': 'function_call',
                        'function': ast.unparse(node.func),
                        'arguments': [ast.unparse(arg) for arg in node.args],
                        'full_call': ast.unparse(node)
                    }
                    rules.append(rule)
        
        return rules
    
    def parse_sql_tables_and_transformations(self, query: str) -> Dict:
        """Parse SQL query to extract tables and transformations"""
        try:
            parsed = sqlparse.parse(query)
            if not parsed:
                return {"tables": [], "columns": [], "transformations": []}
            
            statement = parsed[0]
            tables = []
            columns = []
            transformations = []
            
            # Extract tables
            from_seen = False
            for token in statement.tokens:
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
            
            # Extract columns and transformations
            select_seen = False
            for token in statement.tokens:
                if token.ttype is sqlparse.tokens.DML and token.value.upper() == "SELECT":
                    select_seen = True
                elif select_seen and isinstance(token, sqlparse.sql.IdentifierList):
                    for identifier in token.get_identifiers():
                        col_name = identifier.get_real_name()
                        columns.append(col_name)
                        
                        # Check for transformations in column expressions
                        col_str = str(identifier)
                        if ' AS ' in col_str or '(' in col_str:
                            transformations.append({
                                'type': 'column_transformation',
                                'expression': col_str
                            })
                
                # Check for GROUP BY, ORDER BY, etc.
                if token.ttype is sqlparse.tokens.Keyword and token.value.upper() in ["GROUP BY", "ORDER BY", "HAVING"]:
                    transformations.append({
                        'type': token.value.upper(),
                        'details': str(token.parent)
                    })
            
            return {
                "tables": tables,
                "columns": columns,
                "transformations": transformations
            }
        except Exception as e:
            return {"tables": [], "columns": [], "transformations": [], "error": str(e)}
    
    def analyze_all_sql_queries(self) -> None:
        """Analyze all SQL queries found in the scripts"""
        all_sql_queries = list(self.all_entities["sql_queries"])
        for query in all_sql_queries:
            if not query.strip():
                continue
                
            sql_analysis = self.parse_sql_tables_and_transformations(query)
            for table in sql_analysis["tables"]:
                # Add to source-target mapping
                # The target depends on the SQL operation (SELECT creates a result set)
                if "SELECT" in query.upper():
                    self.all_entities["source_target_mapping"].append({
                        'source_type': 'table',
                        'source': table,
                        'target_type': 'query_result',
                        'target': f"result_of_{table}_query",
                        'operation': 'SQL_SELECT',
                        'filename': 'sql_query'
                    })
    
    def build_data_flow_graph(self) -> nx.DiGraph:
        """Build a directed graph representing data flow"""
        G = nx.DiGraph()
        
        # Add nodes for all dataframes
        for df_key, df_info in self.all_entities["dataframes"].items():
            G.add_node(df_key, type='dataframe', **df_info)
        
        # Add nodes for all sources and targets
        for mapping in self.all_entities["source_target_mapping"]:
            source = mapping['source']
            target = mapping['target']
            
            # Add nodes if they don't exist
            if not G.has_node(source):
                G.add_node(source, type=mapping['source_type'])
            
            if not G.has_node(target):
                G.add_node(target, type=mapping['target_type'])
            
            # Add the edge with operation details
            G.add_edge(source, target, operation=mapping['operation'], filename=mapping.get('filename', ''))
        
        self.data_flow_graph = G
        return G
    
    def visualize_data_flow(self) -> None:
        """Create a visualization of the data flow graph"""
        G = self.data_flow_graph
        
        if not G.nodes():
            return None
            
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)
        
        # Draw different node types with different colors
        node_colors = {
            'file': 'lightblue',
            'dataframe': 'lightgreen',
            'table': 'salmon',
            'query_result': 'yellow',
            'source': 'orange',
            'transformation': 'purple'
        }
        
        for node_type, color in node_colors.items():
            nodes = [n for n, d in G.nodes(data=True) if d.get('type') == node_type]
            if nodes:
                nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=color, node_size=300, alpha=0.8, label=node_type)
        
        # Draw edges with labels for operations
        edge_labels = {(u, v): d['operation'] for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5, arrowsize=20)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        
        # Draw node labels
        node_labels = {}
        for node in G.nodes():
            if isinstance(node, str) and len(node) > 20:
                # Truncate long node names
                node_labels[node] = f"{node[:17]}..."
            else:
                node_labels[node] = node
                
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=10)
        
        plt.title("Data Flow Graph")
        plt.legend()
        plt.axis('off')
        return plt

# ----------------------------- LLM UTILS ----------------------------------

def gpt_summarize_logic(text: str, content_type: str = "sql") -> str:
    """Use GPT to summarize code logic"""
    try:
        if content_type == "sql":
            prompt = f"Explain this SQL logic in simple terms for business understanding: {text}"
        elif content_type == "transformation":
            prompt = f"Explain this data transformation in simple terms for business understanding: {text}"
        elif content_type == "business_rule":
            prompt = f"Explain this business rule in simple terms for non-technical stakeholders: {text}"
        else:
            prompt = f"Explain this code logic in simple terms for business understanding: {text}"
            
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a data analyst helping to understand code logic."},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Error from LLM: {str(e)}"

# ---------------------------- STREAMLIT UI --------------------------------

st.set_page_config(layout="wide")
st.title("Enhanced Universal Scanner")
st.write("Upload Python/PySpark scripts to analyze and extract data lineage, transformations, and business logic.")

upload_type = st.radio("Upload Type", ["Single File", "Multiple Files/Folder (ZIP)"])

analyzer = DataFlowAnalyzer()

if upload_type == "Single File":
    uploaded_file = st.file_uploader("Choose your Python/PySpark script", type=["py"])
    
    if uploaded_file:
        script_text = uploaded_file.read().decode("utf-8")
        filename = uploaded_file.name
        
        with st.spinner("Analyzing script..."):
            result = analyzer.extract_python_entities(script_text, filename)
            st.success(f"Analyzed {filename}")
else:
    uploaded_zip = st.file_uploader("Upload ZIP file containing Python scripts", type=["zip"])
    
    if uploaded_zip:
        with st.spinner("Extracting and analyzing scripts..."):
            # Create a temporary directory to extract files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the uploaded zip file
                zip_path = os.path.join(temp_dir, "uploaded.zip")
                with open(zip_path, "wb") as f:
                    f.write(uploaded_zip.getbuffer())
                
                # Extract the zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find all Python files
                python_files = []
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(".py"):
                            python_files.append(os.path.join(root, file))
                
                # Analyze each Python file
                for file_path in python_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            script_text = f.read()
                        
                        # Get the relative path
                        rel_path = os.path.relpath(file_path, temp_dir)
                        analyzer.extract_python_entities(script_text, rel_path)
                        
                    except Exception as e:
                        st.error(f"Error analyzing {file_path}: {str(e)}")
                
                st.success(f"Analyzed {len(python_files)} Python files")

# Display results if we have analyzed any scripts
if analyzer.script_mapping:
    analyzer.analyze_all_sql_queries()
    analyzer.build_data_flow_graph()
    
    # Set up tabs for different views
    tabs = st.tabs(["Overview", "Variable Tracking", "SQL Analysis", "Transformations", "Business Rules", "Data Flow"])
    
    with tabs[0]:
        st.header("Script Analysis Overview")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Files Analyzed")
            for filename in analyzer.script_mapping.keys():
                st.write(f"• {filename}")
        
        with col2:
            st.subheader("Metrics")
            st.write(f"Functions: {len(analyzer.all_entities['functions'])}")
            st.write(f"Variables: {len(analyzer.all_entities['variables'])}")
            st.write(f"File Paths: {len(analyzer.all_entities['file_paths'])}")
            st.write(f"SQL Queries: {len(analyzer.all_entities['sql_queries'])}")
            st.write(f"Transformations: {len(analyzer.all_entities['transformations'])}")
    
    with tabs[1]:
        st.header("Variable Tracking")
        
        # Create a dataframe of all variables
        var_data = []
        for filename, entities in analyzer.script_mapping.items():
            for var in entities["variables"]:
                var_data.append({
                    "Filename": filename,
                    "Variable Name": var,
                    "Type": "DataFrame" if f"{filename}:{var}" in analyzer.all_entities["dataframes"] else "Regular"
                })
        
        df_vars = pd.DataFrame(var_data)
        st.dataframe(df_vars)
        
        # Show dataframes specifically
        st.subheader("DataFrames")
        df_data = []
        for df_key, df_info in analyzer.all_entities["dataframes"].items():
            filename, df_name = df_key.split(":", 1)
            df_data.append({
                "Filename": filename,
                "DataFrame": df_name,
                "Type": df_info['type'],
                "Source/Method": df_info.get('source', '') + ' / ' + df_info.get('method', '')
            })
        
        df_dataframes = pd.DataFrame(df_data)
        st.dataframe(df_dataframes)
    
    with tabs[2]:
        st.header("SQL Analysis")
        
        for i, query in enumerate(analyzer.all_entities["sql_queries"]):
            if query.strip():
                st.subheader(f"SQL Query {i+1}")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.code(query, language="sql")
                    
                    # Show tables used
                    sql_analysis = analyzer.parse_sql_tables_and_transformations(query)
                    if sql_analysis["tables"]:
                        st.write("Tables referenced:")
                        for table in sql_analysis["tables"]:
                            st.write(f"• {table}")
                
                with col2:
                    # Get LLM explanation of the SQL
                    explanation = gpt_summarize_logic(query, "sql")
                    st.write("**Business Explanation:**")
                    st.write(explanation)
    
    with tabs[3]:
        st.header("Data Transformations")
        
        for i, transform in enumerate(analyzer.all_entities["transformations"]):
            st.subheader(f"Transformation {i+1}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Source:** {transform.get('source')}")
                st.write(f"**Target:** {transform.get('target')}")
                st.write(f"**Operation:** {transform.get('operation')}")
                st.write(f"**In function:** {transform.get('in_function', 'N/A')}")
                st.code(transform.get('details', ''), language="python")
            
            with col2:
                # Get LLM explanation of the transformation
                explanation = gpt_summarize_logic(transform.get('details', ''), "transformation")
                st.write("**Business Explanation:**")
                st.write(explanation)
    
    with tabs[4]:
        st.header("Business Rules")
        
        for filename, entities in analyzer.script_mapping.items():
            if entities.get("business_rules"):
                st.subheader(f"Rules in {filename}")
                
                for i, rule in enumerate(entities["business_rules"]):
                    st.write(f"**Rule {i+1}:** {rule['type']}")
                    
                    if rule['type'] == 'condition':
                        st.code(f"IF {rule['condition']}:", language="python")
                        for action in rule['actions']:
                            st.code(f"  {action}", language="python")
                    else:
                        st.code(rule['full_call'], language="python")
                    
                    # Get LLM explanation of the rule
                    rule_text = rule.get('condition', rule.get('full_call', ''))
                    explanation = gpt_summarize_logic(rule_text, "business_rule")
                    st.write("**Business Explanation:**")
                    st.write(explanation)
    
    with tabs[5]:
        st.header("Data Flow Visualization")
        
        # Generate and display the data flow graph
        plt_fig = analyzer.visualize_data_flow()
        if plt_fig:
            st.pyplot(plt_fig.figure)
        
        # Display source-target mapping table
        st.subheader("Source-Target Mapping")
        df_mapping = pd.DataFrame(analyzer.all_entities["source_target_mapping"])
        st.dataframe(df_mapping)

    # Export section
    st.header("📥 Download Results")
    
    # Create export data
    export_data = {
        "Overview": pd.DataFrame({
            "Metric": ["Files", "Functions", "Variables", "File Paths", "SQL Queries", "Transformations"],
            "Count": [
                len(analyzer.script_mapping),
                len(analyzer.all_entities['functions']),
                len(analyzer.all_entities['variables']),
                len(analyzer.all_entities['file_paths']),
                len(analyzer.all_entities['sql_queries']),
                len(analyzer.all_entities['transformations'])
            ]
        }),
        "Variables": df_vars if 'df_vars' in locals() else pd.DataFrame(),
        "DataFrames": df_dataframes if 'df_dataframes' in locals() else pd.DataFrame(),
        "Transformations": pd.DataFrame(analyzer.all_entities["transformations"]),
        "Source_Target": pd.DataFrame(analyzer.all_entities["source_target_mapping"])
    }
    
    # Create SQL explanation sheet
    sql_explanations = []
    for i, query in enumerate(analyzer.all_entities["sql_queries"]):
        if query.strip():
            explanation = gpt_summarize_logic(query, "sql")
            sql_analysis = analyzer.parse_sql_tables_and_transformations(query)
            
            sql_explanations.append({
                "Query_ID": i+1,
                "SQL": query,
                "Tables": ", ".join(sql_analysis["tables"]),
                "Business_Explanation": explanation
            })
    
    export_data["SQL_Analysis"] = pd.DataFrame(sql_explanations)
    
    # Write to Excel
    with pd.ExcelWriter("enhanced_scanner_output.xlsx") as writer:
        for sheet_name, df in export_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    with open("enhanced_scanner_output.xlsx", "rb") as f:
        st.download_button("Download Excel Output", data=f, file_name="enhanced_scanner_output.xlsx")