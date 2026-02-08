#!/usr/bin/env python3
"""
BreakGuard - Semantic API Breaking Change Predictor
Main CLI Entry Point

Usage:
    python breakguard.py <project_path> [--from VERSION] [--to VERSION] [--library NAME]

Examples:
    python breakguard.py ./my-react-app --from 17 --to 18
    python breakguard.py ./src --from 17 --to 18 --library react
"""

import argparse
import os
import sys
import json
import time

# ─── ANSI Color Codes (Windows compatible) ──────────────────────
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE
    BOLD = Style.BRIGHT
    RESET = Style.RESET_ALL
except ImportError:
    RED = ""
    GREEN = ""
    YELLOW = ""
    CYAN = ""
    WHITE = ""
    BOLD = ""
    RESET = ""


def print_banner():
    """Print the BreakGuard banner."""
    banner = f"""
{CYAN}{BOLD}
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║   ██████╗ ██████╗ ███████╗ █████╗ ██╗  ██╗                  ║
  ║   ██╔══██╗██╔══██╗██╔════╝██╔══██╗██║ ██╔╝                  ║
  ║   ██████╔╝██████╔╝█████╗  ███████║█████╔╝                   ║
  ║   ██╔══██╗██╔══██╗██╔══╝  ██╔══██║██╔═██╗                   ║
  ║   ██████╔╝██║  ██║███████╗██║  ██║██║  ██╗                  ║
  ║   ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝                  ║
  ║                                                              ║
  ║   ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗                  ║
  ║   ██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗                 ║
  ║   ██║  ███╗██║   ██║███████║██████╔╝██║  ██║                 ║
  ║   ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║                 ║
  ║   ╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝                 ║
  ║    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝                  ║
  ║                                                              ║
  ║   Semantic API Breaking Change Predictor                     ║
  ║   Powered by Endee Vector Database                           ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
{RESET}"""
    print(banner)


def print_section(title: str, char: str = "═"):
    """Print a section header."""
    width = 60
    print(f"\n{CYAN}{char * width}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{CYAN}{char * width}{RESET}")


