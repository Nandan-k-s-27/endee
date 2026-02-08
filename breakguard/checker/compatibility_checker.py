"""
BreakGuard - Compatibility Checker
Compares user code API calls against the new API version using vector similarity.
"""

import os
from endee import Endee
from embeddings.embedding_engine import EmbeddingEngine


# ─── Configuration ──────────────────────────────────────────────
ENDEE_BASE_URL = os.getenv("ENDEE_URL", "http://localhost:8080/api/v1")


def get_auth_token() -> str:
    """Return the auth token from supported environment variables."""
    return os.getenv("ENDEE_AUTH_TOKEN") or os.getenv("NDD_AUTH_TOKEN", "")


ENDEE_AUTH_TOKEN = get_auth_token()
INDEX_NAME = "api_versions"

# Similarity thresholds
BREAKING_THRESHOLD = 0.85   # Below this = breaking change
MINOR_THRESHOLD = 0.95      # Below this = minor change, above = compatible


# ─── Migration Guides ──────────────────────────────────────────
MIGRATION_GUIDES = {
    "ReactDOM.render": {
        "18": {
            "replacement": "createRoot",
            "guide": """
  Replace ReactDOM.render() with createRoot().render():

  BEFORE (React 17):
    import ReactDOM from 'react-dom';
    ReactDOM.render(<App />, document.getElementById('root'));

  AFTER (React 18):
    import { createRoot } from 'react-dom/client';
    const root = createRoot(document.getElementById('root'));
    root.render(<App />);

  Reference: https://react.dev/blog/2022/03/08/react-18-upgrade-guide
""",
        }
    },
    "ReactDOM.hydrate": {
        "18": {
            "replacement": "hydrateRoot",
            "guide": """
  Replace ReactDOM.hydrate() with hydrateRoot():

  BEFORE (React 17):
    import ReactDOM from 'react-dom';
    ReactDOM.hydrate(<App />, document.getElementById('root'));

  AFTER (React 18):
    import { hydrateRoot } from 'react-dom/client';
    hydrateRoot(document.getElementById('root'), <App />);

  Reference: https://react.dev/blog/2022/03/08/react-18-upgrade-guide
""",
        }
    },
    "ReactDOM.unmountComponentAtNode": {
        "18": {
            "replacement": "root.unmount()",
            "guide": """
  Replace ReactDOM.unmountComponentAtNode() with root.unmount():

  BEFORE (React 17):
    import ReactDOM from 'react-dom';
    ReactDOM.unmountComponentAtNode(container);

  AFTER (React 18):
    // Keep a reference to the root
    const root = createRoot(container);
    root.render(<App />);
    // Later, to unmount:
    root.unmount();

  Reference: https://react.dev/blog/2022/03/08/react-18-upgrade-guide
""",
        }
    },
    "ReactDOM.findDOMNode": {
        "18": {
            "replacement": "useRef / createRef",
            "guide": """
  ReactDOM.findDOMNode() is deprecated in StrictMode in React 18.
  Use React.createRef() or useRef() instead:

  BEFORE (React 17):
    class MyComponent extends React.Component {
      componentDidMount() {
        const node = ReactDOM.findDOMNode(this);
      }
    }

  AFTER (React 18):
    class MyComponent extends React.Component {
      constructor(props) {
        super(props);
        this.myRef = React.createRef();
      }
      render() {
        return <div ref={this.myRef} />;
      }
    }
""",
        }
    },
}


