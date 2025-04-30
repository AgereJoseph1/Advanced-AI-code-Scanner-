import streamlit as st
import zipfile
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from code_analyzer.analyzers.python_analyzer import PythonAnalyzer
from code_analyzer.llm_analyzer import LLMAnalyzer
import base64
import json
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="Deep Advanced AI Code Scanner",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS for better appearance
st.markdown("""
<style>
    /* Global styles */
    .main {
        padding: 2rem 3rem;
        background-color: #f9fafc;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #1e3a8a;
    }
    
    /* Header styles */
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        text-align: center;
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 1rem 0;
    }
    
    .main-subheader {
        font-size: 1.2rem;
        text-align: center;
        color: #64748b;
        margin-bottom: 2rem;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Card styles */
    .dashboard-card {
        background-color: white;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 30px;
        border: 1px solid #f1f5f9;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .dashboard-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    }
    
    .card-header {
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 1.2rem;
        color: #1e3a8a;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0.8rem;
    }
    
    /* Metric styles */
    .metrics-container {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        justify-content: space-between;
    }
    
    .metric-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        flex: 1;
        min-width: 200px;
        border: 1px solid #f1f5f9;
        text-align: center;
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1e3a8a;
        margin: 10px 0;
    }
    
    .metric-label {
        font-size: 1rem;
        text-align: center;
        color: #64748b;
        font-weight: 500;
    }
    
    .metric-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
        color: #3b82f6;
    }
    
    /* Issue styles */
    .issue-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border-left: 4px solid;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .issue-HIGH { border-left-color: #ef4444; }
    .issue-MEDIUM { border-left-color: #f59e0b; }
    .issue-LOW { border-left-color: #10b981; }
    
    /* Insight styles */
    .llm-insight-card {
        background-color: white;
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    
    .llm-insight-header {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 15px;
        color: #1e3a8a;
    }
    
    .llm-score {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #3b82f6;
        margin: 15px 0;
    }
    
    .llm-category {
        font-weight: 600;
        color: #1e3a8a;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    
    .llm-item {
        padding: 12px 16px;
        background-color: #f8fafc;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 3px solid #3b82f6;
    }
    
    .llm-summary {
        font-style: italic;
        padding: 15px;
        background-color: #f1f5f9;
        border-radius: 8px;
        margin-top: 20px;
        color: #334155;
        line-height: 1.6;
    }
    
    /* Lineage styles */
    .lineage-card {
        background-color: white;
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    
    /* Language badges */
    .language-badge {
        display: inline-block;
        padding: 8px 16px;
        background-color: #3b82f6;
        color: white;
        border-radius: 20px;
        margin: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
    }
    
    /* Transformation and API cards */
    .transformation-card {
        background-color: #f0fff4;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid #d1fae5;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .api-card {
        background-color: #fff1f2;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid #fee2e2;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .variable-card {
        background-color: #eff6ff;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid #dbeafe;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 8px 8px 0 0;
        border: 1px solid #e2e8f0;
        border-bottom: none;
        color: #64748b;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        border: none;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
        transition: all 0.2s;
    }
    
    .stButton>button:hover {
        background-color: #2563eb;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8fafc;
    }
    
    /* Progress bar */
    .stProgress .st-bo {
        background-color: #3b82f6;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1e3a8a;
    }
    
    /* Summary section */
    .summary-section {
        background-color: #f8fafc;
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        border: 1px solid #e2e8f0;
    }
    
    .summary-header {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 15px;
        color: #1e3a8a;
    }
    
    .summary-item {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)

def calculate_health_score(metrics):
    """Calculate an overall health score based on various metrics."""
    if not metrics:
        return 0
    
    # Simple formula for health score calculation
    documentation_score = metrics["documentation"]["docstring_coverage"]
    maintainability_score = metrics["maintainability"]["score"]
    
    # Weighted average
    health_score = (
        documentation_score * 0.3 + 
        maintainability_score * 0.7
    )
    
    return round(health_score, 1)

def create_metrics_chart(metrics):
    """Create a radar chart for code metrics visualization."""
    categories = [
        'Maintainability',
        'Documentation',
        'Code Clarity',
        'Structure'
    ]
    
    # Calculate values on a 0-100 scale
    values = [
        metrics["maintainability"]["score"],
        metrics["documentation"]["docstring_coverage"],
        max(0, 100 - metrics["maintainability"]["debt_ratio"]),
        max(0, 100 - metrics["maintainability"]["debt_ratio"])
    ]
    
    # Create radar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Code Quality'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False
    )
    
    return fig

def display_llm_analysis(llm_analysis):
    """
    Display the LLM analysis results in a structured format.
    """
    if "llm_analysis" not in llm_analysis:
        st.info("No LLM analysis available for this file.")
        return
    
    analysis = llm_analysis["llm_analysis"]
    
    # Display overall code summary
    st.markdown(f"""
    <div class="llm-insight-card">
        <div class="llm-insight-header">Code Overview</div>
        <div class="llm-summary">{analysis.get("summary", "No summary available.")}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display code architecture and purpose
    st.subheader("📐 Code Architecture & Purpose")
    
    # Create a more comprehensive view of the code's purpose and structure
    architecture_html = ""
    
    # Add main purpose
    if "purpose" in analysis:
        architecture_html += f"""
        <div class="lineage-card">
            <h3>Primary Purpose</h3>
            <p>{analysis.get("purpose", "No purpose information available.")}</p>
        </div>
        """
    
    # Add architectural patterns if available
    if "architecture" in analysis:
        architecture_html += f"""
        <div class="lineage-card">
            <h3>Architectural Patterns</h3>
            <p>{analysis.get("architecture", "No architectural information available.")}</p>
        </div>
        """
    
    # Add dependency information
    if "dependencies" in analysis:
        deps = analysis.get("dependencies", [])
        deps_html = "<ul>"
        for dep in deps:
            deps_html += f"<li><strong>{dep.get('name', 'Unknown')}</strong>: {dep.get('purpose', 'No purpose specified')}</li>"
        deps_html += "</ul>"
        
        architecture_html += f"""
        <div class="lineage-card">
            <h3>Key Dependencies</h3>
            {deps_html if deps else "<p>No dependencies identified.</p>"}
        </div>
        """
    
    # Display the architecture information
    if architecture_html:
        st.markdown(architecture_html, unsafe_allow_html=True)
    
    # Display functional components (functions and classes)
    st.subheader("🧩 Key Components")
    
    # Create columns for functions and classes
    col1, col2 = st.columns(2)
    
    with col1:
        # Functions overview
        functions = analysis.get("functions", [])
        if functions:
            functions_html = ""
            for func in functions:
                functions_html += f"""
                <div class="summary-item">
                    <h4>{func.get("name", "Unknown Function")}</h4>
                    <p>{func.get("purpose", "No purpose specified")}</p>
                </div>
                """
            
            st.markdown(f"""
            <div class="lineage-card">
                <h3>Key Functions</h3>
                {functions_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="lineage-card">
                <h3>Key Functions</h3>
                <p>No significant functions identified.</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Classes overview
        classes = analysis.get("classes", [])
        if classes:
            classes_html = ""
            for cls in classes:
                classes_html += f"""
                <div class="summary-item">
                    <h4>{cls.get("name", "Unknown Class")}</h4>
                    <p>{cls.get("purpose", "No purpose specified")}</p>
                </div>
                """
            
            st.markdown(f"""
            <div class="lineage-card">
                <h3>Key Classes</h3>
                {classes_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="lineage-card">
                <h3>Key Classes</h3>
                <p>No significant classes identified.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Display data flow and transformations
    if "data_flow" in analysis or "data_transformations" in analysis:
        st.subheader("📊 Data Flow & Transformations")
        
        # Data flow overview
        if "data_flow" in analysis:
            st.markdown(f"""
            <div class="lineage-card">
                <h3>Data Flow Overview</h3>
                <p>{analysis.get("data_flow", "No data flow information available.")}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Key transformations
        if "data_transformations" in analysis and analysis["data_transformations"]:
            transformations_html = ""
            for transform in analysis["data_transformations"]:
                transformations_html += f"""
                <div class="summary-item">
                    <h4>{transform.get("name", "Transformation")}</h4>
                    <p><strong>Description:</strong> {transform.get("description", "No description")}</p>
                    <p><strong>Input → Output:</strong> {transform.get("input", "Unknown")} → {transform.get("output", "Unknown")}</p>
                </div>
                """
            
            st.markdown(f"""
            <div class="lineage-card">
                <h3>Key Data Transformations</h3>
                {transformations_html}
            </div>
            """, unsafe_allow_html=True)
    
    # Display external interactions (APIs, databases, file systems)
    if "external_communications" in analysis:
        st.subheader("🔌 External Interactions")
        
        ext_comms = analysis["external_communications"]
        
        # Combine all external interactions into a single view
        interactions_html = ""
        
        # API communications
        if "apis" in ext_comms and ext_comms["apis"]:
            apis_html = "<ul>"
            for api in ext_comms["apis"]:
                apis_html += f"<li><strong>{api.get('name', 'Unknown API')}</strong>: {api.get('purpose', 'No purpose specified')}</li>"
            apis_html += "</ul>"
            
            interactions_html += f"""
            <div class="summary-item">
                <h4>API Integrations</h4>
                {apis_html}
            </div>
            """
        
        # Database operations
        if "databases" in ext_comms and ext_comms["databases"]:
            dbs_html = "<ul>"
            for db in ext_comms["databases"]:
                dbs_html += f"<li><strong>{db.get('name', 'Unknown Database')}</strong>: {', '.join(db.get('operations', ['Unknown operations']))}</li>"
            dbs_html += "</ul>"
            
            interactions_html += f"""
            <div class="summary-item">
                <h4>Database Interactions</h4>
                {dbs_html}
            </div>
            """
        
        # File operations
        if "file_operations" in ext_comms and ext_comms["file_operations"]:
            file_ops = ext_comms["file_operations"]
            if isinstance(file_ops, list):
                file_ops_html = "<ul>"
                for op in file_ops:
                    file_ops_html += f"<li>{op}</li>"
                file_ops_html += "</ul>"
                
                interactions_html += f"""
                <div class="summary-item">
                    <h4>File System Operations</h4>
                    {file_ops_html}
                </div>
                """
        
        # Display all interactions
        if interactions_html:
            st.markdown(f"""
            <div class="lineage-card">
                <h3>External System Interactions</h3>
                {interactions_html}
            </div>
            """, unsafe_allow_html=True)

def main():
    st.markdown("<h1 class='main-header'>Deep Advanced AI Code Scanner</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <p class='main-subheader'>
        A powerful AI-driven tool that analyzes codebases across multiple programming languages, 
        providing deep insights into code quality, architecture, and potential improvements.
    </p>
    """, unsafe_allow_html=True)
    
    # API Key for LLM analysis
    with st.sidebar:
        st.sidebar.markdown("### 🔑 API Configuration")
        api_key = st.text_input("OpenAI API Key (required for advanced analysis)", type="password")
        use_llm = st.checkbox("Enable AI-powered analysis", value=True if api_key else False)
        
        if use_llm and not api_key:
            st.warning("Please provide an OpenAI API key to use AI-powered analysis")
        
        # Analysis options
        st.markdown("### ⚙️ Analysis Options")
        analyze_variables = st.checkbox("Analyze variables and transformations", value=True)
        analyze_apis = st.checkbox("Detect external API communications", value=True)
        generate_lineage = st.checkbox("Generate project lineage", value=True)
        
        # Language options
        st.markdown("### 🌐 Languages")
        language_options = {
            "Python": ".py",
            "JavaScript": ".js",
            "TypeScript": ".ts",
            "Java": ".java",
            "C/C++": [".c", ".cpp", ".h", ".hpp"],
            "C#": ".cs",
            "Go": ".go",
            "Ruby": ".rb",
            "PHP": ".php",
            "HTML": ".html",
            "CSS": ".css",
            "SQL": ".sql",
            "Other": [".*"]
        }
        
        selected_languages = st.multiselect(
            "Select languages to analyze",
            options=list(language_options.keys()),
            default=list(language_options.keys())
        )
    
    # File uploader in a nice card
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'>📁 Upload Your Project</h2>", unsafe_allow_html=True)
    st.write("Upload a ZIP file containing your project to get a comprehensive analysis of your codebase.")
    uploaded_file = st.file_uploader("Choose a ZIP file", type="zip")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if uploaded_file:
        with st.spinner("Analyzing your code..."):
            try:
                # Process ZIP file
                zip_file = zipfile.ZipFile(uploaded_file)
                
                # Initialize analysis containers
                all_metrics = []
                all_issues = []
                all_llm_analyses = []
                file_count = 0
                total_lines = 0
                language_stats = {}
                
                # Get list of files to analyze based on selected languages
                selected_extensions = []
                for lang in selected_languages:
                    if lang in language_options:
                        if isinstance(language_options[lang], list):
                            selected_extensions.extend(language_options[lang])
                        else:
                            selected_extensions.append(language_options[lang])
                
                # If no languages are selected, analyze all files
                if not selected_extensions:
                    selected_extensions = [".*"]
                
                # Filter files based on extensions
                files_to_analyze = []
                file_contents = {}
                
                for file_info in zip_file.filelist:
                    if file_info.filename.endswith('/'):  # Skip directories
                        continue
                        
                    file_ext = os.path.splitext(file_info.filename)[1].lower()
                    
                    # Check if this file should be analyzed
                    should_analyze = False
                    for ext in selected_extensions:
                        if ext == ".*" or file_ext == ext:
                            should_analyze = True
                            break
                    
                    if should_analyze:
                        files_to_analyze.append(file_info)
                        try:
                            content = zip_file.read(file_info.filename).decode('utf-8', errors='ignore')
                            file_contents[file_info.filename] = content
                        except:
                            # Skip files that can't be decoded as text
                            pass
                
                # Initialize LLM analyzer if enabled
                llm_analyzer = None
                if use_llm and api_key:
                    llm_analyzer = LLMAnalyzer(api_key=api_key)
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Analyze each file
                for idx, file_info in enumerate(files_to_analyze, 1):
                    status_text.text(f"Analyzing {file_info.filename}...")
                    progress_bar.progress(idx / len(files_to_analyze))
                    
                    try:
                        # Skip if content wasn't loaded
                        if file_info.filename not in file_contents:
                            continue
                            
                        content = file_contents[file_info.filename]
                        file_ext = os.path.splitext(file_info.filename)[1].lower()
                        
                        # Set language based on file extension for basic detection
                        language = "unknown"
                        if file_ext == ".py":
                            language = "python"
                        elif file_ext == ".js":
                            language = "javascript"
                        elif file_ext == ".html":
                            language = "html"
                        elif file_ext == ".css":
                            language = "css"
                        elif file_ext == ".java":
                            language = "java"
                        elif file_ext == ".c" or file_ext == ".cpp" or file_ext == ".h":
                            language = "c/c++"
                        
                        # Update language stats
                        if language not in language_stats:
                            language_stats[language] = {
                                "files": 0,
                                "lines": 0
                            }
                        language_stats[language]["files"] += 1
                        
                        # Basic metrics analysis
                        metrics = {}
                        if language == "python":
                            analyzer = PythonAnalyzer(content, file_info.filename)
                            metrics = analyzer.analyze()
                            
                            # Calculate health score
                            metrics['health'] = calculate_health_score(metrics)
                            
                            # Update statistics
                            file_count += 1
                            total_lines += metrics["size"]["lines_total"]
                            language_stats[language]["lines"] += metrics["size"]["lines_total"]
                            
                            # Collect issues
                            file_issues = analyzer.detect_issues()
                            all_issues.extend(file_issues)
                        else:
                            # For non-Python files, create basic metrics
                            lines = content.count('\n') + 1
                            metrics = {
                                "file_info": {
                                    "path": file_info.filename,
                                    "name": os.path.basename(file_info.filename),
                                    "extension": file_ext,
                                    "language": language
                                },
                                "size": {
                                    "lines_total": lines,
                                    "lines_code": lines,
                                    "lines_comment": 0,
                                    "lines_blank": 0
                                },
                                "structure": {
                                    "functions": 0,
                                    "classes": 0,
                                    "imports": 0,
                                    "import_names": []
                                },
                                "maintainability": {
                                    "score": 50,
                                    "debt_ratio": 50
                                },
                                "health": 50  # Default health score
                            }
                            
                            # Update statistics
                            file_count += 1
                            total_lines += lines
                            language_stats[language]["lines"] += lines
                        
                        # Store metrics
                        all_metrics.append({
                            "file": file_info.filename,
                            "language": language,
                            "metrics": metrics
                        })
                        
                        # LLM analysis (if enabled)
                        if llm_analyzer and (idx % 5 == 0 or idx == len(files_to_analyze)):  # Analyze every 5th file to save API calls
                            status_text.text(f"Performing AI analysis on {file_info.filename}...")
                            llm_analysis = llm_analyzer.analyze_code(content, file_info.filename, language)
                            all_llm_analyses.append({
                                "file": file_info.filename,
                                "analysis": llm_analysis
                            })
                        
                    except Exception as e:
                        st.warning(f"Error analyzing {file_info.filename}: {str(e)}")
                
                # Generate project lineage if enabled
                project_lineage = None
                if generate_lineage and llm_analyzer and file_count > 0:
                    status_text.text("Generating project lineage...")
                    project_lineage = llm_analyzer.analyze_project_structure(
                        list(file_contents.keys()),
                        file_contents
                    )
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                if not all_metrics:
                    st.error("No files found to analyze in the ZIP archive.")
                    return
                
                # Display results
                st.header("📊 Code Structure Analysis")
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-label">Files Analyzed</div>
                        <div class="metric-value">{}</div>
                    </div>
                    """.format(file_count), unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-label">Total Lines</div>
                        <div class="metric-value">{:,}</div>
                    </div>
                    """.format(total_lines), unsafe_allow_html=True)
                
                with col3:
                    # Count total functions and classes
                    total_functions = sum(m["metrics"]["structure"].get("functions", 0) for m in all_metrics)
                    total_classes = sum(m["metrics"]["structure"].get("classes", 0) for m in all_metrics)
                    
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-label">Functions / Classes</div>
                        <div class="metric-value">{} / {}</div>
                    </div>
                    """.format(total_functions, total_classes), unsafe_allow_html=True)
                
                # File metrics table
                st.header("📁 Code Structure Details")
                
                file_df = pd.DataFrame([
                    {
                        "File": m["file"],
                        "Language": m.get("language", "unknown").capitalize(),
                        "Lines": m["metrics"]["size"]["lines_total"],
                        "Functions": m["metrics"]["structure"].get("functions", 0),
                        "Classes": m["metrics"]["structure"].get("classes", 0),
                    }
                    for m in all_metrics
                ])
                
                st.dataframe(file_df)
                
                # Visualize metrics for a selected file
                if all_metrics:
                    st.header("📈 Code Understanding")
                    
                    # Select a file to analyze in detail
                    selected_file = st.selectbox(
                        "Select a file to understand in detail",
                        options=[m["file"] for m in all_metrics]
                    )
                    
                    # Find the selected file metrics
                    selected_file_data = next((m for m in all_metrics if m["file"] == selected_file), None)
                    
                    if selected_file_data:
                        selected_metrics = selected_file_data["metrics"]
                        selected_language = selected_file_data.get("language", "unknown")
                        
                        # Display file information
                        st.subheader(f"File: {os.path.basename(selected_file)} ({selected_language.capitalize()})")
                        
                        # Display structure information
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"""
                            <div class="lineage-card">
                                <h3>Structure</h3>
                                <p><strong>Lines:</strong> {selected_metrics["size"]["lines_total"]}</p>
                                <p><strong>Functions:</strong> {selected_metrics["structure"].get("functions", 0)}</p>
                                <p><strong>Classes:</strong> {selected_metrics["structure"].get("classes", 0)}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            if "imports" in selected_metrics:
                                imports_list = "<ul>"
                                for imp in selected_metrics["imports"]:
                                    imports_list += f"<li>{imp}</li>"
                                imports_list += "</ul>"
                                
                                st.markdown(f"""
                                <div class="lineage-card">
                                    <h3>Dependencies</h3>
                                    {imports_list}
                                </div>
                                """, unsafe_allow_html=True)
                
                        # Display LLM analysis for the selected file if available
                        selected_llm_analysis = next((a["analysis"] for a in all_llm_analyses if a["file"] == selected_file), None)
                        
                        if selected_llm_analysis:
                            # Display the comprehensive LLM analysis
                            display_llm_analysis(selected_llm_analysis)
                        else:
                            st.info("No code understanding analysis available for this file. Select a different file or enable AI-powered analysis.")
                
                # Issues section
                if all_issues:
                    st.header("⚠️ Code Issues")
                    
                    # Filter issues by severity
                    severity_filter = st.selectbox(
                        "Filter by severity",
                        options=["All", "HIGH", "MEDIUM", "LOW"]
                    )
                    
                    filtered_issues = all_issues
                    if severity_filter != "All":
                        filtered_issues = [i for i in all_issues if i.severity.value == severity_filter]
                    
                    # Display issues
                    if filtered_issues:
                        for issue in filtered_issues:
                            st.markdown(f"""
                            <div class="issue-card issue-{issue.severity.value}">
                                <h4>{issue.category}: {issue.message}</h4>
                                <p><strong>File:</strong> {issue.file}</p>
                                <p><strong>Line:</strong> {issue.line}</p>
                                <p><strong>Recommendation:</strong> {issue.recommendation}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No issues found with the selected severity level.")
                
                # Export options
                st.header("📥 Export Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📊 Download Metrics (CSV)"):
                        csv = file_df.to_csv(index=False)
                        b64 = base64.b64encode(csv.encode()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="code_analysis_metrics.csv">Download CSV File</a>'
                        st.markdown(href, unsafe_allow_html=True)
                
                with col2:
                    if st.button("📋 Download Full Report (JSON)"):
                        # Prepare report data
                        report = {
                            "timestamp": datetime.now().isoformat(),
                            "project_summary": {
                                "file_count": file_count,
                                "total_lines": total_lines,
                                "language_stats": language_stats,
                                "issue_count": len(all_issues)
                            },
                            "file_metrics": [
                                {
                                    "file": m["file"],
                                    "language": m.get("language", "unknown"),
                                    "metrics": m["metrics"]
                                }
                                for m in all_metrics
                            ],
                            "issues": [
                                {
                                    "file": issue.file,
                                    "line": issue.line,
                                    "message": issue.message,
                                    "severity": issue.severity.value,
                                    "category": issue.category,
                                    "recommendation": issue.recommendation
                                }
                                for issue in all_issues
                            ]
                        }
                        
                        # Add project lineage if available
                        if project_lineage and "project_structure" in project_lineage:
                            report["project_lineage"] = project_lineage["project_structure"]
                        
                        # Add LLM analyses if available
                        if all_llm_analyses:
                            report["llm_analyses"] = [
                                {
                                    "file": a["file"],
                                    "analysis": a["analysis"]["llm_analysis"] if "llm_analysis" in a["analysis"] else {}
                                }
                                for a in all_llm_analyses
                            ]
                        
                        # Convert to JSON and create download link
                        json_str = json.dumps(report, indent=2)
                        b64 = base64.b64encode(json_str.encode()).decode()
                        href = f'<a href="data:file/json;base64,{b64}" download="deep_ai_code_analysis.json">Download JSON Report</a>'
                        st.markdown(href, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error analyzing code: {str(e)}")
                st.exception(e)

if __name__ == "__main__":
    main()