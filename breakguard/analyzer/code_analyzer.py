"""
BreakGuard - Code Analyzer
Parses JavaScript/JSX files and extracts React API calls using AST analysis.
"""

import os
import re
import json

try:
    import esprima
    HAS_ESPRIMA = True
except ImportError:
    HAS_ESPRIMA = False


# ─── Known React API patterns ──────────────────────────────────
REACT_HOOKS = {
    "useState", "useEffect", "useContext", "useReducer",
    "useCallback", "useMemo", "useRef", "useImperativeHandle",
    "useLayoutEffect", "useDebugValue", "useId", "useTransition",
    "useDeferredValue", "useInsertionEffect", "useSyncExternalStore",
}

REACT_MEMBER_APIS = {
    "ReactDOM": {
        "render", "hydrate", "unmountComponentAtNode",
        "findDOMNode", "createPortal", "flushSync",
    },
    "React": {
        "createElement", "cloneElement", "createRef",
        "forwardRef", "memo", "lazy", "createContext",
        "isValidElement", "startTransition",
    },
}

REACT_COMPONENT_APIS = {
    "React.Component", "React.PureComponent", "React.Fragment",
    "React.Suspense", "React.StrictMode", "React.Profiler",
}

REACT_IMPORTS = {
    "createRoot", "hydrateRoot",
}


def extract_api_calls_ast(file_path: str) -> list:
    """
    Extract React API calls from a JavaScript/JSX file using AST parsing.

    Args:
        file_path: Path to the JS/JSX file.

    Returns:
        List of API call strings found in the file.
    """
    if not HAS_ESPRIMA:
        return extract_api_calls_regex(file_path)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    api_calls = set()

    try:
        ast = esprima.parseScript(code, {"jsx": True, "tolerant": True})
    except Exception:
        try:
            ast = esprima.parseModule(code, {"jsx": True, "tolerant": True})
        except Exception:
            # Fall back to regex if AST parsing fails
            return extract_api_calls_regex(file_path)

    def walk(node):
        """Recursively walk the AST to find API usage patterns."""
        if isinstance(node, dict):
            node_type = node.get("type", "")

            # ── MemberExpression: ReactDOM.render, React.createElement ──
            if node_type == "MemberExpression":
                obj = node.get("object", {})
                prop = node.get("property", {})
                obj_name = obj.get("name", "")
                prop_name = prop.get("name", "")

                if obj_name in REACT_MEMBER_APIS:
                    full_name = f"{obj_name}.{prop_name}"
                    if prop_name in REACT_MEMBER_APIS[obj_name]:
                        api_calls.add(full_name)

                # React.Children.map
                if obj_name == "React" and prop_name == "Children":
                    api_calls.add("React.Children.map")

            # ── CallExpression: useState(), useEffect(), etc. ──
            if node_type == "CallExpression":
                callee = node.get("callee", {})
                callee_name = callee.get("name", "")

                if callee_name in REACT_HOOKS:
                    api_calls.add(callee_name)
                if callee_name in REACT_IMPORTS:
                    api_calls.add(callee_name)

            # ── ClassDeclaration: extends React.Component ──
            if node_type == "ClassDeclaration":
                superclass = node.get("superClass", {})
                if isinstance(superclass, dict):
                    obj = superclass.get("object", {})
                    prop = superclass.get("property", {})
                    if obj.get("name") == "React" and prop.get("name") in (
                        "Component",
                        "PureComponent",
                    ):
                        api_calls.add(f"React.{prop['name']}")

            # ── JSXElement: <React.Fragment>, <React.StrictMode> ──
            if node_type == "JSXMemberExpression":
                obj = node.get("object", {})
                prop = node.get("property", {})
                if obj.get("name") == "React":
                    comp_name = f"React.{prop.get('name', '')}"
                    if comp_name in REACT_COMPONENT_APIS:
                        api_calls.add(comp_name)

            # ── ImportDeclaration: track imports ──
            if node_type == "ImportDeclaration":
                source = node.get("source", {}).get("value", "")
                specifiers = node.get("specifiers", [])
                for spec in specifiers:
                    if isinstance(spec, dict):
                        imported = spec.get("imported", {})
                        local = spec.get("local", {})
                        name = imported.get("name", "") or local.get("name", "")
                        if name in REACT_IMPORTS:
                            api_calls.add(name)
                        if name in REACT_HOOKS:
                            api_calls.add(name)

            # Recurse into child nodes
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(ast.toDict() if hasattr(ast, "toDict") else ast)
    return sorted(list(api_calls))


