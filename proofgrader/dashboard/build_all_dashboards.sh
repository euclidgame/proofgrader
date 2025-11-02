#!/bin/bash
# Convenience script to build both static and dynamic dashboards

set -e  # Exit on error

DATA_VERSION=${1:-iclr_submission}

echo "================================================"
echo "Building dashboards for data version: $DATA_VERSION"
echo "================================================"
echo ""

echo "Step 1: Computing evaluator distances..."
python evaluator_design/compute_evaluator_distances.py --data-version "$DATA_VERSION"
echo "✓ Done"
echo ""

echo "Step 2: Building static dashboard..."
python evaluator_design/build_dashboard.py --data-version "$DATA_VERSION"
echo "✓ Done"
echo ""

echo "Step 3: Collecting detailed data for dynamic dashboard..."
python evaluator_design/collect_detailed_data.py --data-version "$DATA_VERSION"
echo "✓ Done"
echo ""

echo "Step 4: Building dynamic dashboard..."
python evaluator_design/build_dynamic_dashboard.py --data-version "$DATA_VERSION"
echo "✓ Done"
echo ""

echo "================================================"
echo "All dashboards built successfully!"
echo "================================================"
echo ""
echo "Static dashboard:"
echo "  evaluator_design/outputs/dashboard/$DATA_VERSION/dashboard.html"
echo ""
echo "Dynamic dashboard (with filters):"
echo "  evaluator_design/outputs/dashboard/$DATA_VERSION/dynamic_dashboard.html"
echo ""
echo "To view, open in a browser or serve locally with:"
echo "  cd evaluator_design/outputs/dashboard/$DATA_VERSION && python -m http.server 8000"
echo ""

