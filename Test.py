except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read as text
                    files_data.append({
                        "name": file_name,
                        "path": rel_path,
                        "extension": extension,
                        "language": language,
                        "size": file_size,
                        "is_binary": True,
                        "last_modified": last_modified
                    })
        
        # Update code stats
        code_stats["total_files"] = len(files_data)
        code_stats["total_functions"] = len(all_functions)
        code_stats["total_classes"] = len(all_classes)
        code_stats["total_variables"] = len(all_variables)
        code_stats["detected_databases"] = list(code_stats["detected_databases"])
        code_stats["detected_apis"] = list(code_stats["detected_apis"])
        code_stats["detected_frameworks"] = list(code_stats["detected_frameworks"])
        
        # Get top functions (most common names)
        function_counts = {}
        for func in all_functions:
            function_counts[func["name"]] = function_counts.get(func["name"], 0) + 1
        
        top_functions = sorted(function_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Get top classes (most common names)
        class_counts = {}
        for cls in all_classes:
            class_counts[cls["name"]] = class_counts.get(cls["name"], 0) + 1
        
        top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Analyze data flow
        data_flow = self.analyze_data_flow(files_data, all_functions, db_connections, api_usage)
        
        # Generate project summary with AI if API key is set
        project_summary = ""
        if self.openai_client:
            # Create summary information for AI analysis
            summary_data = {
                "languages": language_data,
                "file_count": code_stats["total_files"],
                "line_count": code_stats["total_lines"],
                "top_functions": top_functions[:10],
                "top_classes": top_classes[:10],
                "db_connections": list(code_stats["detected_databases"]),
                "frameworks": list(code_stats["detected_frameworks"]),
                "api_patterns": list(code_stats["detected_apis"])
            }
            
            prompt = OPENAI_PROMPTS["project_summary"].format(
                code_summary=json.dumps(summary_data, indent=2)
            )
            
            project_summary = self.analyze_code_with_openai(prompt)
        
        # Detect architecture patterns
        architecture_patterns = self.detect_architecture_patterns(
            files_data, all_classes, framework_usage, db_connections, api_usage
        )
        
        # Generate data flow diagram
        data_flow_image = self.generate_data_flow_image(data_flow)
        if data_flow_image:
            data_flow_image_b64 = base64.b64encode(data_flow_image.getvalue()).decode()
        else:
            data_flow_image_b64 = None
        
        def get_analysis_results():
            return {
                "files": files_data,
                "language_stats": language_data,
                "functions": all_functions,
                "classes": all_classes,
                "variables": all_variables,
                "db_connections": db_connections,
                "api_usage": api_usage,
                "framework_usage": framework_usage,
                "code_stats": code_stats,
                "top_functions": top_functions,
                "top_classes": top_classes,
                "project_summary": project_summary,
                "data_flow": data_flow,
                "data_flow_image": data_flow_image_b64,
                "architecture_patterns": architecture_patterns
            }
            
        return get_analysis_results()
    
    def detect_architecture_patterns(self, files_data, classes, framework_usage, db_connections, api_usage):
        """Detect common architecture patterns in the codebase"""
        patterns = []
        
        # Check for MVC pattern
        mvc_indicators = {
            "models": False, 
            "views": False, 
            "controllers": False
        }
        
        # Check for directory structure indicators
        for file in files_data:
            path_parts = file["path"].lower().split('/')
            if "model" in path_parts or "models" in path_parts:
                mvc_indicators["models"] = True
            elif "view" in path_parts or "views" in path_parts:
                mvc_indicators["views"] = True
            elif "controller" in path_parts or "controllers" in path_parts:
                mvc_indicators["controllers"] = True
        
        # Check for class names indicating patterns
        model_classes = [cls for cls in classes if "model" in cls["name"].lower()]
        view_classes = [cls for cls in classes if "view" in cls["name"].lower()]
        controller_classes = [cls for cls in classes if "controller" in cls["name"].lower()]
        
        if mvc_indicators["models"] and mvc_indicators["views"] and mvc_indicators["controllers"]:
            patterns.append({
                "name": "MVC Architecture",
                "confidence": "High",
                "evidence": "Directory structure contains models, views, and controllers"
            })
        elif len(model_classes) > 0 and len(view_classes) > 0 and len(controller_classes) > 0:
            patterns.append({
                "name": "MVC Architecture",
                "confidence": "Medium",
                "evidence": "Classes suggest Model-View-Controller pattern"
            })
        
        # Check for microservices architecture
        service_files = [f for f in files_data if "service" in f["path"].lower()]
        docker_files = [f for f in files_data if "dockerfile" in f["name"].lower() or "docker-compose" in f["name"].lower()]
        
        if len(docker_files) > 2 and len(service_files) > 3:
            patterns.append({
                "name": "Microservices Architecture",
                "confidence": "Medium",
                "evidence": f"Multiple Docker files ({len(docker_files)}) and service components ({len(service_files)})"
            })
        
        # Check for REST API architecture
        api_files = [f for f in files_data if "api" in f["path"].lower() or "endpoint" in f["path"].lower()]
        rest_api_usage = sum(1 for patterns in api_usage.values() if "REST API" in patterns)
        
        if rest_api_usage > 3 or len(api_files) > 3:
            patterns.append({
                "name": "REST API Architecture",
                "confidence": "High",
                "evidence": f"Multiple API endpoints and REST API usage detected"
            })
        
        # Check for event-driven architecture
        event_keywords = ["event", "listener", "subscriber", "publisher", "handler"]
        event_files = [f for f in files_data if any(kw in f["path"].lower() for kw in event_keywords)]
        message_queue_usage = sum(1 for patterns in api_usage.values() if "Message Queue" in patterns)
        
        if message_queue_usage > 1 or len(event_files) > 3:
            patterns.append({
                "name": "Event-driven Architecture",
                "confidence": "Medium",
                "evidence": f"Event-related components and message queue usage detected"
            })
        
        # Check for data pipeline/ETL architecture
        etl_keywords = ["etl", "pipeline", "transform", "processor"]
        etl_files = [f for f in files_data if any(kw in f["path"].lower() for kw in etl_keywords)]
        multiple_db_files = [file for file, dbs in db_connections.items() if len(dbs) > 1]
        
        if len(etl_files) > 1 or len(multiple_db_files) > 1:
            patterns.append({
                "name": "Data Pipeline/ETL Architecture",
                "confidence": "Medium",
                "evidence": f"ETL components and multiple database connections in same files"
            })
        
        # Check for client-server architecture
        frontend_frameworks = sum(1 for frameworks in framework_usage.values() 
                               if any(fw in ["React", "Angular", "Vue"] for fw in frameworks))
        backend_frameworks = sum(1 for frameworks in framework_usage.values() 
                               if any(fw in ["Django", "Flask", "Express", "Spring"] for fw in frameworks))
        
        if frontend_frameworks > 0 and backend_frameworks > 0:
            patterns.append({
                "name": "Client-Server Architecture",
                "confidence": "High",
                "evidence": f"Both frontend ({frontend_frameworks} files) and backend ({backend_frameworks} files) frameworks detected"
            })
        
        return patterns

def get_file_hash(content):
    """Generate a hash for a file's content"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def main():
    st.markdown('<h1 class="main-header">AI Code Scanner 🧠</h1>', unsafe_allow_html=True)
    st.markdown("""
    <p class="sub-header">Upload your legacy codebase to uncover insights, map data lineage, and understand project architecture.</p>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = None
    if 'scan_time' not in st.session_state:
        st.session_state.scan_time = None
    if 'last_file_hash' not in st.session_state:
        st.session_state.last_file_hash = None
    
    # API Key input (optional)
    with st.sidebar:
        st.title("Settings")
        
        # OpenAI API key input
        api_key = st.text_input("OpenAI API Key (Optional)", type="password", 
                               help="Provide your OpenAI API key to enable AI-powered analysis")
        
        st.markdown("---")
        st.subheader("About")
        st.markdown("""
        AI Code Scanner analyzes your codebase to provide insights about:
        - Code structure and organization
        - Data flow and lineage
        - Architecture patterns
        - Tech stack and frameworks
        - Database connections
        """)
        
        # Only show advanced options if we have results
        if st.session_state.scan_results:
            st.markdown("---")
            st.subheader("Advanced Analysis")
            
            if api_key:
                if st.button("Analyze Selected File with AI"):
                    # Implement file selection and analysis
                    st.info("File analysis feature coming soon!")
            else:
                st.warning("Add an OpenAI API key to enable advanced AI analysis")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File uploader
        uploaded_file = st.file_uploader("Upload your codebase (ZIP file)", type="zip")
        
        if uploaded_file:
            # Check if same file already scanned (avoid reprocessing)
            file_content = uploaded_file.getvalue()
            current_hash = hashlib.md5(file_content).hexdigest()
            
            if st.session_state.last_file_hash != current_hash:
                with st.spinner("Scanning your codebase... Please wait"):
                    # Create a temporary directory for analysis
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Reset the file pointer and analyze
                        uploaded_file.seek(0)
                        
                        analyzer = CodeAnalyzer(temp_dir)
                        start_time = time.time()
                        results = analyzer.analyze_codebase(uploaded_file, api_key)
                        end_time = time.time()
                        
                        if "error" in results:
                            st.error(results["error"])
                        else:
                            # Save results to session state
                            st.session_state.scan_results = results
                            st.session_state.scan_time = end_time - start_time
                            st.session_state.last_file_hash = current_hash
            
            else:
                st.info("Same file detected. Using cached results.")
    
    with col2:
        if uploaded_file:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**File:** {uploaded_file.name}")
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.markdown(f"**Size:** {file_size_mb:.2f} MB")
            
            if st.session_state.scan_time:
                st.markdown(f"**Scan Time:** {st.session_state.scan_time:.2f} seconds")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Display results if available
    if "scan_results" in st.session_state and st.session_state.scan_results:
        results = st.session_state.scan_results
        
        # Project Summary (AI-generated if available)
        st.header("Project Summary")
        
        if results.get("project_summary"):
            st.markdown(results["project_summary"])
        else:
            # Basic summary without AI
            st.markdown(f"""
            This codebase consists of **{results['code_stats']['total_files']} files** with 
            **{results['code_stats']['total_lines']:,} lines of code**. It contains 
            **{results['code_stats']['total_functions']} functions** and 
            **{results['code_stats']['total_classes']} classes**.
            
            The primary languages used are: {', '.join([f"**{lang}**" for lang, count 
                                                     in sorted(results['language_stats'].items(), 
                                                             key=lambda x: x[1], reverse=True)[:3]])}
            """)
            
            if results['code_stats']['detected_databases']:
                st.markdown(f"Database connections found: {', '.join(results['code_stats']['detected_databases'])}")
            
            if results['code_stats']['detected_frameworks']:
                st.markdown(f"Frameworks detected: {', '.join(results['code_stats']['detected_frameworks'][:5])}")
        
        # Key metrics
        st.header("Codebase Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{results["code_stats"]["total_files"]}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Files</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{results["code_stats"]["total_lines"]:,}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Lines of Code</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{results["code_stats"]["total_functions"]}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Functions</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{results["code_stats"]["total_classes"]}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Classes</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Architecture Patterns
        if results.get("architecture_patterns"):
            st.header("Architecture Patterns")
            
            for pattern in results["architecture_patterns"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{pattern['name']}**")
                    st.markdown(f"{pattern['evidence']}")
                with col2:
                    if pattern['confidence'] == 'High':
                        st.success(f"Confidence: {pattern['confidence']}")
                    elif pattern['confidence'] == 'Medium':
                        st.info(f"Confidence: {pattern['confidence']}")
                    else:
                        st.warning(f"Confidence: {pattern['confidence']}")
        
        # Data Flow
        st.header("Data Flow Analysis")
        
        # Display data flow diagram if available
        if results.get("data_flow_image"):
            st.image(base64.b64decode(results["data_flow_image"]), caption="Data Flow Diagram", use_column_width=True)
        
        # Database connections
        if results["db_connections"]:
            st.success(f"Found connections to {len(results['code_stats']['detected_databases'])} database types")
            
            # Count connections by database type
            db_counts = {}
            for _, db_types in results["db_connections"].items():
                for db_type in db_types:
                    db_counts[db_type] = db_counts.get(db_type, 0) + 1
            
            # Create bar chart
            db_df = pd.DataFrame({
                "Database": list(db_counts.keys()),
                "References": list(db_counts.values())
            }).sort_values("References", ascending=False)
            
            fig = px.bar(db_df, x="Database", y="References", color="Database", title="Database Connections")
            st.plotly_chart(fig, use_container_width=True)
            
            # Show files with database connections
            with st.expander("Files with Database Connections"):
                db_files = []
                for file_path, db_types in results["db_connections"].items():
                    db_files.append({
                        "File": file_path,
                        "Database Types": ", ".join(db_types)
                    })
                
                db_files_df = pd.DataFrame(db_files)
                st.dataframe(db_files_df, hide_index=True)
        else:
            st.info("No database connections detected in this codebase.")
        
        # External API Usage
        if results["api_usage"]:
            st.subheader("External API & Data Movement")
            
            # Count connections by API type
            api_counts = {}
            for _, api_types in results["api_usage"].items():
                for api_type in api_types:
                    api_counts[api_type] = api_counts.get(api_type, 0) + 1
            
            # Create bar chart
            api_df = pd.DataFrame({
                "API/Integration Type": list(api_counts.keys()),
                "References": list(api_counts.values())
            }).sort_values("References", ascending=False)
            
            fig = px.bar(api_df, x="API/Integration Type", y="References", color="API/Integration Type", 
                       title="API & Data Integration Types")
            st.plotly_chart(fig, use_container_width=True)
            
            # Show files with API usage
            with st.expander("Files with External APIs & Data Movement"):
                api_files = []
                for file_path, api_types in results["api_usage"].items():
                    api_files.append({
                        "File": file_path,
                        "API Types": ", ".join(api_types)
                    })
                
                api_files_df = pd.DataFrame(api_files)
                st.dataframe(api_files_df, hide_index=True)
        
        # ETL Candidates
        if results["data_flow"].get("etl_candidates"):
            st.subheader("Potential ETL/Data Pipeline Components")
            
            etl_df = pd.DataFrame(results["data_flow"]["etl_candidates"])
            etl_df.columns = ["File", "Database Types", "API Patterns"]
            etl_df["Database Types"] = etl_df["Database Types"].apply(lambda x: ", ".join(x))
            etl_df["API Patterns"] = etl_df["API Patterns"].apply(lambda x: ", ".join(x))
            
            st.dataframe(etl_df, hide_index=True)
        
        # Language distribution
        st.header("Technology Stack")
        st.subheader("Programming Languages")
        
        if results["language_stats"]:
            lang_df = pd.DataFrame({
                "Language": list(results["language_stats"].keys()),
                "Files": list(results["language_stats"].values())
            }).sort_values("Files", ascending=False)
            
            # Only show top 10 languages in chart
            if len(lang_df) > 10:
                chart_df = lang_df.head(10).copy()
                other_count = lang_df.iloc[10:]["Files"].sum()
                other_df = pd.DataFrame({"Language": ["Other"], "Files": [other_count]})
                chart_df = pd.concat([chart_df, other_df], ignore_index=True)
            else:
                chart_df = lang_df
            
            # Create pie chart
            fig = px.pie(chart_df, values="Files", names="Language", title="Language Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Show full language table
            st.dataframe(lang_df, hide_index=True)
        
        # Frameworks used
        if results["framework_usage"]:
            st.subheader("Frameworks & Libraries")
            
            # Count frameworks
            framework_counts = {}
            for _, frameworks in results["framework_usage"].items():
                for framework in frameworks:
                    framework_counts[framework] = framework_counts.get(framework, 0) + 1
            
            # Create bar chart for top frameworks
            framework_df = pd.DataFrame({
                "Framework": list(framework_counts.keys()),
                "References": list(framework_counts.values())
            }).sort_values("References", ascending=False)
            
            top_frameworks = framework_df.head(15)
            
            fig = px.bar(top_frameworks, x="Framework", y="References", color="Framework", 
                       title="Top Frameworks & Libraries")
            st.plotly_chart(fig, use_container_width=True)
        
        # Create tabs for different views
        tabs = st.tabs(["Functions", "Classes", "Files", "Export"])
        
        # Functions tab
        with tabs[0]:
            st.header("Function Analysis")
            
            # Top function names
            st.subheader("Most Common Functions")
            
            if results["top_functions"]:
                func_df = pd.DataFrame({
                    "Function Name": [f[0] for f in results["top_functions"]],
                    "Occurrences": [f[1] for f in results["top_functions"]]
                })
                
                fig = px.bar(func_df, x="Function Name", y="Occurrences", color="Function Name",
                            title="Top Functions by Frequency")
                st.plotly_chart(fig, use_container_width=True)
            
            # Function search
            st.subheader("Search Functions")
            
            if results["functions"]:
                search_term = st.text_input("Search for function names", key="function_search")
                
                if search_term:
                    filtered_functions = [f for f in results["functions"] if search_term.lower() in f["name"].lower()]
                    
                    if filtered_functions:
                        func_df = pd.DataFrame([{
                            "Name": f["name"],
                            "Language": f["language"],
                            "File": f["file"],
                            "Is Method": f.get("is_method", False),
                            "Class": f.get("class", ""),
                            "Parameters": ", ".join(f.get("parameters", [])) if f.get("parameters") else ""
                        } for f in filtered_functions])
                        
                        st.dataframe(func_df, hide_index=True)
                    else:
                        st.info(f"No functions matching '{search_term}'")
                else:
                    # Show total counts by language
                    func_by_lang = {}
                    for func in results["functions"]:
                        lang = func["language"]
                        func_by_lang[lang] = func_by_lang.get(lang, 0) + 1
                    
                    func_lang_df = pd.DataFrame({
                        "Language": list(func_by_lang.keys()),
                        "Function Count": list(func_by_lang.values())
                    }).sort_values("Function Count", ascending=False)
                    
                    st.dataframe(func_lang_df, hide_index=True)
            else:
                st.info("No functions detected in codebase")
        
        # Classes tab
        with tabs[1]:
            st.header("Class Analysis")
            
            # Top class names
            st.subheader("Most Common Classes")
            
            if results["top_classes"]:
                class_df = pd.DataFrame({
                    "Class Name": [c[0] for c in results["top_classes"]],
                    "Occurrences": [c[1] for c in results["top_classes"]]
                })
                
                fig = px.bar(class_df, x="Class Name", y="Occurrences", color="Class Name",
                            title="Top Classes by Frequency")
                st.plotly_chart(fig, use_container_width=True)
            
            # Class search
            st.subheader("Search Classes")
            
            if results["classes"]:
                search_term = st.text_input("Search for class names", key="class_search")
                
                if search_term:
                    filtered_classes = [c for c in results["classes"] if search_term.lower() in c["name"].lower()]
                    
                    if filtered_classes:
                        class_df = pd.DataFrame([{
                            "Name": c["name"],
                            "Language": c["language"],
                            "File": c["file"],
                            "Parent/Base": c.get("parent", c.get("bases", [])[0] if c.get("bases") else ""),
                            "Methods": ", ".join(c.get("methods", []))[:100] if c.get("methods") else ""
                        } for c in filtered_classes])
                        
                        st.dataframe(class_df, hide_index=True)
                    else:
                        st.info(f"No classes matching '{search_term}'")
                else:
                    # Show total counts by language
                    class_by_lang = {}
                    for cls in results["classes"]:
                        lang = cls["language"]
                        class_by_lang[lang] = class_by_lang.get(lang, 0) + 1
                    
                    class_lang_df = pd.DataFrame({
                        "Language": list(class_by_lang.keys()),
                        "Class Count": list(class_by_lang.values())
                    }).sort_values("Class Count", ascending=False)
                    
                    st.dataframe(class_lang_df, hide_index=True)
            else:
                st.info("No classes detected in codebase")
        
        # Files tab
        with tabs[2]:
            st.header("File Analysis")
            
            # File search
            st.subheader("Search Files")
            
            search_term = st.text_input("Search for file names or paths", key="file_search")
            
            # Prepare dataframe
            files_df = pd.DataFrame([{
                "Name": f["name"],
                "Path": f["path"],
                "Language": f["language"],
                "Size (KB)": round(f["size"] / 1024, 2),
                "Lines": f.get("lines", "N/A"),
                "Functions": f.get("functions", 0),
                "Classes": f.get("classes", 0),
                "Has DB Connection": f.get("has_db_connection", False),
                "Frameworks": ", ".join(f.get("frameworks", []))
            } for f in results["files"]])
            
            if search_term:
                filtered_files = files_df[
                    files_df["Name"].str.contains(search_term, case=False) |
                    files_df["Path"].str.contains(search_term, case=False)
                ]
                
                if not filtered_files.empty:
                    st.dataframe(filtered_files, hide_index=True)
                else:
                    st.info(f"No files matching '{search_term}'")
            else:
                # Show file extension breakdown
                ext_counts = {}
                for file in results["files"]:
                    ext = file["extension"] if file["extension"] else "no extension"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                
                ext_df = pd.DataFrame({
                    "Extension": list(ext_counts.keys()),
                    "Count": list(ext_counts.values())
                }).sort_values("Count", ascending=False)
                
                st.subheader("File Extensions")
                fig = px.bar(ext_df.head(15), x="Extension", y="Count", color="Extension",
                           title="Top File Extensions")
                st.plotly_chart(fig, use_container_width=True)
                
                # Show all files
                st.subheader("All Files")
                st.dataframe(files_df, hide_index=True)
        
        # Export tab
        with tabs[3]:
            st.header("Export Options")
            
            # Export as JSON
            if st.button("Export Full Analysis as JSON"):
                # Convert results for JSON export
                export_data = results.copy()
                
                # Remove binary data for JSON export
                if "data_flow_image" in export_data:
                    del export_data["data_flow_image"]
                
                # Convert datetime objects to strings
                for file in export_data["files"]:
                    if "last_modified" in file:
                        file["last_modified"] = file["last_modified"].isoformat()
                
                # Create JSON string
                json_str = json.dumps(export_data, indent=2)
                
                # Create download link
                b64 = base64.b64encode(json_str.encode()).decode()
                href = f'<a href="data:application/json;base64,{b64}" download="codebase_analysis.json">Download JSON File</a>'
                st.markdown(href, unsafe_allow_html=True)
            
            # Export as CSV
            export_type = st.selectbox("Export specific data as CSV", 
                                     ["Functions", "Classes", "Files with DB Connections", "All Files", "Data Lineage"])
            
            if st.button(f"Export {export_type} as CSV"):
                if export_type == "Functions":
                    # Export functions
                    export_df = pd.DataFrame([{
                        "Name": f["name"],
                        "Language": f["language"],
                        "File": f["file"],
                        "Is Method": f.get("is_method", False),
                        "Class": f.get("class", ""),
                        "Parameters": ", ".join(f.get("parameters", [])) if f.get("parameters") else ""
                    } for f in results["functions"]])
                    
                    file_name = "functions.csv"
                
                elif export_type == "Classes":
                    # Export classes
                    export_df = pd.DataFrame([{
                        "Name": c["name"],
                        "Language": c["language"],
                        "File": c["file"],
                        "Parent/Base": c.get("parent", c.get("bases", [])[0] if c.get("bases") else ""),
                        "Methods": ", ".join(c.get("methods", []))[:100] if c.get("methods") else ""
                    } for c in results["classes"]])
                    
                    file_name = "classes.csv"
                
                elif export_type == "Files with DB Connections":
                    # Export files with DB connections
                    db_files = []
                    for file_path, db_types in results["db_connections"].items():
                        db_files.append({
                            "File": file_path,
                            "Database Types": ", ".join(db_types)
                        })
                    
                    export_df = pd.DataFrame(db_files)
                    file_name = "db_connections.csv"
                
                elif export_type == "Data Lineage":
                    # Export data lineage information
                    lineage_records = []
                    
                    # Extract from data flow graph
                    for edge in results["data_flow"]["graph"]["edges"]:
                        if "DB:" in edge["source"] or "DB:" in edge["target"]:
                            source = edge["source"].replace("DB:", "") if "DB:" in edge["source"] else edge["source"]
                            target = edge["target"].replace("DB:", "") if "DB:" in edge["target"] else edge["target"]
                            
                            lineage_records.append({
                                "Source": source,
                                "Target": target,
                                "Relationship": edge["type"],
                                "Type": "Database Connection"
                            })
                    
                    # Add ETL candidates
                    for etl in results["data_flow"].get("etl_candidates", []):
                        lineage_records.append({
                            "Source": etl["file"],
                            "Target": ", ".join(etl["db_types"]),
                            "Relationship": "ETL Process",
                            "Type": "Data Pipeline"
                        })
                    
                    export_df = pd.DataFrame(lineage_records)
                    file_name = "data_lineage.csv"
                
                else:  # All Files
                    # Export all files
                    export_df = pd.DataFrame([{
                        "Name": f["name"],
                        "Path": f["path"],
                        "Language": f["language"],
                        "Size (KB)": round(f["size"] / 1024, 2),
                        "Lines": f.get("lines", "N/A"),
                        "Functions": f.get("functions", 0),
                        "Classes": f.get("classes", 0),
                        "Has DB Connection": f.get("has_db_connection", False),
                        "DB Types": ", ".join(f.get("db_types", [])),
                        "Frameworks": ", ".join(f.get("frameworks", []))
                    } for f in results["files"]])
                    
                    file_name = "all_files.csv"
                
                # Convert to CSV
                csv = export_df.to_csv(index=False)
                
                # Create download link
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:text/csv;base64,{b64}" download="{file_name}">Download CSV File</a>'
                st.markdown(href, unsafe_allow_html=True)
            
            # Generate comprehensive report
            if st.button("Generate Comprehensive Report"):
                # Create markdown report
                report = f"""
                # AI Code Scanner - Codebase Analysis Report
                
                ## Project Summary
                {results.get("project_summary", f"""
                This codebase consists of {results['code_stats']['total_files']} files with 
                {results['code_stats']['total_lines']:,} lines of code. It contains 
                {results['code_stats']['total_functions']} functions and 
                {results['code_stats']['total_classes']} classes.
                
                The primary languages used are: {', '.join([f"{lang}" for lang, count 
                                                         in sorted(results['language_stats'].items(), 
                                                                 key=lambda x: x[1], reverse=True)[:3]])}
                """)}
                
                ## Architecture Patterns
                {chr(10).join([f"- **{pattern['name']}** (Confidence: {pattern['confidence']}): {pattern['evidence']}" 
                             for pattern in results.get("architecture_patterns", [])]) or "No specific architecture patterns detected."}
                
                ## Technology Stack
                
                ### Programming Languages
                {chr(10).join([f"- **{lang}:** {count} files" for lang, count in sorted(results["language_stats"].items(), key=lambda x: x[1], reverse=True)])}
                
                ### Frameworks & Libraries
                {chr(10).join([f"- **{framework}**" for framework in results["code_stats"]["detected_frameworks"]]) if results["code_stats"]["detected_frameworks"] else "No frameworks detected."}
                
                ## Database Connections
                {chr(10).join([f"- **{db}**" for db in results["code_stats"]["detected_databases"]]) if results["code_stats"]["detected_databases"] else "No database connections detected."}
                
                ## External APIs & Data Movement
                {chr(10).join([f"- **{api}**" for api in results["code_stats"]["detected_apis"]]) if results["code_stats"]["detected_apis"] else "No external API usage detected."}
                
                ## Data Lineage
                {chr(10).join([f"- **{etl['file']}**: Connects {', '.join(etl['db_types'])} using {', '.join(etl['api_patterns'])}" 
                             for etl in results["data_flow"].get("etl_candidates", [])]) if results["data_flow"].get("etl_candidates") else "No clear data lineage paths identified."}
                
                ## Most Common Functions
                {chr(10).join([f"- **{func[0]}:** {func[1]} occurrences" for func in results["top_functions"][:10]]) if results["top_functions"] else "No functions detected."}
                
                ## Most Common Classes
                {chr(10).join([f"- **{cls[0]}:** {cls[1]} occurrences" for cls in results["top_classes"][:10]]) if results["top_classes"] else "No classes detected."}
                
                ## Files with Database Connections
                {chr(10).join([f"- **{file_path}:** {', '.join(db_types)}" for file_path, db_types in list(results["db_connections"].items())[:20]]) if results["db_connections"] else "No database connections detected."}
                
                ## Key Metrics
                - **Total Files:** {results["code_stats"]["total_files"]}
                - **Total Lines of Code:** {results["code_stats"]["total_lines"]:,}
                - **Functions:** {results["code_stats"]["total_functions"]}
                - **Classes:** {results["code_stats"]["total_classes"]}
                - **Variables:** {results["code_stats"]["total_variables"]}
                
                ---
                
                *Report generated by AI Code Scanner*
                """
                
                # Create download link
                b64 = base64.b64encode(report.encode()).decode()
                href = f'<a href="data:text/markdown;base64,{b64}" download="codebase_report.md">Download Markdown Report</a>'
                st.markdown(href, unsafe_allow_html=True)
                
                # Also display the report
                with st.expander("Preview Report"):
                    st.markdown(report)

if __name__ == "__main__":
    main()

import streamlit as st
import zipfile
import os
import tempfile
from pathlib import Path
import re
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
import base64
import networkx as nx
import matplotlib.pyplot as plt
import openai
from io import BytesIO
import numpy as np
from PIL import Image
import nbformat
from nbconvert import PythonExporter
import ast
import time
from collections import defaultdict
import hashlib

# Set page configuration
st.set_page_config(
    page_title="AI Code Scanner",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4A90E2;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #6C757D;
        margin-bottom: 1rem;
    }
    .card {
        padding: 1rem;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .card-header {
        font-weight: bold;
        color: #4A90E2;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #F8F9FA;
        padding: 1rem;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4A90E2;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6C757D;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #FFF3CD;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Language detection mapping
LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".ipynb": "Python (Notebook)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".html": "HTML",
    ".css": "CSS",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".sql": "SQL",
    ".xml": "XML",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".md": "Markdown",
    ".r": "R",
    ".scala": "Scala",
    ".kt": "Kotlin",
    ".rs": "Rust",
    ".dart": "Dart",
    ".lua": "Lua",
    ".pl": "Perl",
    ".sh": "Shell",
    ".bash": "Bash",
    ".ps1": "PowerShell",
    ".groovy": "Groovy",
    ".vue": "Vue",
    ".svelte": "Svelte"
}

# Database connection patterns - expanded
DB_PATTERNS = {
    "MySQL": [
        r'mysql\.connector', r'pymysql', r'MySQLdb', r'jdbc:mysql', 
        r'createConnection\s*\(\s*["\']mysql', r'mysql\s*://', r'new\s+MySQL'
    ],
    "PostgreSQL": [
        r'psycopg2', r'pg8000', r'postgresql://', r'postgres://', r'jdbc:postgresql', 
        r'new\s+PostgreSQL', r'Pool\s*\(\s*["\']postgres'
    ],
    "SQLite": [
        r'sqlite3', r'\.db', r'\.sqlite', r'jdbc:sqlite', r'createConnection\s*\(\s*["\']sqlite'
    ],
    "MongoDB": [
        r'pymongo', r'mongodb://', r'MongoClient', r'mongoose', r'mongodb\+srv', 
        r'new\s+Mongo', r'connect\s*\(\s*["\']mongodb'
    ],
    "Oracle": [
        r'cx_Oracle', r'oracle', r'jdbc:oracle', r'oracledb', r'OracleConnection'
    ],
    "SQL Server": [
        r'pyodbc', r'sqlserver', r'mssql', r'jdbc:sqlserver', r'new\s+SqlConnection', 
        r'data source=.*server', r'Server=.*Database', r'Data Source=.*Initial Catalog'
    ],
    "Redis": [
        r'redis', r'Redis\(', r'createClient\s*\(\s*["\']redis', r'redis://'
    ],
    "Firestore/Firebase": [
        r'firebase', r'firestore', r'initializeApp', r'FirebaseFirestore', 
        r'collection\s*\(', r'getFirestore'
    ],
    "DynamoDB": [
        r'dynamodb', r'DynamoDBClient', r'DocumentClient', r'new\s+AWS\.DynamoDB'
    ],
    "Cassandra": [
        r'cassandra', r'datastax', r'Cluster\s*\(', r'cqlengine', 
        r'cassandra-driver', r'CassandraClient'
    ],
    "Elasticsearch": [
        r'elasticsearch', r'elastic', r'Elasticsearch\s*\(', r'createClient\s*\(\s*\{\s*node'
    ],
    "Neo4j": [
        r'neo4j', r'GraphDatabase', r'bolt://', r'neo4j://', r'Driver\s*\('
    ],
    "Snowflake": [
        r'snowflake', r'SnowflakeConnection', r'snowflake-connector', r'snowflake://'
    ],
    "BigQuery": [
        r'bigquery', r'BigQuery', r'google\.cloud\.bigquery', r'bigquery\.Client'
    ],
    "Redshift": [
        r'redshift', r'redshift_connector', r'jdbc:redshift', r'redshift://'
    ]
}

# External API and data movement patterns
API_PATTERNS = {
    "REST API": [
        r'\.get\(\s*["\']https?://', r'\.post\(\s*["\']https?://', r'fetch\(\s*["\']https?://',
        r'axios', r'requests\.', r'http\.', r'HttpClient', r'new\s+Http', r'new\s+XMLHttpRequest',
        r'RestTemplate', r'WebClient', r'OkHttp', r'Retrofit'
    ],
    "GraphQL": [
        r'graphql', r'ApolloClient', r'gql\s*`', r'useQuery', r'useMutation', 
        r'GraphQLClient', r'execute\s*\(\s*[\w\s]*\{', r'execute\s*\(\s*gql'
    ],
    "gRPC": [
        r'grpc', r'protobuf', r'ServiceClient', r'createClient\s*\(\s*[\'\"]grpc', 
        r'\.proto', r'ServerBuilder'
    ],
    "WebSocket": [
        r'websocket', r'new\s+WebSocket', r'\.on\(\s*["\']message', r'\.on\(\s*["\']open',
        r'socket\.io', r'socketio', r'ws://', r'wss://'
    ],
    "Message Queue": [
        r'rabbitmq', r'kafka', r'activemq', r'pubsub', r'SQS', r'kinesis', 
        r'EventHub', r'ServiceBus', r'JMS', r'MQTT', r'Producer', r'Consumer', 
        r'publish\s*\(', r'subscribe\s*\(', r'amqp', r'message_broker'
    ],
    "ETL Process": [
        r'airflow', r'luigi', r'nifi', r'talend', r'informatica', r'pentaho', 
        r'spark', r'databricks', r'dbt', r'extract_transform_load', 
        r'etl', r'data\s+pipeline', r'pipeline'
    ],
    "File System": [
        r'open\s*\(\s*[\'\"][^\'\"]+\.', r'readFile', r'writeFile', r'readdir', 
        r'fs\.', r'filesystem', r'storage\.', r'blob', r'S3', r'uploadFile', 
        r'downloadFile', r'copyFile'
    ],
    "Cloud Storage": [
        r'S3', r'Blob', r'GCS', r'Azure\s*Storage', r'StorageClient', r'CloudStorage', 
        r'uploadToS3', r'downloadFromS3', r'bucket', r'container\.', r'putObject', 
        r'getObject'
    ]
}

# Framework patterns
FRAMEWORK_PATTERNS = {
    "Web Framework": {
        "Django": [r'django', r'urls\.py', r'models\.py', r'views\.py', r'from\s+django', r'@admin\.register'],
        "Flask": [r'flask', r'Flask\s*\(', r'from\s+flask', r'@app\.route', r'Blueprint\s*\('],
        "FastAPI": [r'fastapi', r'FastAPI\s*\(', r'from\s+fastapi', r'@app\.get', r'@app\.post'],
        "Express": [r'express', r'app\s*=\s*express\s*\(\)', r'router\s*=\s*express\.Router', r'app\.use\s*\(', r'app\.get\s*\('],
        "React": [r'react', r'React', r'ReactDOM', r'useState', r'useEffect', r'import\s+React', r'extends\s+Component', r'<\w+\s+.*\/>'],
        "Angular": [r'@angular', r'NgModule', r'Component\s*\(\s*\{', r'Injectable', r'import\s+\{\s*.*\s*\}\s+from\s+[\'"]@angular'],
        "Vue": [r'vue', r'Vue\s*\(', r'createApp', r'new\s+Vue', r'<template>', r'v-for', r'v-if'],
        "Spring": [r'@RestController', r'@Service', r'@Repository', r'@Autowired', r'@SpringBootApplication', r'SpringApplication\.run'],
        "Rails": [r'ActiveRecord', r'Rails', r'ApplicationController', r'has\_many', r'belongs\_to', r'validates']
    },
    "Data Science": {
        "Pandas": [r'pandas', r'pd\.DataFrame', r'pd\.read_csv', r'pd\.Series', r'pd\.concat'],
        "NumPy": [r'numpy', r'np\.array', r'np\.zeros', r'np\.ones', r'np\.random'],
        "SciPy": [r'scipy', r'scipy\.', r'from\s+scipy'],
        "Matplotlib": [r'matplotlib', r'plt\.', r'pyplot'],
        "Seaborn": [r'seaborn', r'sns\.', r'import\s+seaborn'],
        "Scikit-learn": [r'sklearn', r'from\s+sklearn', r'train_test_split', r'RandomForest', r'LogisticRegression'],
        "TensorFlow": [r'tensorflow', r'tf\.', r'keras', r'Sequential\s*\(', r'Model\s*\(', r'tf\.data'],
        "PyTorch": [r'torch', r'nn\.Module', r'torch\.', r'optim\.', r'DataLoader', r'from\s+torch'],
        "Dask": [r'dask', r'from\s+dask', r'dask\.dataframe', r'dask\.array'],
        "Spark": [r'pyspark', r'SparkContext', r'SparkSession', r'spark\.', r'RDD', r'createDataFrame']
    },
    "Mobile": {
        "React Native": [r'react-native', r'from\s+react-native', r'ReactNative', r'StyleSheet\.create'],
        "Flutter": [r'flutter', r'StatelessWidget', r'StatefulWidget', r'Widget\s+build', r'MaterialApp'],
        "Android": [r'androidx', r'android\.', r'Activity', r'Fragment', r'Intent', r'setContentView'],
        "iOS": [r'UIKit', r'SwiftUI', r'UIViewController', r'AppDelegate', r'@IBOutlet', r'@IBAction']
    },
    "DevOps": {
        "Docker": [r'Dockerfile', r'docker-compose', r'FROM\s+\w+', r'ENTRYPOINT', r'CMD', r'EXPOSE'],
        "Kubernetes": [r'kubectl', r'apiVersion:', r'kind:', r'metadata:', r'Deployment', r'Service', r'Pod'],
        "Terraform": [r'terraform', r'provider\s+["\']', r'resource\s+["\']', r'module\s+["\']', r'aws_', r'azure_', r'google_'],
        "Ansible": [r'ansible', r'playbook', r'tasks:', r'hosts:', r'become:', r'with_items:'],
        "Jenkins": [r'Jenkinsfile', r'pipeline\s*\{', r'stage\s*\(', r'steps\s*\{', r'agent']
    }
}

# Configuration templates for OpenAI API
OPENAI_PROMPTS = {
    "project_summary": """
You are an expert code analyst. I'll provide you with a summary of a codebase, and your task is to:
1. Identify the main purpose of the project
2. Summarize the architecture and key components
3. Highlight potential areas of interest or concern
4. Provide a high-level overview appropriate for technical stakeholders

Here's the codebase summary:
{code_summary}

Please provide a concise, informative analysis.
""",
    "code_explanation": """
You are an expert developer tasked with explaining complex code. I'll provide a code snippet, and your task is to:
1. Explain what this code does in simple terms
2. Identify key functions, variables and their purpose
3. Note any potential issues, bugs, or security concerns
4. Suggest any potential improvements

Here's the code:
```{language}
{code}
```

Please provide your expert analysis.
""",
    "data_flow_analysis": """
You are an expert in data engineering and system architecture. Analyze this information about data flows and database connections in a codebase:

{data_flow_info}

Please:
1. Describe the overall data architecture
2. Identify the data sources and sinks
3. Map the flow of data through the system
4. Highlight any potential data security or integrity issues
5. Suggest improvements to the data flow architecture

Provide a comprehensive analysis focused on data lineage.
"""
}

class CodeAnalyzer:
    """Class for analyzing code and extracting information"""
    
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        self.api_key = None
        self.openai_client = None
    
    def set_api_key(self, api_key):
        """Set up OpenAI client with provided API key"""
        if api_key:
            self.api_key = api_key
            try:
                openai.api_key = api_key
                self.openai_client = openai
                return True
            except Exception as e:
                st.error(f"Error setting up OpenAI client: {e}")
                return False
        return False
    
    def analyze_code_with_openai(self, prompt, model="gpt-4-turbo"):
        """Analyze code using OpenAI API"""
        if not self.openai_client:
            return "OpenAI API key not configured"
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "You are an expert code analyzer assistant."},
                          {"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing code with OpenAI: {e}"
    
    def extract_python_imports(self, content):
        """Extract imports from Python code"""
        imports = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append({"module": name.name, "alias": name.asname})
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        imports.append({
                            "module": f"{module}.{name.name}" if module else name.name,
                            "from": module,
                            "import": name.name,
                            "alias": name.asname
                        })
        except Exception:
            # If parsing fails, try regex as fallback
            import_patterns = [
                r'import\s+([\w\.]+)(?:\s+as\s+([\w]+))?',
                r'from\s+([\w\.]+)\s+import\s+([\w\.\*]+)(?:\s+as\s+([\w]+))?'
            ]
            
            for pattern in import_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    if match.group(0).startswith('from'):
                        imports.append({
                            "from": match.group(1),
                            "import": match.group(2),
                            "alias": match.group(3) if len(match.groups()) > 2 else None
                        })
                    else:
                        imports.append({
                            "module": match.group(1),
                            "alias": match.group(2) if len(match.groups()) > 1 else None
                        })
                        
        return imports
    
    def extract_javascript_imports(self, content):
        """Extract imports from JavaScript/TypeScript code"""
        imports = []
        
        # ES6 import patterns
        import_patterns = [
            r'import\s+\{\s*([\w\s,]+)\s*\}\s+from\s+[\'"]([^\'"]+)[\'"]',  # import { x, y } from 'module'
            r'import\s+([\w]+)\s+from\s+[\'"]([^\'"]+)[\'"]',  # import x from 'module'
            r'import\s+\*\s+as\s+([\w]+)\s+from\s+[\'"]([^\'"]+)[\'"]',  # import * as x from 'module'
            r'import\s+[\'"]([^\'"]+)[\'"]'  # import 'module'
        ]
        
        # CommonJS require pattern
        require_pattern = r'(?:const|let|var)\s+([\w\{\}\s,]+)\s*=\s*require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if '{' in match.group(0):
                    # Extract individual imports from destructuring pattern
                    modules = [m.strip() for m in match.group(1).split(',')]
                    source = match.group(2)
                    for module in modules:
                        if ' as ' in module:
                            orig, alias = module.split(' as ')
                            imports.append({
                                "import": orig.strip(),
                                "source": source,
                                "alias": alias.strip()
                            })
                        else:
                            imports.append({
                                "import": module.strip(),
                                "source": source
                            })
                elif '*' in match.group(0):
                    # Import * as x from 'y'
                    imports.append({
                        "import": "*",
                        "source": match.group(2),
                        "alias": match.group(1)
                    })
                elif 'from' in match.group(0):
                    # Standard import
                    imports.append({
                        "import": match.group(1),
                        "source": match.group(2)
                    })
                else:
                    # Side-effect import
                    imports.append({
                        "source": match.group(1),
                        "type": "side-effect"
                    })
        
        # Process CommonJS requires
        matches = re.finditer(require_pattern, content)
        for match in matches:
            var_part = match.group(1).strip()
            source = match.group(2)
            
            if '{' in var_part:
                # Destructuring assignment
                destructured = re.search(r'\{\s*([\w\s,]+)\s*\}', var_part)
                if destructured:
                    modules = [m.strip() for m in destructured.group(1).split(',')]
                    for module in modules:
                        if ':' in module:
                            orig, alias = module.split(':')
                            imports.append({
                                "import": orig.strip(),
                                "source": source,
                                "alias": alias.strip(),
                                "type": "require"
                            })
                        else:
                            imports.append({
                                "import": module.strip(),
                                "source": source,
                                "type": "require"
                            })
            else:
                imports.append({
                    "variable": var_part,
                    "source": source,
                    "type": "require"
                })
        
        return imports
    
    def extract_functions(self, content, language):
        """Extract function names and definitions from code"""
        functions = []
        
        if language == "Python":
            # Match Python function declarations
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Get decorator list
                        decorators = []
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Name):
                                decorators.append(decorator.id)
                            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                                decorators.append(decorator.func.id)
                            elif isinstance(decorator, ast.Attribute):
                                decorators.append(f"{decorator.value.id}.{decorator.attr}")
                        
                        # Get parameters
                        params = []
                        for arg in node.args.args:
                            params.append(arg.arg)
                        
                        # Check if it's a method in a class
                        parent_class = None
                        for parent in ast.walk(tree):
                            if isinstance(parent, ast.ClassDef):
                                for item in parent.body:
                                    if isinstance(item, ast.FunctionDef) and item.name == node.name:
                                        parent_class = parent.name
                                        break
                                if parent_class:
                                    break
                        
                        functions.append({
                            "name": node.name,
                            "language": "Python",
                            "is_method": parent_class is not None,
                            "class": parent_class,
                            "docstring": ast.get_docstring(node),
                            "decorators": decorators,
                            "parameters": params,
                            "line_number": node.lineno
                        })
            except SyntaxError:
                # Fallback to regex for files with syntax errors
                func_matches = re.finditer(r'def\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)(?:\s*->.*?)?\s*:', content)
                for match in func_matches:
                    params = [p.strip().split('=')[0].strip() for p in match.group(2).split(',') if p.strip()]
                    functions.append({
                        "name": match.group(1),
                        "language": "Python",
                        "parameters": params
                    })
        
        elif language in ["JavaScript", "TypeScript", "JavaScript (React)", "TypeScript (React)"]:
            # Match JavaScript/TypeScript function declarations and methods
            patterns = [
                # Standard function declarations
                r'function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)',
                # Arrow functions and function expressions
                r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>',
                r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?function\s*\(([^)]*)\)',
                # Class methods
                r'(?:async\s+)?(?:static\s+)?(?:get\s+|set\s+)?([a-zA-Z0-9_$]+)\s*\(([^)]*)\)\s*(?:\{|=>)'
            ]
            
            for pattern in patterns:
                func_matches = re.finditer(pattern, content)
                for match in func_matches:
                    # Extract parameters
                    params = [p.strip().split('=')[0].strip() for p in match.group(2).split(',') if p.strip()]
                    
                    # Determine if it's a method (rough heuristic)
                    is_method = False
                    class_name = None
                    
                    # Look for class context (very basic approach)
                    if "class" in content[:match.start()]:
                        class_match = re.search(r'class\s+([a-zA-Z0-9_$]+)', content[:match.start()])
                        if class_match and '{' in content[class_match.end():match.start()]:
                            is_method = True
                            class_name = class_match.group(1)
                    
                    functions.append({
                        "name": match.group(1),
                        "language": language,
                        "is_method": is_method,
                        "class": class_name,
                        "parameters": params
                    })
            
            # For TypeScript, also look for typed function declarations
            if language in ["TypeScript", "TypeScript (React)"]:
                typed_func_matches = re.finditer(r'(?:function|async\s+function)\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)\s*:\s*([a-zA-Z0-9_$<>[\]]+)', content)
                for match in typed_func_matches:
                    functions.append({
                        "name": match.group(1),
                        "language": language,
                        "parameters": [p.strip().split('=')[0].strip() for p in match.group(2).split(',') if p.strip()],
                        "return_type": match.group(3)
                    })
        
        elif language == "Java":
            # Match Java method declarations
            method_matches = re.finditer(r'(?:public|private|protected)?\s+(?:static\s+)?(?:final\s+)?([a-zA-Z0-9_<>.]+)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)', content)
            for match in method_matches:
                return_type = match.group(1)
                method_name = match.group(2)
                
                # Skip if found return type is a declaration keyword
                if return_type in ["class", "interface", "enum"]:
                    continue
                
                # Extract parameters
                params_str = match.group(3).strip()
                params = []
                if params_str:
                    # Handle multiple parameters
                    param_parts = []
                    bracket_count = 0
                    current_part = ""
                    
                    for char in params_str:
                        if char == ',' and bracket_count == 0:
                            param_parts.append(current_part.strip())
                            current_part = ""
                        else:
                            current_part += char
                            if char == '<':
                                bracket_count += 1
                            elif char == '>':
                                bracket_count -= 1
                    
                    if current_part:
                        param_parts.append(current_part.strip())
                    
                    for part in param_parts:
                        # Extract parameter name (last word before any = or ,)
                        param_match = re.search(r'(\w+)(?:\s*=.*)?$', part)
                        if param_match:
                            params.append(param_match.group(1))
                
                # Check if it's in a class
                class_match = re.search(r'class\s+([a-zA-Z0-9_]+)', content[:match.start()])
                class_name = class_match.group(1) if class_match else None
                
                functions.append({
                    "name": method_name,
                    "language": "Java",
                    "return_type": return_type,
                    "is_method": class_name is not None,
                    "class": class_name,
                    "parameters": params
                })
        
        return functions
    
    def extract_classes(self, content, language):
        """Extract class names and information from code"""
        classes = []
        
        if language == "Python":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Get base classes
                        bases = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                bases.append(base.id)
                            elif isinstance(base, ast.Attribute):
                                bases.append(f"{base.value.id}.{base.attr}")
                        
                        # Get class docstring
                        doc = ast.get_docstring(node)
                        
                        # Get methods
                        methods = []
                        for child in node.body:
                            if isinstance(child, ast.FunctionDef):
                                methods.append(child.name)
                        
                        # Get decorators
                        decorators = []
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Name):
                                decorators.append(decorator.id)
                            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                                decorators.append(decorator.func.id)
                            elif isinstance(decorator, ast.Attribute):
                                decorators.append(f"{decorator.value.id}.{decorator.attr}")
                        
                        classes.append({
                            "name": node.name,
                            "language": "Python",
                            "bases": bases,
                            "docstring": doc,
                            "methods": methods,
                            "decorators": decorators,
                            "line_number": node.lineno
                        })
            except SyntaxError:
                # Fallback to regex for files with syntax errors
                class_matches = re.finditer(r'class\s+([a-zA-Z0-9_]+)(?:\s*\(([^)]*)\))?:', content)
                for match in class_matches:
                    # Extract base classes
                    bases = [b.strip() for b in match.group(2).split(',') if b.strip()]
                    
                    # Get class docstring
                    doc = re.search(r'"""(.*?)"""', content[:match.start()])
                    doc = doc.group(1) if doc else None
                    
                    # Get methods
                    methods = []
                    method_matches = re.finditer(r'def\s+([a-zA-Z0-9_]+)\s*\(\s*\)', content)
                    for method_match in method_matches:
                        methods.append(method_match.group(1))
                        
                    # Get decorators
                    decorators = []
                    decorator_matches = re.finditer(r'@([a-zA-Z0-9_]+)', content[:match.start()])
                    for decorator_match in decorator_matches:
                        decorators.append(decorator_match.group(1))
                        
                    classes.append({
                        "name": match.group(1),
                        "language": "Python",
                        "bases": bases,
                        "docstring": doc,
                        "methods": methods,
                        "decorators": decorators,
                        "line_number": match.start()
                    })
                    
        elif language == "Java":
            # Match Java class declarations
            class_matches = re.finditer(r'public\s+class\s+([a-zA-Z0-9_]+)(?:\s+extends\s+([a-zA-Z0-9_<>.]+))?(?:\s+implements\s+([a-zA-Z0-9_<>.,\s]+))?', content)
            for match in class_matches:
                # Get class docstring
                doc = re.search(r'/\*\*(.*?)\*/', content[:match.start()])
                doc = doc.group(1) if doc else None
                
                # Get methods
                methods = []
                method_matches = re.finditer(r'public\s+([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\s*\(\s*\)', content)
                for method_match in method_matches:
                    methods.append(method_match.group(2))
                    
                # Get decorators
                decorators = []
                decorator_matches = re.finditer(r'@([a-zA-Z0-9_]+)', content[:match.start()])
                for decorator_match in decorator_matches:
                    decorators.append(decorator_match.group(1))
                    
                classes.append({
                    "name": match.group(1),
                    "language": "Java",
                    "docstring": doc,
                    "methods": methods,
                    "decorators": decorators,
                    "line_number": match.start()
                })
                
        return classes
    
    def extract_variables(self, content, language):
        """Extract important variable names from code"""
        variables = []
        
        if language == "Python":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    # Regular assignments
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                # Skip private variables and constants
                                if not target.id.startswith('_') and not target.id.isupper():
                                    value_type = self._get_python_value_type(node.value)
                                    variables.append({
                                        "name": target.id,
                                        "language": "Python",
                                        "type": value_type,
                                        "line_number": node.lineno
                                    })
                    
                    # Class attributes
                    elif isinstance(node, ast.ClassDef):
                        class_name = node.name
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        variables.append({
                                            "name": target.id,
                                            "language": "Python",
                                            "class": class_name,
                                            "is_class_attr": True,
                                            "line_number": item.lineno
                                        })
            except SyntaxError:
                # Fallback to regex for files with syntax errors
                var_matches = re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*[^\s=]', content)
                for match in var_matches:
                    var_name = match.group(1)
                    # Skip common keywords and function calls
                    if var_name not in ['if', 'for', 'while', 'def', 'class', 'import', 'from', 'as']:
                        variables.append({
                            "name": var_name,
                            "language": "Python"
                        })
        
        elif language in ["JavaScript", "TypeScript", "JavaScript (React)", "TypeScript (React)"]:
            # Match JS/TS variable declarations
            patterns = [
                r'(?:let|var|const)\s+([a-zA-Z0-9_$]+)\s*=\s*([^;]*)',
                r'this\.([a-zA-Z0-9_$]+)\s*=\s*([^;]*)'
            ]
            
            for pattern in patterns:
                var_matches = re.finditer(pattern, content)
                for match in var_matches:
                    var_name = match.group(1)
                    var_value = match.group(2).strip()
                    
                    # Try to determine variable type from its initialization
                    var_type = "unknown"
                    if var_value.startswith('"') or var_value.startswith("'") or var_value.startswith("`"):
                        var_type = "string"
                    elif var_value.isdigit() or (var_value.replace('.', '', 1).isdigit() and var_value.count('.') == 1):
                        var_type = "number"
                    elif var_value in ['true', 'false']:
                        var_type = "boolean"
                    elif var_value.startswith('['):
                        var_type = "array"
                    elif var_value.startswith('{'):
                        var_type = "object"
                    elif var_value.startswith('new '):
                        var_type = var_value.split('new ')[1].split('(')[0].strip()
                    elif var_value.startswith('function'):
                        var_type = "function"
                    elif var_value.startswith('(') and '=>' in var_value:
                        var_type = "arrow function"
                    
                    is_class_property = match.group(0).startswith('this.')
                    
                    variables.append({
                        "name": var_name,
                        "language": language,
                        "type": var_type,
                        "is_class_property": is_class_property
                    })
            
            # For TypeScript, also look for typed variable declarations
            if language in ["TypeScript", "TypeScript (React)"]:
                typed_var_matches = re.finditer(r'(?:let|var|const)\s+([a-zA-Z0-9_$]+)\s*:\s*([a-zA-Z0-9_$<>[\]]+)', content)
                for match in typed_var_matches:
                    variables.append({
                        "name": match.group(1),
                        "language": language,
                        "declared_type": match.group(2)
                    })
        
        elif language == "Java":
            # Match Java variable declarations
            var_matches = re.finditer(r'(?:private|public|protected)?\s+(?:static\s+)?(?:final\s+)?([a-zA-Z0-9_<>.]+)\s+([a-zA-Z0-9_]+)\s*(?:=\s*([^;]*))?;', content)
            for match in var_matches:
                var_type = match.group(1)
                var_name = match.group(2)
                var_value = match.group(3) if match.group(3) else None
                
                # Skip method declarations which can be caught by this pattern
                if var_type in ["class", "interface", "enum"] or "(" in match.group(0):
                    continue
                
                # Check if it's a class field
                class_match = re.search(r'class\s+([a-zA-Z0-9_]+)', content[:match.start()])
                class_name = class_match.group(1) if class_match else None
                
                variables.append({
                    "name": var_name,
                    "language": "Java",
                    "type": var_type,
                    "initial_value": var_value,
                    "class": class_name,
                    "is_class_field": class_name is not None
                })
        
        return variables
    
    def _get_python_value_type(self, node):
        """Helper to determine Python variable type from AST"""
        if isinstance(node, ast.Num):
            return "number"
        elif isinstance(node, ast.Str):
            return "string"
        elif isinstance(node, ast.List) or isinstance(node, ast.Tuple):
            return "list/tuple"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.NameConstant) and node.value in [True, False]:
            return "boolean"
        elif isinstance(node, ast.NameConstant) and node.value is None:
            return "None"
        elif isinstance(node, ast.Call):
            if hasattr(node.func, 'id'):
                return f"call:{node.func.id}"
            elif hasattr(node.func, 'attr'):
                return f"call:{node.func.attr}"
        return "unknown"
    
    def analyze_notebook(self, content):
        """Analyze Jupyter notebook content"""
        try:
            notebook = nbformat.reads(content, as_version=4)
            
            # Extract code cells
            cells = []
            for i, cell in enumerate(notebook.cells):
                if cell.cell_type == 'code':
                    cells.append({
                        "index": i,
                        "content": cell.source,
                        "type": "code"
                    })
                elif cell.cell_type == 'markdown':
                    cells.append({
                        "index": i,
                        "content": cell.source,
                        "type": "markdown"
                    })
            
            # Convert all code cells to a single Python file
            python_exporter = PythonExporter()
            python_code, _ = python_exporter.from_notebook_node(notebook)
            
            return {
                "cells": cells,
                "cell_count": len(notebook.cells),
                "code_cell_count": sum(1 for cell in notebook.cells if cell.cell_type == 'code'),
                "markdown_cell_count": sum(1 for cell in notebook.cells if cell.cell_type == 'markdown'),
                "python_code": python_code
            }
        except Exception as e:
            return {"error": str(e)}
    
    def scan_for_database_connections(self, content):
        """Scan code for database connection patterns"""
        found_connections = []
        
        for db_type, patterns in DB_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    if db_type not in [conn for conn in found_connections]:
                        found_connections.append(db_type)
                        break  # Found this database type, no need to check other patterns
        
        return found_connections
    
    def scan_for_api_patterns(self, content):
        """Scan code for API usage patterns"""
        found_patterns = []
        
        for api_type, patterns in API_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    if api_type not in [api for api in found_patterns]:
                        found_patterns.append(api_type)
                        break  # Found this API type, no need to check other patterns
        
        return found_patterns
    
    def identify_frameworks(self, content, language):
        """Identify frameworks used in the code"""
        frameworks = []
        
        for category, framework_dict in FRAMEWORK_PATTERNS.items():
            for framework, patterns in framework_dict.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        frameworks.append({
                            "category": category,
                            "name": framework
                        })
                        break  # Found this framework, no need to check other patterns
        
        return frameworks
    
    def extract_urls(self, content):
        """Extract URLs from the code"""
        url_pattern = r'(?:https?://|www\.)[^\s<>"\']+(?<![,.;:])'
        urls = re.findall(url_pattern, content)
        
        # Clean up URLs
        urls = [url for url in urls if len(url) > 7]  # Skip very short matches
        
        # Categorize URLs (basic)
        categorized = []
        for url in urls:
            category = "unknown"
            if "api" in url.lower():
                category = "API"
            elif any(domain in url.lower() for domain in ["github", "gitlab", "bitbucket"]):
                category = "Repository"
            elif any(domain in url.lower() for domain in ["cdn", "assets", "static"]):
                category = "Content/Assets"
            elif any(domain in url.lower() for domain in ["docs", "documentation"]):
                category = "Documentation"
            
            categorized.append({
                "url": url,
                "category": category
            })
        
        return categorized
    
    def extract_environment_variables(self, content):
        """Extract environment variable usage"""
        env_patterns = [
            r'os\.environ\.get\(["\']([^"\']+)["\']',  # Python
            r'os\.getenv\(["\']([^"\']+)["\']',        # Python
            r'process\.env\.([A-Za-z0-9_]+)',          # Node.js
            r'process\.env\[["\']([^"\']+)["\']',      # Node.js
            r'dotenv',                                  # dotenv package
            r'\.env',                                   # .env files
            r'System\.getenv\(["\']([^"\']+)["\']'     # Java
        ]
        
        env_vars = []
        for pattern in env_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if match.groups():
                    var_name = match.group(1)
                    env_vars.append(var_name)
        
        return list(set(env_vars))  # Remove duplicates
    
    def analyze_data_flow(self, files_data, functions, db_connections, api_usage):
        """Analyze data flow in the codebase"""
        # Build data flow graph
        graph = nx.DiGraph()
        
        # Add nodes for files
        for file in files_data:
            if file.get("has_db_connection", False):
                graph.add_node(file["path"], type="file", has_db=True, db_types=file.get("db_types", []))
            else:
                graph.add_node(file["path"], type="file")
        
        # Add nodes for databases
        for db_type in set(db for connections in db_connections.values() for db in connections):
            graph.add_node(f"DB:{db_type}", type="database")
        
        # Connect files to databases
        for file_path, db_types in db_connections.items():
            for db_type in db_types:
                graph.add_edge(file_path, f"DB:{db_type}", type="uses")
                graph.add_edge(f"DB:{db_type}", file_path, type="used_by")
        
        # Add import relationship edges (basic approximation)
        import_patterns = {
            "Python": r'(?:from|import)\s+([\w.]+)',
            "JavaScript": r'(?:import.*from\s+["\']([^"\']+)["\']|require\(["\']([^"\']+)["\'])',
            "TypeScript": r'(?:import.*from\s+["\']([^"\']+)["\']|require\(["\']([^"\']+)["\'])',
            "Java": r'import\s+([\w.]+)'
        }
        
        for file in files_data:
            try:
                with open(os.path.join(self.temp_dir, "extracted", file["path"]), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    pattern = import_patterns.get(file["language"].split(" ")[0])
                    if not pattern:
                        continue
                    
                    imports = re.findall(pattern, content)
                    for imp in imports:
                        if isinstance(imp, tuple):  # Handle multiple capture groups
                            imp = next((i for i in imp if i), "")
                        
                        # Try to find the imported file
                        for other_file in files_data:
                            # Very basic matching - would need improvement for real use
                            if other_file["path"].endswith(f"{imp}.py") or \
                               other_file["path"].endswith(f"{imp}.js") or \
                               other_file["path"].endswith(f"{imp}.ts") or \
                               other_file["path"].endswith(f"{imp}.java") or \
                               imp in other_file["path"]:
                                graph.add_edge(file["path"], other_file["path"], type="imports")
            except Exception:
                pass
        
        # Create visualizable data
        nodes = []
        for node in graph.nodes():
            node_type = graph.nodes[node].get("type", "unknown")
            if node_type == "file":
                has_db = graph.nodes[node].get("has_db", False)
                nodes.append({
                    "id": node,
                    "label": os.path.basename(node),
                    "type": "file",
                    "has_db": has_db,
                    "db_types": graph.nodes[node].get("db_types", [])
                })
            elif node_type == "database":
                nodes.append({
                    "id": node,
                    "label": node.replace("DB:", ""),
                    "type": "database"
                })
        
        edges = []
        for source, target, data in graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": data.get("type", "unknown")
            })
        
        # Identify potential ETL processes or data pipelines
        etl_candidates = []
        for file in files_data:
            if file.get("has_db_connection", False) and any(api in file.get("api_patterns", []) for api in ["REST API", "ETL Process", "File System", "Cloud Storage"]):
                etl_candidates.append({
                    "file": file["path"],
                    "db_types": file.get("db_types", []),
                    "api_patterns": file.get("api_patterns", [])
                })
        
        return {
            "graph": {
                "nodes": nodes,
                "edges": edges
            },
            "etl_candidates": etl_candidates
        }
    
    def generate_data_flow_image(self, data_flow):
        """Generate a data flow diagram as an image"""
        try:
            G = nx.DiGraph()
            
            # Add nodes
            for node in data_flow["graph"]["nodes"]:
                if node["type"] == "database":
                    G.add_node(node["id"], color="red", shape="rectangle")
                elif node["type"] == "file" and node.get("has_db", False):
                    G.add_node(node["id"], color="orange", shape="ellipse")
                else:
                    G.add_node(node["id"], color="blue", shape="ellipse")
            
            # Add edges
            for edge in data_flow["graph"]["edges"]:
                if edge["type"] == "imports":
                    G.add_edge(edge["source"], edge["target"], color="green")
                elif edge["type"] == "uses":
                    G.add_edge(edge["source"], edge["target"], color="red")
                elif edge["type"] == "used_by":
                    G.add_edge(edge["source"], edge["target"], color="purple")
            
            # Create figure
            plt.figure(figsize=(12, 9))
            
            # Define node colors and shapes
            node_colors = [G.nodes[n].get("color", "blue") for n in G]
            node_shapes = {"rectangle": "s", "ellipse": "o"}
            
            # Position nodes using force-directed layout
            pos = nx.spring_layout(G, seed=42)
            
            # Draw nodes
            for shape, shape_code in node_shapes.items():
                node_list = [n for n in G.nodes() if G.nodes[n].get("shape") == shape]
                colors = [G.nodes[n].get("color", "blue") for n in node_list]
                nx.draw_networkx_nodes(G, pos, nodelist=node_list, node_shape=shape_code, 
                                      node_color=colors, node_size=800, alpha=0.8)
            
            # Draw edges
            for edge_type, edge_color in [("imports", "green"), ("uses", "red"), ("used_by", "purple")]:
                edge_list = [(u, v) for u, v, d in G.edges(data=True) if d.get("color") == edge_color]
                nx.draw_networkx_edges(G, pos, edgelist=edge_list, edge_color=edge_color, 
                                      arrows=True, width=1.5, alpha=0.7)
            
            # Add labels
            labels = {n: n.split("/")[-1] if "/" in n else (n.replace("DB:", "") if "DB:" in n else n) 
                     for n in G.nodes()}
            nx.draw_networkx_labels(G, pos, labels, font_size=10, font_family="sans-serif")
            
            # Add legend
            legend_elements = [
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='File'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='DB-Connected File'),
                plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='red', markersize=10, label='Database'),
                plt.Line2D([0], [0], color='green', lw=2, label='Imports'),
                plt.Line2D([0], [0], color='red', lw=2, label='Uses'),
                plt.Line2D([0], [0], color='purple', lw=2, label='Used By')
            ]
            plt.legend(handles=legend_elements, loc="upper right")
            
            plt.title("Data Flow Diagram", fontsize=16)
            plt.axis("off")
            
            # Save figure to BytesIO
            img_data = BytesIO()
            plt.savefig(img_data, format='png', dpi=300, bbox_inches='tight')
            img_data.seek(0)
            plt.close()
            
            return img_data
            
        except Exception as e:
            print(f"Error generating data flow image: {e}")
            return None
    
    def analyze_file(self, file_path, content, file_extension):
        """Analyze a single file"""
        language = LANGUAGE_EXTENSIONS.get(file_extension.lower(), "Other")
        
        # Count lines
        lines = content.count('\n') + 1
        
        # Extract functions, classes and variables based on language
        functions = self.extract_functions(content, language)
        classes = self.extract_classes(content, language)
        variables = self.extract_variables(content, language)
        
        # Scan for database connections
        db_connections = self.scan_for_database_connections(content)
        
        # Scan for API patterns
        api_patterns = self.scan_for_api_patterns(content)
        
        # Identify frameworks
        frameworks = self.identify_frameworks(content, language)
        
        # Extract URLs
        urls = self.extract_urls(content)
        
        # Extract environment variables
        env_vars = self.extract_environment_variables(content)
        
        # For Python files, extract imports
        imports = []
        if language == "Python":
            imports = self.extract_python_imports(content)
        elif language in ["JavaScript", "TypeScript", "JavaScript (React)", "TypeScript (React)"]:
            imports = self.extract_javascript_imports(content)
        
        # Special handling for Jupyter notebooks
        notebook_info = None
        if language == "Python (Notebook)":
            notebook_info = self.analyze_notebook(content)
        
        return {
            "language": language,
            "lines": lines,
            "functions": functions,
            "classes": classes,
            "variables": variables,
            "db_connections": db_connections,
            "api_patterns": api_patterns,
            "frameworks": frameworks,
            "urls": urls,
            "env_vars": env_vars,
            "imports": imports,
            "notebook_info": notebook_info
        }
    
    def analyze_codebase(self, uploaded_file, api_key=None):
        """Analyze the uploaded zip file containing source code"""
        # Set OpenAI API key if provided
        if api_key:
            self.set_api_key(api_key)
        
        # Save uploaded zip to temp directory
        zip_path = os.path.join(self.temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Extract zip file
        extract_path = os.path.join(self.temp_dir, "extracted")
        os.makedirs(extract_path, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        except zipfile.BadZipFile:
            return {"error": "Invalid or corrupted ZIP file"}
        
        # Initialize results containers
        files_data = []
        language_data = {}
        all_functions = []
        all_classes = []
        all_variables = []
        db_connections = {}
        api_usage = {}
        framework_usage = {}
        file_dependencies = defaultdict(list)
        code_stats = {
            "total_files": 0,
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "total_variables": 0,
            "detected_databases": set(),
            "detected_apis": set(),
            "detected_frameworks": set()
        }
        
        # Analyze files
        for root, _, files in os.walk(extract_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, extract_path)
                
                # Skip hidden files and directories
                if any(part.startswith('.') for part in Path(rel_path).parts):
                    continue
                
                # Get file extension and language
                extension = Path(file_path).suffix.lower()
                language = LANGUAGE_EXTENSIONS.get(extension, "Other")
                
                # Skip binary files
                if extension in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.bin', '.exe', 
                                '.zip', '.tar', '.gz', '.7z', '.rar', '.so', '.dll']:
                    continue
                
                # Get file stats
                file_size = os.path.getsize(file_path)
                last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Update language stats
                language_data[language] = language_data.get(language, 0) + 1
                
                # Analyze file content
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # Analyze the file
                        analysis = self.analyze_file(rel_path, content, extension)
                        
                        # Update counts
                        lines = analysis["lines"]
                        functions = analysis["functions"]
                        classes = analysis["classes"]
                        variables = analysis["variables"]
                        db_conns = analysis["db_connections"]
                        api_patterns = analysis["api_patterns"]
                        frameworks = analysis["frameworks"]
                        
                        code_stats["total_lines"] += lines
                        
                        # Add metadata to functions, classes, variables
                        for func in functions:
                            func["file"] = rel_path
                        all_functions.extend(functions)
                        
                        for cls in classes:
                            cls["file"] = rel_path
                        all_classes.extend(classes)
                        
                        for var in variables:
                            var["file"] = rel_path
                        all_variables.extend(variables)
                        
                        # Track database connections
                        if db_conns:
                            db_connections[rel_path] = db_conns
                            code_stats["detected_databases"].update(db_conns)
                        
                        # Track API patterns
                        if api_patterns:
                            api_usage[rel_path] = api_patterns
                            code_stats["detected_apis"].update(api_patterns)
                        
                        # Track frameworks
                        if frameworks:
                            framework_names = [fw["name"] for fw in frameworks]
                            framework_usage[rel_path] = framework_names
                            code_stats["detected_frameworks"].update(framework_names)
                        
                        # Add file data
                        files_data.append({
                            "name": file_name,
                            "path": rel_path,
                            "extension": extension,
                            "language": language,
                            "size": file_size,
                            "lines": lines,
                            "functions": len(functions),
                            "classes": len(classes),
                            "has_db_connection": bool(db_conns),
                            "db_types": db_conns,
                            "api_patterns": api_patterns,
                            "frameworks": [fw["name"] for fw in frameworks],
                            "last_modified": last_modified
                        })
                
                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read as text
                    files_data.append({
                        "name": file_name,
                        "path": rel_path,
                        "extension": extension,
                        "language": language,
                        "size": file_size,
                        "is_binary": True,
                        "last_modified": last_modified
                    })
        
        # Update code stats
        code_stats["total_files"] = len(files_data)
        code_stats["total_functions"] = len(all_functions)
        code_stats["total_classes"] = len(all_classes)
        code_stats["total_variables"] = len(all_variables)
        
        return {
            "files": files_data,
            "language_stats": language_data,
            "functions": all_functions,
            "classes": all_classes,
            "variables": all_variables,
            "db_connections": db_connections,
            "api_usage": api_usage,
            "framework_usage": framework_usage,
            "code_stats": code_stats
        }
