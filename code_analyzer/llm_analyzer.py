"""
LLM-based code analyzer module for advanced code analysis across multiple programming languages.
"""

import os
from openai import OpenAI
from typing import Dict, List, Any, Optional, Set
import json
import time
import re

class LLMAnalyzer:
    """
    LLM-powered code analyzer that provides deep insights into code quality,
    architecture, variables, transformations, and external API communications.
    """
    
    # Supported programming languages and their file extensions
    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
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
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM analyzer.
        
        Args:
            api_key: OpenAI API key. If None, will try to use the OPENAI_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = "gpt-4"  # Default to GPT-4 for best code analysis
    
    def detect_language(self, file_path: str, content: str) -> str:
        """
        Detect the programming language based on file extension or content.
        
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
        
        # If extension is not recognized, ask the LLM to identify the language
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a programming language detection expert. Identify the programming language of the given code snippet. Respond with only the language name in lowercase."},
                        {"role": "user", "content": f"Identify the programming language:\n\n```\n{content[:1000]}\n```"}
                    ],
                    temperature=0.1,
                    max_tokens=20
                )
                detected_language = response.choices[0].message.content.strip().lower()
                return detected_language
            except Exception:
                pass
        
        # Default to 'unknown' if detection fails
        return "unknown"
    
    def analyze_code(self, content: str, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze code using an LLM to get advanced insights.
        
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
                    {"role": "system", "content": "You are an expert code analyzer with deep knowledge of all programming languages. Analyze the given code and provide detailed insights about its structure, variables, transformations, external API communications, and quality."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lower temperature for more consistent analysis
                max_tokens=2000
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            
            # Try to extract structured data if the response is in JSON format
            try:
                # Check if the response contains a JSON block
                if "```json" in analysis_text and "```" in analysis_text.split("```json", 1)[1]:
                    json_str = analysis_text.split("```json", 1)[1].split("```", 1)[0]
                    analysis_data = json.loads(json_str)
                else:
                    # Process the text response into structured data
                    analysis_data = self._process_text_analysis(analysis_text)
            except json.JSONDecodeError:
                # Fall back to processing the text response
                analysis_data = self._process_text_analysis(analysis_text)
            
            return {
                "file": file_path,
                "language": language,
                "llm_analysis": analysis_data,
                "raw_response": analysis_text
            }
            
        except Exception as e:
            return {
                "error": f"Error during LLM analysis: {str(e)}",
                "file": file_path
            }
    
    def analyze_project_structure(self, file_paths: List[str], file_contents: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze the overall project structure and generate lineage information.
        
        Args:
            file_paths: List of all file paths in the project
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            Project structure analysis
        """
        if not self.client:
            return {
                "error": "No API key provided. Set the OPENAI_API_KEY environment variable or pass an API key to the constructor."
            }
            
        try:
            # Prepare file list with languages
            file_info = []
            for file_path in file_paths:
                if file_path in file_contents:
                    language = self.detect_language(file_path, file_contents[file_path])
                    file_info.append(f"{file_path} ({language})")
                else:
                    file_info.append(file_path)
            
            # Create a prompt for project structure analysis
            prompt = f"""
Analyze the structure of this project based on the file list below:

File List:
{chr(10).join(file_info[:100])}  # Limit to first 100 files to avoid token limits

{f"(Showing first 100 of {len(file_info)} files)" if len(file_info) > 100 else ""}

Based on these files, provide a comprehensive analysis of the project structure in JSON format:
{{
    "project_type": "<type of project (e.g., web application, API, library, etc.)>",
    "main_languages": [<list of main programming languages used>],
    "architecture": "<architectural pattern identified (e.g., MVC, microservices, etc.)>",
    "entry_points": [<likely entry points or main files>],
    "dependencies": [<identified external dependencies or frameworks>],
    "project_lineage": "<description of the project's purpose, structure, and data flow>",
    "technical_stack": {{
        "frontend": [<frontend technologies>],
        "backend": [<backend technologies>],
        "database": [<database technologies>],
        "infrastructure": [<infrastructure technologies>]
    }},
    "summary": "<overall assessment of the project structure>"
}}

Focus on providing accurate insights about the project's structure, purpose, and technical stack.
"""
            
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert software architect with deep knowledge of project structures across all programming languages and frameworks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            
            # Extract JSON data
            try:
                # Check if the response contains a JSON block
                if "```json" in analysis_text and "```" in analysis_text.split("```json", 1)[1]:
                    json_str = analysis_text.split("```json", 1)[1].split("```", 1)[0]
                    analysis_data = json.loads(json_str)
                else:
                    # Try to parse the entire response as JSON
                    analysis_data = json.loads(analysis_text)
            except json.JSONDecodeError:
                # Create a basic structure if JSON parsing fails
                analysis_data = {
                    "project_type": "Unknown",
                    "main_languages": self._extract_main_languages(file_info),
                    "architecture": "Could not determine",
                    "entry_points": [],
                    "dependencies": [],
                    "project_lineage": "Could not generate project lineage from the provided information.",
                    "technical_stack": {
                        "frontend": [],
                        "backend": [],
                        "database": [],
                        "infrastructure": []
                    },
                    "summary": "Analysis could not be completed in structured format. Please see raw response."
                }
            
            return {
                "project_structure": analysis_data,
                "raw_response": analysis_text
            }
            
        except Exception as e:
            return {
                "error": f"Error during project structure analysis: {str(e)}"
            }
    
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
