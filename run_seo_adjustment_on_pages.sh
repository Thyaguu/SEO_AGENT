#!/usr/bin/env bash
set -e

# Script directory / Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PATH_HTML=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --Path_html=*)
            PATH_HTML="${1#*=}"
            shift
            ;;
        --Path_html)
            PATH_HTML="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            echo "Usage: ./run_seo_adjustment_on_pages.sh --Path_html=/absolute/path/to/html/repository" >&2
            exit 1
            ;;
    esac
done

# Validate argument presence
if [[ -z "$PATH_HTML" ]]; then
    echo "Error: Missing required argument --Path_html" >&2
    echo "Usage: ./run_seo_adjustment_on_pages.sh --Path_html=/absolute/path/to/html/repository" >&2
    exit 1
fi

# Resolve absolute path
ABS_PATH=$(cd "$PATH_HTML" 2>/dev/null && pwd || echo "$PATH_HTML")

# Validate path existence
if [[ ! -e "$ABS_PATH" ]]; then
    echo "Error: Path does not exist: $PATH_HTML" >&2
    exit 1
fi

# Validate directory
if [[ ! -d "$ABS_PATH" ]]; then
    echo "Error: Path is not a directory: $PATH_HTML" >&2
    exit 1
fi

# Validate HTML files exist
HTML_COUNT=$(find "$ABS_PATH" -maxdepth 2 -name "*.html" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$HTML_COUNT" -eq 0 ]]; then
    echo "Error: Directory contains no HTML files: $PATH_HTML" >&2
    exit 1
fi

# Print required header banner
echo "============================================================"
echo "SEO AGENT"
echo "============================================================"
echo ""
echo "Repository:"
echo "$ABS_PATH"
echo ""

# Execute existing workflow
PYTHONPATH="$SCRIPT_DIR" python3 -m seo_agent.cli --Path_html="$ABS_PATH"
