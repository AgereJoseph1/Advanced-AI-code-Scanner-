"""
LLM-based code analyzer module for advanced code analysis across multiple programming languages.
"""

import os
from openai import OpenAI
from typing import Dict, List, Any, Optional, Set, Union, Tuple
import json
import time
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMAnalyzer:
    """
    LLM-powered code analyzer that provides deep insights into code quality,
    architecture, variables, transformations, and external API communications.
    Specialized for analyzing legacy codebases and extracting comprehensive metadata.
    """
    
    # Supported programming languages and their file extensions
    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c/cpp header",
        ".hpp": "c++ header",
        ".cs": "csharp",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".r": "r",
        ".scala": "scala",
        ".pl": "perl",
        ".sh": "bash",
        ".ps1": "powershell",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".vue": "vue",
        ".rs": "rust",
        ".m": "objective-c",
        ".mm": "objective-c++",
        ".groovy": "groovy",
        ".dart": "dart",
        ".lua": "lua",
        ".clj": "clojure",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".hrl": "erlang",
        ".hs": "haskell",
        ".fs": "f#",
        ".fsx": "f#",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".config": "config",
        ".md": "markdown",
        ".rst": "restructuredtext",
        ".toml": "toml",
        ".ini": "ini",
        ".bat": "batch",
        ".cmd": "batch",
        ".dockerfile": "dockerfile",
        ".tf": "terraform",
        ".hcl": "hcl",
    }
    
    # Common frameworks and libraries for different languages
    COMMON_FRAMEWORKS = {
        "python": [
            "django", "flask", "fastapi", "pyramid", "tornado", "bottle", "cherrypy",
            "numpy", "pandas", "scikit-learn", "tensorflow", "pytorch", "keras",
            "matplotlib", "seaborn", "plotly", "dash", "streamlit", "gradio",
            "sqlalchemy", "django-orm", "pony", "peewee", "celery", "rq", "dramatiq",
            "pytest", "unittest", "nose", "behave", "robot", "selenium", "requests",
            "beautifulsoup", "scrapy", "lxml", "pydantic", "marshmallow", "dataclasses"
        ],
        "javascript": [
            "react", "angular", "vue", "svelte", "next.js", "nuxt.js", "gatsby",
            "express", "koa", "hapi", "nest.js", "meteor", "sails", "loopback",
            "jquery", "d3", "three.js", "chart.js", "highcharts", "echarts",
            "redux", "mobx", "vuex", "pinia", "recoil", "jotai", "zustand",
            "jest", "mocha", "jasmine", "karma", "cypress", "puppeteer", "playwright",
            "axios", "fetch", "graphql", "apollo", "relay", "swr", "react-query",
            "webpack", "rollup", "parcel", "vite", "esbuild", "babel", "typescript"
        ]
    }
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo"):
        """
        Initialize the LLM analyzer.
        
        Args:
            api_key: OpenAI API key. If None, will try to use the OPENAI_API_KEY environment variable.
            model: The OpenAI model to use for analysis. Default is gpt-4-turbo for best results.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = model
        
        if not self.client:
            logger.warning("No OpenAI API key provided. LLM analysis will not be available.")
    
    def detect_language(self, file_path: str, content: str) -> str:
        """
        Detect the programming language based on file extension or content.
        Enhanced to better handle legacy codebases with mixed or unusual patterns.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Detected programming language
        """
        # First try to detect by file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.SUPPORTED_LANGUAGES:
            return self.SUPPORTED_LANGUAGES[ext]
        
        # Check for special filenames
        filename = os.path.basename(file_path).lower()
        if filename == "dockerfile":
            return "dockerfile"
        elif filename in ["makefile", "gnumakefile", "makefile.am", "makefile.in"]:
            return "makefile"
        elif filename.startswith("requirements") and filename.endswith(".txt"):
            return "requirements"
        elif filename in [".gitignore", ".dockerignore"]:
            return "ignore"
        
        # If extension is not recognized, use content-based heuristics
        if content:
            # Check for shebang
            first_line = content.split('\n', 1)[0] if '\n' in content else content
            if first_line.startswith("#!"):
                if "python" in first_line:
                    return "python"
                elif "node" in first_line:
                    return "javascript"
                elif "bash" in first_line or "sh" in first_line:
                    return "bash"
                elif "perl" in first_line:
                    return "perl"
                elif "ruby" in first_line:
                    return "ruby"
            
            # Check for common language patterns
            if "<?php" in content[:1000]:
                return "php"
            elif "<html" in content[:1000].lower() or "<!doctype html" in content[:1000].lower():
                return "html"
            elif "import React" in content[:1000] or "from 'react'" in content[:1000]:
                return "jsx"
            elif "package " in content[:1000] and "import " in content[:1000] and "{" in content[:1000]:
                return "java"
            elif "#include" in content[:1000] and (".h" in content[:1000] or ".hpp" in content[:1000]):
                return "cpp"
        
        # If still not detected, ask the LLM to identify the language
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use a smaller model for language detection
                    messages=[
                        {"role": "system", "content": "You are a programming language detection expert. Identify the programming language of the given code snippet. Respond with only the language name in lowercase."},
                        {"role": "user", "content": f"Identify the programming language:\n\n```\n{content[:1000]}\n```"}
                    ],
                    temperature=0.1,
                    max_tokens=20
                )
                detected_language = response.choices[0].message.content.strip().lower()
                return detected_language
            except Exception as e:
                logger.warning(f"Error during language detection: {str(e)}")
        
        # Default to 'unknown' if detection fails
        return "unknown"
    
    def analyze_code(self, content: str, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze code using an LLM to get advanced insights.
        Enhanced to provide deeper analysis of legacy codebases.
        
        Args:
            content: The source code content
            file_path: Path to the file being analyzed
            language: Programming language of the code (optional, will be detected if not provided)
            
        Returns:
            Dictionary containing LLM analysis results
        """
        if not self.client:
            return {
                "error": "No API key provided. Set the OPENAI_API_KEY environment variable or pass an API key to the constructor."
            }
        
        # Detect language if not provided
        if not language or language == "unknown":
            language = self.detect_language(file_path, content)
            
        try:
            # Prepare the prompt for the LLM
            prompt = self._create_analysis_prompt(content, file_path, language)
            
            # Call the OpenAI API using the new client interface
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert code analyzer with deep knowledge of all programming languages, particularly legacy systems. Analyze the given code and provide detailed insights about its structure, purpose, variables, transformations, external API communications, quality, and technical debt. Focus on helping users understand complex or legacy codebases."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lower temperature for more consistent analysis
                max_tokens=4000,   # Increased token limit for more detailed analysis
                response_format={"type": "json_object"}  # Request JSON response
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            
            # Try to extract structured data from the JSON response
            try:
                analysis_data = json.loads(analysis_text)
            except json.JSONDecodeError:
                # Fall back to processing the text response
                analysis_data = self._process_text_analysis(analysis_text)
                logger.warning(f"Failed to parse JSON response for {file_path}. Falling back to text processing.")
            
            # Enhance the analysis with additional metadata
            analysis_data = self._enhance_analysis(analysis_data, content, language, file_path)
            
            return {
                "file": file_path,
                "language": language,
                "llm_analysis": analysis_data,
                "raw_response": analysis_text
            }
            
        except Exception as e:
            logger.error(f"Error during LLM analysis of {file_path}: {str(e)}")
            return {
                "error": f"Error during LLM analysis: {str(e)}",
                "file": file_path
            }
    
    def analyze_project_structure(self, file_paths: List[str], file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze the overall project structure and generate lineage information.
        Enhanced to provide more comprehensive analysis of legacy codebases.
        
        Args:
            file_paths: List of all file paths in the project
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Project structure analysis with detailed lineage metadata
        """
        if not self.client:
            return {
                "error": "No API key provided. Set the OPENAI_API_KEY environment variable or pass an API key to the constructor."
            }
            
        try:
            # Prepare file list with languages
            file_info = []
            language_stats = {}
            
            # Analyze file types and languages
            for file_path in file_paths:
                if file_path in file_contents:
                    language = self.detect_language(file_path, file_contents[file_path])
                    file_info.append(f"{file_path} ({language})")
                    
                    # Track language statistics
                    if language not in language_stats:
                        language_stats[language] = 0
                    language_stats[language] += 1
                else:
                    file_info.append(file_path)
            
            # Extract key files for deeper analysis
            key_files = self._identify_key_files(file_paths, file_contents)
            
            # Extract dependencies from key files
            dependencies = self._extract_dependencies(key_files, file_contents)
            
            # Create a prompt for project structure analysis
            prompt = f"""
Analyze the structure of this project based on the file list and key information below:

File List (showing {len(file_info[:100])} of {len(file_info)} files):
{chr(10).join(file_info[:100])}

Language Distribution:
{chr(10).join([f"- {lang}: {count} files" for lang, count in sorted(language_stats.items(), key=lambda x: x[1], reverse=True) if lang != 'unknown'])}

Key Files:
{chr(10).join([f"- {file}" for file in key_files[:10]])}

Detected Dependencies:
{chr(10).join([f"- {dep}" for dep in dependencies[:20]])}

Based on this information, provide a comprehensive analysis of the project structure in JSON format:
{{
    "project_type": "<type of project (e.g., web application, API, library, etc.)>",
    "main_languages": [<list of main programming languages used>],
    "architecture": "<architectural pattern identified (e.g., MVC, microservices, etc.)>",
    "entry_points": [<likely entry points or main files>],
    "dependencies": [
        {{
            "name": "<dependency name>",
            "purpose": "<what this dependency is used for>",
            "type": "<framework, library, tool, etc.>"
        }}
    ],
    "code_lineage": {{
        "purpose": "<overall purpose of the codebase>",
        "history": "<likely evolution of the codebase>",
        "organization": "<how the code is organized>",
        "complexity": "<assessment of codebase complexity>"
    }},
    "technical_stack": {{
        "frontend": [<frontend technologies>],
        "backend": [<backend technologies>],
        "database": [<database technologies>],
        "infrastructure": [<infrastructure technologies>]
    }},
    "data_flow": {{
        "sources": [<data sources>],
        "transformations": [<key data transformations>],
        "sinks": [<data destinations>]
    }},
    "key_components": [
        {{
            "name": "<component name>",
            "purpose": "<component purpose>",
            "files": [<files that make up this component>]
        }}
    ],
    "legacy_aspects": [<list of legacy code patterns or technologies>],
    "modernization_opportunities": [<suggestions for modernizing the codebase>],
    "summary": "<overall assessment of the project structure>"
}}

Focus on providing accurate insights about the project's structure, purpose, technical stack, and lineage. If you're uncertain about any aspect, provide your best assessment based on the available information.
"""
            
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert software architect with deep knowledge of project structures across all programming languages and frameworks. You specialize in analyzing legacy codebases and providing insights about their structure, purpose, and technical stack."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"}  # Request JSON response
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            
            # Extract JSON data
            try:
                analysis_data = json.loads(analysis_text)
                
                # Enhance the analysis with additional metadata
                analysis_data = self._enhance_project_analysis(analysis_data, file_paths, file_contents, language_stats, dependencies)
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {str(e)}")
                # Create a basic structure if JSON parsing fails
                analysis_data = {
                    "project_type": "Unknown",
                    "main_languages": self._extract_main_languages(file_info),
                    "architecture": "Could not determine",
                    "entry_points": self._identify_key_files(file_paths, file_contents)[:5],
                    "dependencies": [{"name": dep, "purpose": "Unknown", "type": "Unknown"} for dep in dependencies[:10]],
                    "code_lineage": {
                        "purpose": "Could not determine the overall purpose of the codebase.",
                        "history": "Unknown",
                        "organization": "Unknown",
                        "complexity": "Unknown"
                    },
                    "technical_stack": {
                        "frontend": [],
                        "backend": [],
                        "database": [],
                        "infrastructure": []
                    },
                    "data_flow": {
                        "sources": [],
                        "transformations": [],
                        "sinks": []
                    },
                    "key_components": [],
                    "legacy_aspects": [],
                    "modernization_opportunities": [],
                    "summary": "Analysis could not be completed in structured format. Please see raw response."
                }
            
            return {
                "project_structure": analysis_data,
                "language_stats": language_stats,
                "raw_response": analysis_text
            }
            
        except Exception as e:
            logger.error(f"Error during project structure analysis: {str(e)}")
            return {
                "error": f"Error during project structure analysis: {str(e)}"
            }
    
    def _identify_key_files(self, file_paths: List[str], file_contents: Dict[str, str]) -> List[str]:
        """
        Identify key files in the project that are likely to be important.
        
        Args:
            file_paths: List of all file paths in the project
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            List of key file paths
        """
        key_files = []
        
        # Common patterns for key files
        entry_point_patterns = [
            "main.py", "app.py", "index.js", "server.js", "application.java",
            "Program.cs", "Main.java", "App.js", "App.tsx", "index.html"
        ]
        
        config_patterns = [
            "requirements.txt", "package.json", "setup.py", "pom.xml", 
            "build.gradle", ".env", "config.json", "settings.py", "webpack.config.js"
        ]
        
        # First, look for exact matches
        for pattern in entry_point_patterns + config_patterns:
            for file_path in file_paths:
                if os.path.basename(file_path) == pattern:
                    key_files.append(file_path)
        
        # Then, look for partial matches in filenames
        if len(key_files) < 10:
            for file_path in file_paths:
                filename = os.path.basename(file_path).lower()
                if ("main" in filename or "app" in filename or "index" in filename or 
                    "server" in filename or "application" in filename or "config" in filename):
                    if file_path not in key_files:
                        key_files.append(file_path)
        
        # Look for files with significant content
        if len(key_files) < 10:
            for file_path in file_paths:
                if file_path in file_contents and len(file_contents[file_path]) > 1000:
                    if file_path not in key_files:
                        key_files.append(file_path)
        
        return key_files[:20]  # Limit to 20 key files
    
    def _extract_dependencies(self, key_files: List[str], file_contents: Dict[str, str]) -> List[str]:
        """
        Extract dependencies from key files.
        
        Args:
            key_files: List of key file paths
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            List of detected dependencies
        """
        dependencies = set()
        
        for file_path in key_files:
            if file_path not in file_contents:
                continue
                
            content = file_contents[file_path]
            ext = os.path.splitext(file_path)[1].lower()
            
            # Python dependencies
            if ext == ".py":
                # Look for import statements
                import_patterns = [
                    r"import\s+([a-zA-Z0-9_.]+)",
                    r"from\s+([a-zA-Z0-9_.]+)\s+import"
                ]
                
                for pattern in import_patterns:
                    for match in re.finditer(pattern, content):
                        module = match.group(1).split(".")[0]
                        if module not in ["__future__", "typing", "os", "sys", "re", "json", "time", "datetime"]:
                            dependencies.add(module)
            
            # JavaScript/TypeScript dependencies
            elif ext in [".js", ".jsx", ".ts", ".tsx"]:
                # Look for import statements and require calls
                import_patterns = [
                    r"import.*?from\s+['\"]([^.][^'\"]+)['\"]",
                    r"require\(['\"]([^.][^'\"]+)['\"]\)"
                ]
                
                for pattern in import_patterns:
                    for match in re.finditer(pattern, content):
                        module = match.group(1)
                        dependencies.add(module)
            
            # Package.json
            elif os.path.basename(file_path) == "package.json":
                try:
                    package_data = json.loads(content)
                    if "dependencies" in package_data:
                        for dep in package_data["dependencies"]:
                            dependencies.add(dep)
                    if "devDependencies" in package_data:
                        for dep in package_data["devDependencies"]:
                            dependencies.add(dep)
                except:
                    pass
            
            # Requirements.txt
            elif os.path.basename(file_path) == "requirements.txt":
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name (remove version specifiers)
                        package = re.split(r'[=<>~]', line)[0].strip()
                        if package:
                            dependencies.add(package)
        
        return list(dependencies)
    
    def _enhance_project_analysis(self, analysis_data: Dict[str, Any], 
                                 file_paths: List[str], 
                                 file_contents: Dict[str, str],
                                 language_stats: Dict[str, int],
                                 dependencies: List[str]) -> Dict[str, Any]:
        """
        Enhance the project analysis with additional metadata.
        
        Args:
            analysis_data: The analysis data from the LLM
            file_paths: List of all file paths in the project
            file_contents: Dictionary mapping file paths to their contents
            language_stats: Dictionary mapping languages to file counts
            dependencies: List of detected dependencies
            
        Returns:
            The enhanced analysis data
        """
        # Add file statistics
        analysis_data["file_stats"] = {
            "total_files": len(file_paths),
            "language_distribution": language_stats
        }
        
        # Add timestamp
        analysis_data["analysis_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Ensure dependencies are in the right format
        if "dependencies" not in analysis_data or not analysis_data["dependencies"]:
            analysis_data["dependencies"] = []
            for dep in dependencies[:20]:  # Limit to 20 dependencies
                analysis_data["dependencies"].append({
                    "name": dep,
                    "purpose": "Unknown",
                    "type": "library"
                })
        
        # Add lineage metadata if not present
        if "code_lineage" not in analysis_data:
            analysis_data["code_lineage"] = {
                "purpose": "Unknown",
                "history": "Unknown",
                "organization": "Unknown",
                "complexity": "Unknown"
            }
        
        return analysis_data
    
    def _create_analysis_prompt(self, content: str, file_path: str, language: str) -> str:
        """
        Create a prompt for the LLM to analyze the code.
        
        Args:
            content: The source code content
            file_path: Path to the file being analyzed
            language: Programming language of the code
            
        Returns:
            Prompt string for the LLM
        """
        filename = os.path.basename(file_path)
        
        prompt = f"""
Please analyze the following {language} code from file '{filename}':

```{language}
{content}
```

Provide a comprehensive analysis in JSON format with the following structure:
{{
    "code_quality": {{
        "score": <0-100 score>,
        "strengths": [<list of code strengths>],
        "weaknesses": [<list of code weaknesses>]
    }},
    "variables": {{
        "important_variables": [
            {{
                "name": "<variable name>",
                "type": "<variable type if detectable>",
                "purpose": "<brief description of the variable's purpose>",
                "transformations": [<list of transformations applied to this variable>]
            }}
        ]
    }},
    "functions": {{
        "count": <number of functions/methods>,
        "important_functions": [
            {{
                "name": "<function name>",
                "purpose": "<brief description of what the function does>",
                "parameters": [<list of parameters>],
                "return_value": "<description of what the function returns>"
            }}
        ]
    }},
    "classes": {{
        "count": <number of classes>,
        "important_classes": [
            {{
                "name": "<class name>",
                "purpose": "<brief description of the class's purpose>",
                "properties": [<list of important properties>],
                "methods": [<list of important methods>]
            }}
        ]
    }},
    "external_communications": {{
        "apis": [
            {{
                "name": "<API name or endpoint>",
                "purpose": "<what this API is used for>",
                "method": "<HTTP method if applicable>"
            }}
        ],
        "databases": [
            {{
                "type": "<database type>",
                "operations": [<list of operations performed>]
            }}
        ],
        "file_operations": [<list of file operations performed>]
    }},
    "data_transformations": [
        {{
            "description": "<description of data transformation>",
            "input": "<input data format or source>",
            "output": "<output data format or destination>"
        }}
    ],
    "architecture": {{
        "patterns": [<identified design patterns>],
        "anti_patterns": [<identified anti-patterns>],
        "suggestions": [<architectural improvement suggestions>]
    }},
    "security": {{
        "vulnerabilities": [<potential security issues>],
        "severity": <"low", "medium", or "high">,
        "mitigations": [<security improvement suggestions>]
    }},
    "summary": "<overall assessment in 2-3 sentences>"
}}

Focus on providing actionable insights and specific information about variables, transformations, and external communications. If a section is not applicable, include an empty list or appropriate default values.
"""
        return prompt
    
    def _process_text_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """
        Process a text analysis response into structured data.
        
        Args:
            analysis_text: The text response from the LLM
            
        Returns:
            Structured data extracted from the text
        """
        # Default structure with enhanced fields for variables, transformations, and external communications
        analysis_data = {
            "code_quality": {
                "score": 0,
                "strengths": [],
                "weaknesses": []
            },
            "variables": {
                "important_variables": []
            },
            "functions": {
                "count": 0,
                "important_functions": []
            },
            "classes": {
                "count": 0,
                "important_classes": []
            },
            "external_communications": {
                "apis": [],
                "databases": [],
                "file_operations": []
            },
            "data_transformations": [],
            "architecture": {
                "patterns": [],
                "anti_patterns": [],
                "suggestions": []
            },
            "security": {
                "vulnerabilities": [],
                "severity": "low",
                "mitigations": []
            },
            "summary": "No summary available."
        }
        
        # Extract code quality score
        if "code quality" in analysis_text.lower() and "score" in analysis_text.lower():
            for line in analysis_text.split("\n"):
                if "code quality" in line.lower() and "score" in line.lower():
                    try:
                        score = int(''.join(filter(str.isdigit, line)))
                        if 0 <= score <= 100:
                            analysis_data["code_quality"]["score"] = score
                    except ValueError:
                        pass
        
        # Extract strengths
        if "strength" in analysis_text.lower():
            strengths_section = self._extract_section(analysis_text, "strength")
            if strengths_section:
                strengths = self._extract_list_items(strengths_section)
                if strengths:
                    analysis_data["code_quality"]["strengths"] = strengths
        
        # Extract weaknesses
        if "weakness" in analysis_text.lower():
            weaknesses_section = self._extract_section(analysis_text, "weakness")
            if weaknesses_section:
                weaknesses = self._extract_list_items(weaknesses_section)
                if weaknesses:
                    analysis_data["code_quality"]["weaknesses"] = weaknesses
        
        # Extract variables information
        if "variable" in analysis_text.lower():
            variables_section = self._extract_section(analysis_text, "variable")
            if variables_section:
                # Try to extract structured variable information
                var_items = self._extract_list_items(variables_section)
                if var_items:
                    for item in var_items:
                        var_info = {"name": "unknown", "type": "unknown", "purpose": item, "transformations": []}
                        # Try to extract variable name
                        name_match = re.search(r'`([^`]+)`|"([^"]+)"|\'([^\']+)\'', item)
                        if name_match:
                            var_name = next(filter(None, name_match.groups()))
                            var_info["name"] = var_name
                        analysis_data["variables"]["important_variables"].append(var_info)
        
        # Extract functions information
        if "function" in analysis_text.lower():
            functions_section = self._extract_section(analysis_text, "function")
            if functions_section:
                # Try to extract function count
                count_match = re.search(r'(\d+)\s+functions?', functions_section.lower())
                if count_match:
                    analysis_data["functions"]["count"] = int(count_match.group(1))
                
                # Extract function information
                func_items = self._extract_list_items(functions_section)
                if func_items:
                    for item in func_items:
                        func_info = {"name": "unknown", "purpose": item, "parameters": [], "return_value": ""}
                        # Try to extract function name
                        name_match = re.search(r'`([^`]+)`|"([^"]+)"|\'([^\']+)\'', item)
                        if name_match:
                            func_name = next(filter(None, name_match.groups()))
                            func_info["name"] = func_name
                        analysis_data["functions"]["important_functions"].append(func_info)
        
        # Extract classes information
        if "class" in analysis_text.lower():
            classes_section = self._extract_section(analysis_text, "class")
            if classes_section:
                # Try to extract class count
                count_match = re.search(r'(\d+)\s+classes?', classes_section.lower())
                if count_match:
                    analysis_data["classes"]["count"] = int(count_match.group(1))
                
                # Extract class information
                class_items = self._extract_list_items(classes_section)
                if class_items:
                    for item in class_items:
                        class_info = {"name": "unknown", "purpose": item, "properties": [], "methods": []}
                        # Try to extract class name
                        name_match = re.search(r'`([^`]+)`|"([^"]+)"|\'([^\']+)\'', item)
                        if name_match:
                            class_name = next(filter(None, name_match.groups()))
                            class_info["name"] = class_name
                        analysis_data["classes"]["important_classes"].append(class_info)
        
        # Extract external API communications
        if "api" in analysis_text.lower() or "external" in analysis_text.lower():
            api_section = self._extract_section(analysis_text, "api")
            if api_section:
                api_items = self._extract_list_items(api_section)
                if api_items:
                    for item in api_items:
                        api_info = {"name": "unknown", "purpose": item, "method": ""}
                        # Try to extract API name/endpoint
                        name_match = re.search(r'`([^`]+)`|"([^"]+)"|\'([^\']+)\'', item)
                        if name_match:
                            api_name = next(filter(None, name_match.groups()))
                            api_info["name"] = api_name
                        analysis_data["external_communications"]["apis"].append(api_info)
        
        # Extract data transformations
        if "transformation" in analysis_text.lower():
            transform_section = self._extract_section(analysis_text, "transformation")
            if transform_section:
                transform_items = self._extract_list_items(transform_section)
                if transform_items:
                    for item in transform_items:
                        transform_info = {"description": item, "input": "", "output": ""}
                        analysis_data["data_transformations"].append(transform_info)
        
        # Extract security information
        if "security" in analysis_text.lower() or "vulnerabilit" in analysis_text.lower():
            security_section = self._extract_section(analysis_text, "security")
            if security_section:
                vulnerabilities = self._extract_list_items(security_section)
                if vulnerabilities:
                    analysis_data["security"]["vulnerabilities"] = vulnerabilities
                
                # Determine severity
                if "high" in security_section.lower() and "severity" in security_section.lower():
                    analysis_data["security"]["severity"] = "high"
                elif "medium" in security_section.lower() and "severity" in security_section.lower():
                    analysis_data["security"]["severity"] = "medium"
        
        # Extract summary
        if "summary" in analysis_text.lower():
            summary_section = self._extract_section(analysis_text, "summary")
            if summary_section:
                # Take the first paragraph after "summary"
                summary = summary_section.strip().split("\n\n")[0]
                if summary:
                    analysis_data["summary"] = summary.strip()
        
        return analysis_data
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """
        Extract a section from the text based on a section name.
        
        Args:
            text: The full text
            section_name: The name of the section to extract
            
        Returns:
            The extracted section text or empty string if not found
        """
        lower_text = text.lower()
        section_name_lower = section_name.lower()
        
        if section_name_lower not in lower_text:
            return ""
        
        # Find the start of the section
        start_idx = lower_text.find(section_name_lower)
        if start_idx == -1:
            return ""
        
        # Find the end of the section (next section or end of text)
        end_idx = len(text)
        
        # Common section headers to look for
        section_headers = ["code quality", "variables", "functions", "classes", 
                          "external communications", "data transformations", 
                          "architecture", "security", "summary", "conclusion", 
                          "recommendation", "strength", "weakness", "api"]
        
        for header in section_headers:
            if header == section_name_lower:
                continue
                
            next_section_idx = lower_text.find(header, start_idx + len(section_name_lower))
            if next_section_idx != -1 and next_section_idx < end_idx:
                end_idx = next_section_idx
        
        # Extract the section
        section_text = text[start_idx:end_idx].strip()
        
        # Remove the section header
        lines = section_text.split("\n")
        if len(lines) > 1:
            return "\n".join(lines[1:]).strip()
        return ""
    
    def _extract_list_items(self, text: str) -> List[str]:
        """
        Extract list items from text, looking for bullet points or numbered lists.
        
        Args:
            text: The text containing list items
            
        Returns:
            List of extracted items
        """
        items = []
        
        # Split by lines
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            
            # Check for bullet points or numbered lists
            if line.startswith("- ") or line.startswith("* "):
                items.append(line[2:].strip())
            elif line.startswith(". "):
                items.append(line[2:].strip())
            elif len(line) >= 3 and line[0].isdigit() and line[1] == "." and line[2] == " ":
                items.append(line[3:].strip())
            elif len(line) >= 4 and line[0].isdigit() and line[1].isdigit() and line[2] == "." and line[3] == " ":
                items.append(line[4:].strip())
        
        return items
    
    def _enhance_analysis(self, analysis_data: Dict[str, Any], content: str, language: str, file_path: str) -> Dict[str, Any]:
        """
        Enhance the analysis with additional metadata.
        
        Args:
            analysis_data: The analysis data from the LLM
            content: The source code content
            language: The programming language of the code
            file_path: The path to the file being analyzed
            
        Returns:
            The enhanced analysis data
        """
        # Add language-specific information
        if language in self.COMMON_FRAMEWORKS:
            detected_frameworks = []
            for framework in self.COMMON_FRAMEWORKS[language]:
                if framework.lower() in content.lower():
                    detected_frameworks.append(framework)
            
            if detected_frameworks:
                analysis_data["detected_frameworks"] = detected_frameworks
        
        # Add file-specific information
        analysis_data["file_path"] = file_path
        analysis_data["file_name"] = os.path.basename(file_path)
        analysis_data["file_extension"] = os.path.splitext(file_path)[1]
        
        # Enhance data transformation analysis
        if "data_transformations" in analysis_data and analysis_data["data_transformations"]:
            self._enhance_data_transformations(analysis_data["data_transformations"], content, language)
        
        return analysis_data
    
    def _enhance_data_transformations(self, transformations: List[Dict[str, Any]], content: str, language: str) -> None:
        """
        Enhance data transformation information by adding more details about the transformations.
        
        Args:
            transformations: List of transformation dictionaries
            content: The source code content
            language: The programming language of the code
        """
        # Add transformation type if not present
        for transform in transformations:
            if "type" not in transform:
                # Try to infer transformation type
                desc = transform.get("description", "").lower()
                
                if "filter" in desc or "where" in desc:
                    transform["type"] = "filter"
                elif "map" in desc or "convert" in desc or "transform" in desc:
                    transform["type"] = "map"
                elif "reduce" in desc or "aggregate" in desc or "sum" in desc:
                    transform["type"] = "reduce"
                elif "sort" in desc or "order" in desc:
                    transform["type"] = "sort"
                elif "join" in desc or "merge" in desc:
                    transform["type"] = "join"
                elif "group" in desc:
                    transform["type"] = "group"
                else:
                    transform["type"] = "other"
    
    def generate_lineage_visualization_data(self, project_analysis: Dict[str, Any], file_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate data for visualizing code lineage.
        
        Args:
            project_analysis: The project structure analysis
            file_analyses: List of file analysis results
            
        Returns:
            Data structure suitable for visualization of code lineage
        """
        # Create nodes for components
        nodes = []
        edges = []
        node_id_map = {}
        
        # Add project as root node
        project_type = project_analysis.get("project_structure", {}).get("project_type", "Unknown Project")
        root_node = {
            "id": "project_root",
            "label": project_type,
            "type": "project",
            "size": 30
        }
        nodes.append(root_node)
        node_id_map["project_root"] = 0  # Index in nodes array
        
        # Add key components as nodes
        components = project_analysis.get("project_structure", {}).get("key_components", [])
        for i, component in enumerate(components):
            component_id = f"component_{i}"
            component_node = {
                "id": component_id,
                "label": component.get("name", f"Component {i}"),
                "type": "component",
                "purpose": component.get("purpose", ""),
                "size": 20
            }
            nodes.append(component_node)
            node_id_map[component_id] = len(nodes) - 1
            
            # Add edge from project to component
            edges.append({
                "source": node_id_map["project_root"],
                "target": node_id_map[component_id],
                "type": "contains"
            })
            
            # Add files for this component
            component_files = component.get("files", [])
            for file_path in component_files:
                # Find the file analysis
                file_analysis = next((f for f in file_analyses if f.get("file") == file_path), None)
                if file_analysis:
                    file_id = f"file_{len(nodes)}"
                    file_node = {
                        "id": file_id,
                        "label": os.path.basename(file_path),
                        "type": "file",
                        "language": file_analysis.get("language", "unknown"),
                        "size": 10
                    }
                    nodes.append(file_node)
                    node_id_map[file_id] = len(nodes) - 1
                    
                    # Add edge from component to file
                    edges.append({
                        "source": node_id_map[component_id],
                        "target": node_id_map[file_id],
                        "type": "contains"
                    })
        
        # Add data flow connections
        data_flow = project_analysis.get("project_structure", {}).get("data_flow", {})
        sources = data_flow.get("sources", [])
        transformations = data_flow.get("transformations", [])
        sinks = data_flow.get("sinks", [])
        
        # Add data sources
        for i, source in enumerate(sources):
            source_id = f"source_{i}"
            source_node = {
                "id": source_id,
                "label": source if isinstance(source, str) else source.get("name", f"Source {i}"),
                "type": "data_source",
                "size": 15
            }
            nodes.append(source_node)
            node_id_map[source_id] = len(nodes) - 1
            
            # Connect to project
            edges.append({
                "source": node_id_map["project_root"],
                "target": node_id_map[source_id],
                "type": "data_input"
            })
        
        # Add data transformations
        for i, transform in enumerate(transformations):
            transform_id = f"transform_{i}"
            transform_node = {
                "id": transform_id,
                "label": transform if isinstance(transform, str) else transform.get("name", f"Transform {i}"),
                "type": "data_transformation",
                "description": transform.get("description", "") if not isinstance(transform, str) else "",
                "size": 12
            }
            nodes.append(transform_node)
            node_id_map[transform_id] = len(nodes) - 1
            
            # Connect to previous node if available
            if i > 0:
                prev_transform_id = f"transform_{i-1}"
                edges.append({
                    "source": node_id_map[prev_transform_id],
                    "target": node_id_map[transform_id],
                    "type": "data_flow"
                })
            elif sources:
                # Connect to first source
                source_id = f"source_0"
                edges.append({
                    "source": node_id_map[source_id],
                    "target": node_id_map[transform_id],
                    "type": "data_flow"
                })
        
        # Add data sinks
        for i, sink in enumerate(sinks):
            sink_id = f"sink_{i}"
            sink_node = {
                "id": sink_id,
                "label": sink if isinstance(sink, str) else sink.get("name", f"Sink {i}"),
                "type": "data_sink",
                "size": 15
            }
            nodes.append(sink_node)
            node_id_map[sink_id] = len(nodes) - 1
            
            # Connect from last transformation or source
            if transformations:
                last_transform_id = f"transform_{len(transformations)-1}"
                edges.append({
                    "source": node_id_map[last_transform_id],
                    "target": node_id_map[sink_id],
                    "type": "data_flow"
                })
            elif sources:
                # Connect from first source
                source_id = f"source_0"
                edges.append({
                    "source": node_id_map[source_id],
                    "target": node_id_map[sink_id],
                    "type": "data_flow"
                })
        
        # Add dependencies
        dependencies = project_analysis.get("project_structure", {}).get("dependencies", [])
        for i, dep in enumerate(dependencies):
            dep_name = dep if isinstance(dep, str) else dep.get("name", f"Dependency {i}")
            dep_id = f"dependency_{i}"
            dep_node = {
                "id": dep_id,
                "label": dep_name,
                "type": "dependency",
                "purpose": dep.get("purpose", "") if not isinstance(dep, str) else "",
                "dep_type": dep.get("type", "library") if not isinstance(dep, str) else "library",
                "size": 8
            }
            nodes.append(dep_node)
            node_id_map[dep_id] = len(nodes) - 1
            
            # Connect to project
            edges.append({
                "source": node_id_map["project_root"],
                "target": node_id_map[dep_id],
                "type": "depends_on"
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "project_type": project_type,
                "main_languages": project_analysis.get("project_structure", {}).get("main_languages", []),
                "architecture": project_analysis.get("project_structure", {}).get("architecture", "Unknown"),
                "summary": project_analysis.get("project_structure", {}).get("summary", "")
            }
        }
    
    def generate_code_lineage_metadata(self, project_analysis: Dict[str, Any], file_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive code lineage metadata for export.
        
        Args:
            project_analysis: The project structure analysis
            file_analyses: List of file analysis results
            
        Returns:
            Structured lineage metadata
        """
        # Extract project structure information
        project_structure = project_analysis.get("project_structure", {})
        
        # Build comprehensive lineage metadata
        lineage = {
            "project": {
                "type": project_structure.get("project_type", "Unknown"),
                "architecture": project_structure.get("architecture", "Unknown"),
                "main_languages": project_structure.get("main_languages", []),
                "entry_points": project_structure.get("entry_points", []),
                "summary": project_structure.get("summary", "No summary available")
            },
            "code_lineage": project_structure.get("code_lineage", {
                "purpose": "Unknown",
                "history": "Unknown",
                "organization": "Unknown",
                "complexity": "Unknown"
            }),
            "technical_stack": project_structure.get("technical_stack", {
                "frontend": [],
                "backend": [],
                "database": [],
                "infrastructure": []
            }),
            "dependencies": project_structure.get("dependencies", []),
            "data_flow": project_structure.get("data_flow", {
                "sources": [],
                "transformations": [],
                "sinks": []
            }),
            "components": project_structure.get("key_components", []),
            "legacy_aspects": project_structure.get("legacy_aspects", []),
            "modernization_opportunities": project_structure.get("modernization_opportunities", []),
            "file_analyses": []
        }
        
        # Add file analyses
        for file_analysis in file_analyses:
            if "llm_analysis" not in file_analysis:
                continue
                
            analysis = file_analysis["llm_analysis"]
            file_data = {
                "file_path": file_analysis.get("file", "Unknown"),
                "language": file_analysis.get("language", "unknown"),
                "summary": analysis.get("summary", "No summary available"),
                "functions": analysis.get("functions", {}).get("important_functions", []),
                "classes": analysis.get("classes", {}).get("important_classes", []),
                "data_transformations": analysis.get("data_transformations", []),
                "external_communications": analysis.get("external_communications", {})
            }
            lineage["file_analyses"].append(file_data)
        
        # Add timestamp and metadata
        lineage["metadata"] = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files_analyzed": len(file_analyses),
            "file_stats": project_structure.get("file_stats", {})
        }
        
        return lineage
    
    def _extract_main_languages(self, file_info: List[str]) -> List[str]:
        """Extract the main languages used in the project based on file extensions."""
        languages = {}
        pattern = r"\((.*?)\)$"
        
        for file in file_info:
            match = re.search(pattern, file)
            if match:
                lang = match.group(1)
                languages[lang] = languages.get(lang, 0) + 1
        
        # Sort by frequency and return top languages
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in sorted_langs[:5]]  # Return top 5 languages
