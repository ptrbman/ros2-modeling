#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <input_spec.json> <output_model.xml>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_JSON="$1"
OUTPUT_XML="$2"

if [[ ! -f "$INPUT_JSON" ]]; then
    echo "ERROR: Spec not found: $INPUT_JSON"
    exit 1
fi

UPPAAL_TEMPLATE_PATH="$SCRIPT_DIR/multisrc_v2.xml" \
    python3 "$SCRIPT_DIR/generate_xml_multisrc_v2.py" "$INPUT_JSON" "$OUTPUT_XML"

echo "Generated: $OUTPUT_XML"
