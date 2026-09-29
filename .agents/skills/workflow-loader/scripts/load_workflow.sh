#!/bin/bash

# Default values
AGENT=""
WORKFLOW=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --agent) AGENT="$2"; shift ;;
        --workflow) WORKFLOW="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$AGENT" ] || [ -z "$WORKFLOW" ]; then
    echo "Usage: ./load_workflow.sh --agent {agent_name} --workflow {workflow_name}"
    exit 1
fi

BASE_PATH=".mitra/agents/$AGENT/workflows"
FILENAME="${WORKFLOW}.md"
FILE_PATH="$BASE_PATH/$FILENAME"

# Check if file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "❌ Error: Workflow file not found at $FILE_PATH"
    echo "Available workflows in $BASE_PATH:"
    
    if [ -d "$BASE_PATH" ]; then
        for file in "$BASE_PATH"/*.md; do
            if [ -f "$file" ]; then
                fn=$(basename -- "$file")
                echo " - ${fn%.*}"
            fi
        done
    else
        echo "Directory $BASE_PATH does not exist."
    fi
    exit 1
fi

# Load content
echo ""
# tr instead of ${VAR^^}: macOS ships bash 3.2, which lacks case modification
echo "✅ LOADED WORKFLOW: $(echo "$AGENT" | tr '[:lower:]' '[:upper:]') / $(echo "$WORKFLOW" | tr '[:lower:]' '[:upper:]')"
echo "Source: $FILE_PATH"
echo "========================================"
cat "$FILE_PATH"
echo ""
echo "========================================"
echo ""
echo "INSTRUCTION: Execute the steps above."