def extract_api_calls_regex(file_path: str) -> list:
    """
    Fallback: Extract React API calls using regex pattern matching.
    Used when esprima is not available or AST parsing fails.

    Args:
        file_path: Path to the JS/JSX file.

    Returns:
        List of API call strings found in the file.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    api_calls = set()

    # Match ReactDOM.method() calls
    reactdom_pattern = r"ReactDOM\.(render|hydrate|unmountComponentAtNode|findDOMNode|createPortal|flushSync)\s*\("
    for match in re.finditer(reactdom_pattern, code):
        api_calls.add(f"ReactDOM.{match.group(1)}")

    # Match React.method() calls
    react_pattern = r"React\.(createElement|cloneElement|createRef|forwardRef|memo|lazy|createContext|isValidElement|startTransition)\s*[\(\<]"
    for match in re.finditer(react_pattern, code):
        api_calls.add(f"React.{match.group(1)}")

    # Match React hooks
    hooks_pattern = r"\b(useState|useEffect|useContext|useReducer|useCallback|useMemo|useRef|useImperativeHandle|useLayoutEffect|useDebugValue|useId|useTransition|useDeferredValue|useInsertionEffect|useSyncExternalStore)\s*\("
    for match in re.finditer(hooks_pattern, code):
        api_calls.add(match.group(1))

    # Match createRoot / hydrateRoot
    new_api_pattern = r"\b(createRoot|hydrateRoot)\s*\("
    for match in re.finditer(new_api_pattern, code):
        api_calls.add(match.group(1))

    # Match class extends React.Component / React.PureComponent
    class_pattern = r"extends\s+React\.(Component|PureComponent)"
    for match in re.finditer(class_pattern, code):
        api_calls.add(f"React.{match.group(1)}")

    # Match React.Fragment, React.StrictMode, React.Suspense, React.Profiler
    component_pattern = r"React\.(Fragment|StrictMode|Suspense|Profiler)"
    for match in re.finditer(component_pattern, code):
        api_calls.add(f"React.{match.group(1)}")

    # Match React.Children.map
    if re.search(r"React\.Children\.\w+", code):
        api_calls.add("React.Children.map")

    return sorted(list(api_calls))


def scan_project(project_path: str) -> dict:
    """
    Scan an entire project directory for React API usage.

    Args:
        project_path: Path to the root of the project.

    Returns:
        Dictionary mapping file paths to lists of API calls found.
    """
    results = {}
    skipped = []
    supported_extensions = {".js", ".jsx", ".tsx", ".ts", ".mjs"}

    # Directories to skip
    skip_dirs = {"node_modules", ".git", "dist", "build", "__pycache__", ".next"}

    for root, dirs, files in os.walk(project_path):
        # Remove skip directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            _, ext = os.path.splitext(file)
            if ext.lower() in supported_extensions:
                file_path = os.path.join(root, file)
                try:
                    calls = extract_api_calls_ast(file_path)
                    if calls:
                        results[file_path] = calls
                except Exception as e:
                    skipped.append((file_path, str(e)))

    return results


def get_api_call_locations(file_path: str, api_call: str) -> list:
    """
    Find the line numbers where a specific API call appears in a file.

    Args:
        file_path: Path to the file.
        api_call: The API call to search for (e.g., "ReactDOM.render").

    Returns:
        List of line numbers (1-indexed) where the call appears.
    """
    locations = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                # Check for the API call in the line
                if api_call in line:
                    locations.append(line_num)
                # Also check individual parts for member expressions
                elif "." in api_call:
                    parts = api_call.split(".")
                    if all(part in line for part in parts):
                        locations.append(line_num)
    except Exception:
        pass

    return locations


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python code_analyzer.py <project_path>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Scanning: {path}\n")

    results = scan_project(path)
    for file_path, calls in results.items():
        print(f"  {file_path}:")
        for call in calls:
            locations = get_api_call_locations(file_path, call)
            loc_str = f" (lines: {locations})" if locations else ""
            print(f"    - {call}{loc_str}")

    total = sum(len(calls) for calls in results.values())
    print(f"\nTotal: {total} API calls in {len(results)} files")