class CompatibilityChecker:
    """Checks API compatibility between library versions using semantic similarity."""

    def __init__(self):
        """Initialize the checker with Endee client and embedding engine."""
        if ENDEE_AUTH_TOKEN:
            self.client = Endee(ENDEE_AUTH_TOKEN)
        else:
            self.client = Endee()
        self.client.set_base_url(ENDEE_BASE_URL)
        self.index = self.client.get_index(name=INDEX_NAME)
        self.engine = EmbeddingEngine()

    def check_api(
        self,
        api_call: str,
        old_version: str = "17",
        new_version: str = "18",
        library: str = "react",
    ) -> dict:
        """
        Check if a single API call is compatible with the new version.

        Args:
            api_call: The API function name (e.g., "ReactDOM.render")
            old_version: Current library version
            new_version: Target library version
            library: Library name

        Returns:
            Dictionary with compatibility status, details, and migration info.
        """
        # Build a semantic description
        context = self._build_context(api_call)
        query_vector = self.engine.encode(context)

        # Query Endee for the new version
        new_version_num = int(new_version)
        try:
            results = self.index.query(
                vector=query_vector,
                top_k=5,
                filter=[
                    {"library": library},
                    {"version": new_version_num},
                ],
                include_vectors=False,
            )
        except Exception as e:
            return {
                "status": "error",
                "api": api_call,
                "error": str(e),
            }

        if not results:
            return {
                "status": "breaking_change",
                "old_api": api_call,
                "new_api": "NOT FOUND",
                "similarity": 0.0,
                "message": f"{api_call} has no equivalent in {library} {new_version}",
                "migration": self._get_migration(api_call, new_version),
            }

        best_match = results[0]
        similarity = best_match.get("similarity", 0.0)
        match_meta = best_match.get("meta", {})
        matched_function = match_meta.get("function", "unknown")
        is_deprecated = match_meta.get("deprecated", False)

        # Decision logic
        if is_deprecated or similarity < BREAKING_THRESHOLD:
            return {
                "status": "breaking_change",
                "old_api": api_call,
                "new_api": matched_function,
                "similarity": round(similarity, 4),
                "deprecated": is_deprecated,
                "message": self._get_break_message(api_call, matched_function, match_meta),
                "migration": self._get_migration(api_call, new_version),
                "confidence": round(similarity * 100, 1),
            }
        elif similarity < MINOR_THRESHOLD:
            return {
                "status": "minor_change",
                "old_api": api_call,
                "new_api": matched_function,
                "similarity": round(similarity, 4),
                "message": f"{api_call} has minor behavioral changes in v{new_version}",
                "confidence": round(similarity * 100, 1),
            }
        else:
            return {
                "status": "compatible",
                "api": api_call,
                "matched": matched_function,
                "similarity": round(similarity, 4),
                "confidence": round(similarity * 100, 1),
            }

    def check_project(
        self,
        api_usage: dict,
        old_version: str = "17",
        new_version: str = "18",
        library: str = "react",
    ) -> dict:
        """
        Check compatibility for all API calls in a project.

        Args:
            api_usage: Dict mapping file paths to lists of API calls.
            old_version: Current version.
            new_version: Target version.
            library: Library name.

        Returns:
            Dictionary with breaking_changes, minor_changes, compatible lists.
        """
        breaking_changes = []
        minor_changes = []
        compatible = []
        errors = []

        # Deduplicate API calls across files
        all_calls = set()
        for calls in api_usage.values():
            all_calls.update(calls)

        # Check each unique API call
        results_cache = {}
        for api_call in sorted(all_calls):
            result = self.check_api(api_call, old_version, new_version, library)
            results_cache[api_call] = result

        # Map results back to files
        for file_path, calls in api_usage.items():
            for api_call in calls:
                result = results_cache[api_call]
                if result["status"] == "breaking_change":
                    breaking_changes.append({"file": file_path, **result})
                elif result["status"] == "minor_change":
                    minor_changes.append({"file": file_path, **result})
                elif result["status"] == "error":
                    errors.append({"file": file_path, **result})
                else:
                    compatible.append({"file": file_path, **result})

        return {
            "breaking_changes": breaking_changes,
            "minor_changes": minor_changes,
            "compatible": compatible,
            "errors": errors,
            "summary": {
                "total_apis": len(all_calls),
                "breaking": len([r for r in results_cache.values() if r["status"] == "breaking_change"]),
                "minor": len([r for r in results_cache.values() if r["status"] == "minor_change"]),
                "compatible": len([r for r in results_cache.values() if r["status"] == "compatible"]),
                "errors": len([r for r in results_cache.values() if r["status"] == "error"]),
            },
        }

    def _build_context(self, api_call: str) -> str:
        """Build a semantic context string for an API call."""
        contexts = {
            "ReactDOM.render": "ReactDOM.render: Render a React element into the DOM in the supplied container. Takes element, container, optional callback. Returns void.",
            "ReactDOM.hydrate": "ReactDOM.hydrate: Hydrate server-rendered HTML content with React. Attach event listeners to existing markup. Takes element, container, optional callback.",
            "ReactDOM.unmountComponentAtNode": "ReactDOM.unmountComponentAtNode: Remove a mounted React component from the DOM and clean up event handlers and state.",
            "ReactDOM.findDOMNode": "ReactDOM.findDOMNode: Find the browser DOM node for a mounted React component instance.",
            "ReactDOM.createPortal": "ReactDOM.createPortal: Render children into a DOM node outside the parent component hierarchy.",
            "useState": "useState: Declare a state variable in a functional React component. Returns state value and setter function.",
            "useEffect": "useEffect: Perform side effects in functional components. Runs after render. Accepts cleanup function.",
            "useContext": "useContext: Read and subscribe to context from a React component.",
            "useReducer": "useReducer: Manage complex state logic with a reducer function in React.",
            "useCallback": "useCallback: Memoize a callback function to prevent unnecessary re-renders.",
            "useMemo": "useMemo: Memoize an expensive computation result between re-renders.",
            "useRef": "useRef: Create a mutable ref object that persists across renders.",
            "useLayoutEffect": "useLayoutEffect: Fire effect synchronously after DOM mutations for layout reading.",
            "useImperativeHandle": "useImperativeHandle: Customize ref instance value exposed to parent components.",
            "useDebugValue": "useDebugValue: Display label for custom hooks in React DevTools.",
            "React.Component": "React.Component: Base class for class-based React components with lifecycle methods and state.",
            "React.PureComponent": "React.PureComponent: React component with shallow prop and state comparison for performance.",
            "React.Fragment": "React.Fragment: Group children without adding extra DOM nodes.",
            "React.Suspense": "React.Suspense: Display fallback while waiting for lazy-loaded children.",
            "React.StrictMode": "React.StrictMode: Development tool for highlighting potential problems in React app.",
            "React.createElement": "React.createElement: Create a new React element of the given type with props and children.",
            "React.cloneElement": "React.cloneElement: Clone a React element with merged props.",
            "React.createRef": "React.createRef: Create a ref to attach to React elements for DOM access.",
            "React.forwardRef": "React.forwardRef: Forward ref to a child component.",
            "React.memo": "React.memo: Memoize a component to skip re-rendering when props are unchanged.",
            "React.lazy": "React.lazy: Define a dynamically loaded component for code splitting.",
            "React.createContext": "React.createContext: Create a context for passing data through component tree.",
            "React.Profiler": "React.Profiler: Measure rendering performance of React components.",
            "React.Children.map": "React.Children.map: Iterate over children elements with a function.",
            "React.isValidElement": "React.isValidElement: Check if an object is a valid React element.",
            "createRoot": "createRoot: Create a concurrent React root for rendering. New React 18 API.",
            "hydrateRoot": "hydrateRoot: Create a root for hydrating server-rendered content. New React 18 API.",
        }
        return contexts.get(api_call, f"{api_call}: React API function call")

    def _get_break_message(self, old_api: str, new_api: str, meta: dict) -> str:
        """Generate a breaking change message."""
        if meta.get("deprecated"):
            migrate_to = meta.get("migrateTo", new_api)
            return f"{old_api} is DEPRECATED in the new version. Use {migrate_to} instead."
        replaces = meta.get("replaces", "")
        if replaces:
            return f"{old_api} has been replaced by {new_api}."
        return f"{old_api} has significant changes in the new version (closest match: {new_api})."

    def _get_migration(self, api_call: str, new_version: str) -> str:
        """Get migration guide for an API call."""
        guide_info = MIGRATION_GUIDES.get(api_call, {}).get(new_version, {})
        if guide_info:
            return guide_info.get("guide", "No migration guide available.")
        return "  No specific migration guide available. Check the official documentation."


if __name__ == "__main__":
    # Quick test
    checker = CompatibilityChecker()
    result = checker.check_api("ReactDOM.render", "17", "18")
    print(f"Status: {result['status']}")
    print(f"Details: {result}")
