"""
Python code analyzer module for analyzing Python source code.
"""

import ast
import os
from typing import Dict, List, Any, Optional
from enum import Enum
import re


class IssueSeverity(Enum):
    """Enum representing the severity of code issues."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Issue:
    """Class representing a code issue."""
    
    def __init__(self, file: str, line: int, message: str, 
                 severity: IssueSeverity, category: str, recommendation: str = ""):
        self.file = file
        self.line = line
        self.message = message
        self.severity = severity
        self.category = category
        self.recommendation = recommendation


class PythonAnalyzer:
    """
    Analyzer for Python source code that extracts metrics and structure information.
    """
    
    def __init__(self, content: str, file_path: str):
        self.content = content
        self.file_path = file_path
        self.tree = None
        try:
            self.tree = ast.parse(content)
        except SyntaxError as e:
            # Handle syntax errors gracefully
            pass
        
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze the Python code and extract metrics.
            
        Returns:
            Dictionary containing analysis results
        """
        if not self.tree:
            return self._create_error_metrics("Failed to parse Python code")
        
        # Count various code elements
        functions = self._count_functions()
        classes = self._count_classes()
        lines = self._count_lines()
        imports = self._extract_imports()
        complexity = self._calculate_complexity()
        
        # Calculate additional metrics
        cognitive_complexity = self._calculate_cognitive_complexity()
        docstring_coverage = self._calculate_docstring_coverage()
        maintainability = self._calculate_maintainability()
        
        # Build the metrics dictionary
        metrics = {
            "file_info": {
                "path": self.file_path,
                "name": os.path.basename(self.file_path),
                "extension": ".py",
                "language": "Python"
            },
            "size": {
                "lines_total": lines["total"],
                "lines_code": lines["code"],
                "lines_comment": lines["comments"],
                "lines_blank": lines["blank"]
            },
            "structure": {
                "functions": functions,
                "classes": classes,
                "imports": len(imports),
                "import_names": imports
            },
            "complexity": {
                "cyclomatic": complexity["total_complexity"],
                "cognitive": cognitive_complexity,
                "if_statements": complexity["if_statements"],
                "loops": complexity["for_loops"] + complexity["while_loops"]
            },
            "documentation": {
                "docstring_coverage": docstring_coverage,
                "comment_ratio": lines["comments"] / max(lines["code"], 1) * 100
            },
            "maintainability": {
                "score": maintainability["score"],
                "debt_ratio": maintainability["debt_ratio"]
            }
        }
        
        return metrics
    
    def _count_functions(self) -> int:
        """Count the number of function definitions in the AST."""
        if not self.tree:
            return 0
        return len([node for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef)])
    
    def _count_classes(self) -> int:
        """Count the number of class definitions in the AST."""
        if not self.tree:
            return 0
        return len([node for node in ast.walk(self.tree) if isinstance(node, ast.ClassDef)])
    
    def _count_lines(self) -> Dict[str, int]:
        """Count different types of lines in the code."""
        if not self.content:
            return {"total": 0, "code": 0, "comments": 0, "blank": 0}
        
        lines = self.content.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        
        # Simple heuristic for comment lines
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        
        # Code lines are those that are neither blank nor comments
        code_lines = total_lines - blank_lines - comment_lines
        
        return {
            "total": total_lines,
            "code": code_lines,
            "comments": comment_lines,
            "blank": blank_lines
        }
    
    def _extract_imports(self) -> List[str]:
        """Extract all import statements from the AST."""
        if not self.tree:
            return []
            
        imports = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for name in node.names:
                    imports.append(f"{module}.{name.name}")
        
        return imports
    
    def _calculate_complexity(self) -> Dict[str, int]:
        """Calculate complexity metrics for the code."""
        if not self.tree:
            return {"if_statements": 0, "for_loops": 0, "while_loops": 0, "total_complexity": 0}
            
        # Count control flow statements as a simple complexity metric
        if_statements = len([node for node in ast.walk(self.tree) if isinstance(node, ast.If)])
        for_loops = len([node for node in ast.walk(self.tree) if isinstance(node, ast.For)])
        while_loops = len([node for node in ast.walk(self.tree) if isinstance(node, ast.While)])
        
        # Count additional complexity factors
        try_except = len([node for node in ast.walk(self.tree) if isinstance(node, ast.Try)])
        boolean_ops = len([node for node in ast.walk(self.tree) if isinstance(node, ast.BoolOp)])
        
        total_complexity = if_statements + for_loops + while_loops + try_except + boolean_ops
        
        return {
            "if_statements": if_statements,
            "for_loops": for_loops,
            "while_loops": while_loops,
            "try_except": try_except,
            "boolean_ops": boolean_ops,
            "total_complexity": total_complexity
        }
    
    def _calculate_cognitive_complexity(self) -> float:
        """Calculate cognitive complexity of the code."""
        if not self.tree:
            return 0.0
            
        # A simplified cognitive complexity calculation
        # Nested control structures increase complexity more
        complexity = 0
        nesting_level = 0
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Add base complexity for each function/class
                complexity += 1
                
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                # Add complexity based on nesting level
                complexity += 1 + nesting_level
                nesting_level += 1
                
            # Reset nesting level after function/class definition
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                nesting_level = 0
        
        return float(complexity)
    
    def _calculate_docstring_coverage(self) -> float:
        """Calculate the percentage of functions and classes that have docstrings."""
        if not self.tree:
            return 0.0
            
        functions = [node for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(self.tree) if isinstance(node, ast.ClassDef)]
        
        total_items = len(functions) + len(classes)
        if total_items == 0:
            return 100.0  # No functions or classes, so coverage is perfect
            
        items_with_docstring = 0
        
        for node in functions + classes:
            if ast.get_docstring(node):
                items_with_docstring += 1
                
        return (items_with_docstring / total_items) * 100
    
    def _calculate_maintainability(self) -> Dict[str, float]:
        """Calculate maintainability metrics."""
        if not self.tree:
            return {"score": 0.0, "debt_ratio": 100.0}
            
        # Calculate maintainability index (simplified version)
        # Higher is better, scale 0-100
        lines = self._count_lines()
        complexity = self._calculate_complexity()
        
        # Simplified maintainability index formula
        volume = lines["code"] * (complexity["total_complexity"] / max(1, self._count_functions() + self._count_classes()))
        maintainability_index = max(0, min(100, 100 - volume / 10))
        
        # Calculate technical debt ratio (higher is worse)
        debt_ratio = 0.0
        
        # Factors that contribute to technical debt
        if lines["code"] > 0:
            # Low comment ratio increases debt
            comment_ratio = lines["comments"] / lines["code"]
            if comment_ratio < 0.1:
                debt_ratio += 20.0
            
            # High complexity increases debt
            if complexity["total_complexity"] / max(1, lines["code"]) > 0.1:
                debt_ratio += 20.0
            
            # Low docstring coverage increases debt
            docstring_coverage = self._calculate_docstring_coverage()
            if docstring_coverage < 50:
                debt_ratio += 20.0
            
            # Long functions increase debt
            long_functions = 0
            for node in ast.walk(self.tree):
                if isinstance(node, ast.FunctionDef):
                    if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                        if node.end_lineno - node.lineno > 30:
                            long_functions += 1
            
            if long_functions > 0:
                debt_ratio += 20.0 * (long_functions / max(1, self._count_functions()))
        
        # Cap debt ratio at 100%
        debt_ratio = min(100.0, debt_ratio)
        
        return {
            "score": maintainability_index,
            "debt_ratio": debt_ratio
        }
        
    def detect_issues(self) -> List[Issue]:
        """Detect potential issues in the code and return a list of Issue objects."""
        issues = []
        
        if not self.tree:
            return [Issue(
                self.file_path, 
                1, 
                "Failed to parse Python code", 
                IssueSeverity.HIGH, 
                "Syntax",
                "Fix the syntax errors in the file to enable proper analysis."
            )]
            
        # Check for long functions (more than 50 lines)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    func_lines = node.end_lineno - node.lineno
                    if func_lines > 50:
                        issues.append(Issue(
                            self.file_path,
                            node.lineno,
                            f"Function '{node.name}' is too long ({func_lines} lines)",
                            IssueSeverity.MEDIUM,
                            "Maintainability",
                            "Consider breaking this function into smaller, more focused functions."
                        ))
        
        # Check for too many arguments in functions (more than 5)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                arg_count = len(node.args.args)
                if arg_count > 5:
                    issues.append(Issue(
                        self.file_path,
                        node.lineno,
                        f"Function '{node.name}' has too many arguments ({arg_count})",
                        IssueSeverity.MEDIUM,
                        "Design",
                        "Consider grouping related parameters into a class or using keyword arguments."
                    ))
        
        # Check for missing docstrings in functions and classes
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    node_type = "class" if isinstance(node, ast.ClassDef) else "function"
                    issues.append(Issue(
                        self.file_path,
                        node.lineno,
                        f"Missing docstring in {node_type} '{node.name}'",
                        IssueSeverity.LOW,
                        "Documentation",
                        f"Add a docstring to describe what this {node_type} does."
                    ))
        
        # Check for overly complex functions
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                # Count complexity factors within this function
                if_statements = len([n for n in ast.walk(node) if isinstance(n, ast.If)])
                loops = len([n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While))])
                try_except = len([n for n in ast.walk(node) if isinstance(n, ast.Try)])
                
                complexity = if_statements + loops + try_except
                if complexity > 10:
                    issues.append(Issue(
                        self.file_path,
                        node.lineno,
                        f"Function '{node.name}' is too complex (complexity: {complexity})",
                        IssueSeverity.HIGH,
                        "Complexity",
                        "Refactor this function to reduce its complexity by extracting logic into helper functions."
                    ))
        
        # Check for potential bugs
        for node in ast.walk(self.tree):
            # Check for empty except blocks
            if isinstance(node, ast.ExceptHandler):
                if not node.body or all(isinstance(n, ast.Pass) for n in node.body):
                    issues.append(Issue(
                        self.file_path,
                        node.lineno,
                        "Empty except block",
                        IssueSeverity.HIGH,
                        "Error Handling",
                        "Empty except blocks hide errors. Either handle the exception properly or log it."
                    ))
            
            # Check for mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(Issue(
                            self.file_path,
                            node.lineno,
                            f"Mutable default argument in function '{node.name}'",
                            IssueSeverity.MEDIUM,
                            "Bug Risk",
                            "Using mutable objects as default arguments can lead to unexpected behavior. Use None instead."
                        ))
        
        return issues
        
    def _detect_issues(self) -> List[Dict[str, Any]]:
        """Detect potential issues in the code."""
        issues = []
        
        if not self.tree:
            return issues
            
        # Check for long functions (more than 50 lines)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    func_lines = node.end_lineno - node.lineno
                    if func_lines > 50:
                        issues.append({
                            "type": "long_function",
                            "message": f"Function '{node.name}' is too long ({func_lines} lines)",
                            "line": node.lineno,
                            "severity": "warning"
                        })
        
        # Check for too many arguments in functions (more than 5)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                arg_count = len(node.args.args)
                if arg_count > 5:
                    issues.append({
                        "type": "too_many_args",
                        "message": f"Function '{node.name}' has too many arguments ({arg_count})",
                        "line": node.lineno,
                        "severity": "warning"
                    })
        
        return issues
        
    def _create_error_metrics(self, error_message: str) -> Dict[str, Any]:
        """Create a metrics dictionary for error cases."""
        return {
            "file_info": {
                "path": self.file_path,
                "name": os.path.basename(self.file_path),
                "extension": ".py",
                "language": "Python"
            },
            "size": {
                "lines_total": 0,
                "lines_code": 0,
                "lines_comment": 0,
                "lines_blank": 0
            },
            "structure": {
                "functions": 0,
                "classes": 0,
                "imports": 0,
                "import_names": []
            },
            "complexity": {
                "cyclomatic": 0,
                "cognitive": 0,
                "if_statements": 0,
                "loops": 0
            },
            "documentation": {
                "docstring_coverage": 0,
                "comment_ratio": 0
            },
            "maintainability": {
                "score": 0,
                "debt_ratio": 100
            },
            "issues": [{
                "type": "error",
                "message": error_message,
                "line": 1,
                "severity": "error"
            }]
        }
