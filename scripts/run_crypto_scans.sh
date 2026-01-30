#!/bin/bash
# DEPRECATED: This script is maintained for backwards compatibility.
# Prefer using: make flow-crypto
# Or directly: uv run python scripts/compose_pipeline.py --profile crypto_production

set -e

echo "=========================================="
echo "Crypto Production Scan (BINANCE-only)"
echo "=========================================="
echo ""
echo "NOTE: This script wraps the modern compose_pipeline.py orchestrator."
echo "      For full production runs, use: make flow-crypto"
echo ""

# Use compose_pipeline with crypto_production profile
PROFILE="${PROFILE:-crypto_production}"

echo "Profile: $PROFILE"
echo "------------------------------------------"

uv run python scripts/compose_pipeline.py --profile "$PROFILE"

echo "------------------------------------------"
echo "Crypto scans completed. Results are in data/export/<run_id>/"
echo ""
echo "Next steps:"
echo "  1. make data-prep-raw    # Aggregate scans into raw pool"
echo "  2. make port-select      # Run natural selection"
echo "  3. make flow-crypto      # Or run full pipeline"