def format_similarity_bar(similarity: float, width: int = 20) -> str:
    """Create a visual similarity bar."""
    filled = int(similarity * width)
    empty = width - filled
    if similarity >= 0.95:
        color = GREEN
    elif similarity >= 0.85:
        color = YELLOW
    else:
        color = RED
    return f"{color}{'█' * filled}{'░' * empty}{RESET} {similarity*100:.1f}%"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BreakGuard: Semantic API Breaking Change Predictor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python breakguard.py ./my-react-app --from 17 --to 18
  python breakguard.py ./src --from 17 --to 18 --json report.json
        """,
    )
    parser.add_argument("path", help="Path to the project directory to scan")
    parser.add_argument(
        "--from",
        dest="old_version",
        default="17",
        help="Current library version (default: 17)",
    )
    parser.add_argument(
        "--to",
        dest="new_version",
        default="18",
        help="Target library version (default: 18)",
    )
    parser.add_argument(
        "--library",
        default="react",
        help="Library to check against (default: react)",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        default=None,
        help="Output results to a JSON file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for breaking changes (default: 0.85)",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Skip the banner display",
    )

    args = parser.parse_args()

    # ─── Banner ─────────────────────────────────────────────────
    if not args.no_banner:
        print_banner()

    # ─── Validate Path ──────────────────────────────────────────
    project_path = os.path.abspath(args.path)
    if not os.path.exists(project_path):
        print(f"\n{RED}  Error: Path does not exist: {project_path}{RESET}")
        sys.exit(1)

    # ─── Step 1: Scan Project ───────────────────────────────────
    print_section(
        f"Scanning: {args.library} {args.old_version} -> {args.new_version}"
    )
    print(f"\n  Project path: {project_path}")

    start_time = time.time()

    # Import analyzer
    from analyzer.code_analyzer import scan_project, get_api_call_locations

    print(f"  Scanning for {args.library} API calls...\n")
    api_usage = scan_project(project_path)

    if not api_usage:
        print(f"\n{YELLOW}  No React API calls found in the project.{RESET}")
        print("  Make sure the path contains .js/.jsx/.ts/.tsx files.")
        sys.exit(0)

    # Display found API calls
    total_calls = sum(len(calls) for calls in api_usage.values())
    unique_calls = set()
    for calls in api_usage.values():
        unique_calls.update(calls)

    print(f"  {GREEN}Found {total_calls} API calls ({len(unique_calls)} unique) in {len(api_usage)} files{RESET}\n")

    for file_path, calls in api_usage.items():
        rel_path = os.path.relpath(file_path, project_path)
        print(f"    {CYAN}{rel_path}{RESET}")
        for call in calls:
            locations = get_api_call_locations(file_path, call)
            loc_str = f" (line{'s' if len(locations)>1 else ''}: {', '.join(map(str, locations))})" if locations else ""
            print(f"      - {call}{loc_str}")

    # ─── Step 2: Check Compatibility ────────────────────────────
    print_section("Compatibility Analysis")
    print(f"\n  Comparing against {args.library} v{args.new_version} in Endee...\n")

    from checker.compatibility_checker import CompatibilityChecker

    checker = CompatibilityChecker()
    results = checker.check_project(
        api_usage, args.old_version, args.new_version, args.library
    )

    scan_time = time.time() - start_time

    # ─── Step 3: Generate Report ────────────────────────────────
    print_section(
        f"BreakGuard Report: {args.library} {args.old_version} -> {args.new_version}"
    )

    summary = results["summary"]

    # Summary bar
    print(f"\n  Total APIs analyzed: {BOLD}{summary['total_apis']}{RESET}")
    print(f"  {RED}Breaking changes: {summary['breaking']}{RESET}")
    print(f"  {YELLOW}Minor changes:    {summary['minor']}{RESET}")
    print(f"  {GREEN}Compatible:       {summary['compatible']}{RESET}")
    if "errors" in summary and summary["errors"]:
        print(f"  {RED}Errors:           {summary['errors']}{RESET}")
    print(f"  Scan time:        {scan_time:.2f}s")

    # ─── Breaking Changes ───────────────────────────────────────
    if results["breaking_changes"]:
        print(f"\n{'─' * 60}")
        print(f"  {RED}{BOLD}BREAKING CHANGES ({len(results['breaking_changes'])}){RESET}")
        print(f"{'─' * 60}")

        # Group by unique API
        seen = set()
        for change in results["breaking_changes"]:
            api = change["old_api"]
            if api in seen:
                continue
            seen.add(api)

            print(f"\n  {RED}✗{RESET} {BOLD}{api}{RESET}")
            print(f"    Status:     {RED}BREAKING CHANGE{RESET}")
            if "new_api" in change:
                print(f"    Replaced by: {GREEN}{change['new_api']}{RESET}")
            if "confidence" in change:
                print(f"    Similarity:  {format_similarity_bar(change['similarity'])}")
            if "message" in change:
                print(f"    Message:     {change['message']}")

            # Show affected files
            affected = [
                c for c in results["breaking_changes"] if c["old_api"] == api
            ]
            print(f"    Affected files ({len(affected)}):")
            for item in affected:
                rel = os.path.relpath(item["file"], project_path)
                locations = get_api_call_locations(item["file"], api)
                loc = f":{locations[0]}" if locations else ""
                print(f"      - {CYAN}{rel}{loc}{RESET}")

            # Migration guide
            migration = change.get("migration", "")
            if migration and migration.strip() != "No specific migration guide available. Check the official documentation.":
                print(f"\n    {GREEN}Migration Guide:{RESET}")
                for line in migration.strip().split("\n"):
                    print(f"    {line}")

    # ─── Minor Changes ──────────────────────────────────────────
    if results["minor_changes"]:
        print(f"\n{'─' * 60}")
        print(f"  {YELLOW}{BOLD}MINOR CHANGES ({len(results['minor_changes'])}){RESET}")
        print(f"{'─' * 60}")

        seen = set()
        for change in results["minor_changes"]:
            api = change["old_api"]
            if api in seen:
                continue
            seen.add(api)

            print(f"\n  {YELLOW}~{RESET} {BOLD}{api}{RESET}")
            print(f"    Status:    {YELLOW}Review recommended{RESET}")
            print(f"    Similarity: {format_similarity_bar(change['similarity'])}")
            if "message" in change:
                print(f"    Note:      {change['message']}")

    # ─── Errors ───────────────────────────────────────────────
    if results.get("errors"):
        print(f"\n{'─' * 60}")
        print(f"  {RED}{BOLD}ERRORS ({len(results['errors'])}){RESET}")
        print(f"{'─' * 60}")
        for item in results["errors"]:
            rel = os.path.relpath(item["file"], project_path)
            print(f"\n  {RED}!{RESET} {item.get('api', item.get('old_api', 'unknown'))}")
            print(f"    File: {CYAN}{rel}{RESET}")
            print(f"    Error: {item.get('error', 'Unknown error')}")

    # ─── Compatible ─────────────────────────────────────────────
    if results["compatible"]:
        print(f"\n{'─' * 60}")
        print(f"  {GREEN}{BOLD}COMPATIBLE ({len(results['compatible'])}){RESET}")
        print(f"{'─' * 60}")

        seen = set()
        for item in results["compatible"]:
            api = item.get("api", item.get("old_api", "unknown"))
            if api in seen:
                continue
            seen.add(api)
            sim = item.get("similarity", 1.0)
            print(f"  {GREEN}✓{RESET} {api}  {format_similarity_bar(sim)}")

    # ─── Final Summary ──────────────────────────────────────────
    print(f"\n{'═' * 60}")
    if summary["breaking"] > 0:
        print(f"  {RED}{BOLD}Result: {summary['breaking']} breaking change(s) detected!{RESET}")
        print(f"  {YELLOW}Action required before upgrading to {args.library} {args.new_version}.{RESET}")
    elif summary.get("errors", 0) > 0:
        print(f"  {RED}{BOLD}Result: {summary['errors']} error(s) occurred during analysis.{RESET}")
        print(f"  {YELLOW}Resolve the errors and re-run the scan.{RESET}")
    elif summary["minor"] > 0:
        print(f"  {YELLOW}{BOLD}Result: {summary['minor']} minor change(s) to review.{RESET}")
        print(f"  {GREEN}Upgrade is mostly safe, review the flagged items.{RESET}")
    else:
        print(f"  {GREEN}{BOLD}Result: All APIs are compatible!{RESET}")
        print(f"  {GREEN}Safe to upgrade to {args.library} {args.new_version}.{RESET}")
    print(f"{'═' * 60}\n")

    # ─── JSON Output ────────────────────────────────────────────
    if args.json_output:
        output = {
            "library": args.library,
            "from_version": args.old_version,
            "to_version": args.new_version,
            "project_path": project_path,
            "scan_time_seconds": round(scan_time, 2),
            "summary": summary,
            "breaking_changes": results["breaking_changes"],
            "minor_changes": results["minor_changes"],
            "errors": results.get("errors", []),
            "compatible": results["compatible"],
        }
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"  Report saved to: {args.json_output}\n")


if __name__ == "__main__":
    main()
