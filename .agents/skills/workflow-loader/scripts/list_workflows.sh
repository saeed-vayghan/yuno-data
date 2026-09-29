#!/bin/bash

# Default values
AGENT=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --agent) AGENT="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$AGENT" ]; then
    echo "Usage: ./list_workflows.sh --agent {agent_name}"
    exit 1
fi

BASE_PATH=".mitra/agents/$AGENT/workflows"

if [ ! -d "$BASE_PATH" ]; then
    echo "❌ Agent directory not found: $BASE_PATH"
    exit 1
fi

# tr instead of ${VAR^}: macOS ships bash 3.2, which lacks case modification
echo "📂 Available Workflows for $(echo "${AGENT:0:1}" | tr '[:lower:]' '[:upper:]')${AGENT:1}:"
echo "------------------------------"

found=false
for file in "$BASE_PATH"/*.md; do
    if [ -f "$file" ]; then
        filename=$(basename -- "$file")
        if [ "$filename" != "memory-manager.md" ]; then
            name="${filename%.*}"
            echo "* $name"
            found=true
        fi
    fi
done

if [ "$found" = false ]; then
    echo "(No workflows found)"
fi

echo "------------------------------"
