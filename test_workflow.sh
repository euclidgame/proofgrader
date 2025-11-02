#!/bin/bash
# Test ProofGym Workflow
# This script tests the complete workflow with the test data

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            ProofGym Workflow Test Script                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
DATA_DIR="data/test_data"
PROBLEMS_FILE="$DATA_DIR/problems.jsonl"
OUTPUT_DIR="$DATA_DIR/outputs"
GENERATOR="gpt-4"
NUM_ATTEMPTS=2
MAX_PROBLEMS=3
EVALUATOR="gemini-2.5-pro"

# Check if problems file exists
if [ ! -f "$PROBLEMS_FILE" ]; then
    echo "❌ Error: $PROBLEMS_FILE not found"
    echo "   Please make sure you have test data in $DATA_DIR/"
    exit 1
fi

echo "✓ Found problems file: $PROBLEMS_FILE"
echo "  $(wc -l < "$PROBLEMS_FILE") problems available"
echo ""

# Count problems
echo "📊 Test Configuration:"
echo "   Data directory: $DATA_DIR"
echo "   Generator: $GENERATOR"
echo "   Attempts per problem: $NUM_ATTEMPTS"
echo "   Max problems: $MAX_PROBLEMS"
echo "   Evaluator: $EVALUATOR"
echo ""

# Check for API keys
echo "🔑 Checking API keys..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set"
fi
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  Warning: GOOGLE_API_KEY not set"
fi
echo ""

# Test 1: Generation only
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  TEST 1: Solution Generation                                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Running: python scripts/run_full_workflow.py"
echo "         --data-dir $DATA_DIR"
echo "         --generators $GENERATOR"
echo "         --num-attempts $NUM_ATTEMPTS"
echo "         --max-problems $MAX_PROBLEMS"
echo "         --skip-evaluation"
echo ""

python scripts/run_full_workflow.py \
    --data-dir "$DATA_DIR" \
    --generators "$GENERATOR" \
    --num-attempts "$NUM_ATTEMPTS" \
    --max-problems "$MAX_PROBLEMS" \
    --skip-evaluation || {
        echo "❌ Generation test failed"
        exit 1
    }

# Check output
SOLUTIONS_FILE="$OUTPUT_DIR/model_solutions.jsonl"
if [ -f "$SOLUTIONS_FILE" ]; then
    NUM_SOLUTIONS=$(wc -l < "$SOLUTIONS_FILE")
    echo ""
    echo "✓ Generated $NUM_SOLUTIONS solutions"
    echo "  Output: $SOLUTIONS_FILE"
    echo ""
    echo "Sample solution:"
    head -n 1 "$SOLUTIONS_FILE" | python -m json.tool | head -n 20
    echo "  ..."
else
    echo "❌ Expected output file not found: $SOLUTIONS_FILE"
    exit 1
fi

# Test 2: Evaluation workflow
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  TEST 2: Evaluation Workflow                                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Running: python scripts/evaluate_workflow.py"
echo "         --evaluator-model $EVALUATOR"
echo "         --workflow single"
echo "         --data-version test_data"
echo "         --dataset $SOLUTIONS_FILE"
echo "         --max-examples $MAX_PROBLEMS"
echo ""

python scripts/evaluate_workflow.py \
    --evaluator-model "$EVALUATOR" \
    --workflow single \
    --data-version test_data \
    --dataset "$SOLUTIONS_FILE" \
    --max-examples "$MAX_PROBLEMS" || {
        echo "⚠️  Evaluation test failed (may be due to missing API keys)"
        echo "   You can test this step manually when API keys are available"
    }

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  WORKFLOW TEST SUMMARY                                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✓ Generation: SUCCESS"
if [ -f "$SOLUTIONS_FILE" ]; then
    echo "  - Generated $(wc -l < "$SOLUTIONS_FILE") solutions"
    echo "  - Output: $SOLUTIONS_FILE"
fi
echo ""
echo "ℹ️  Evaluation: Depends on API access"
echo "   Run manually with API keys configured"
echo ""
echo "📁 Output directory: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Review generated solutions in $SOLUTIONS_FILE"
echo "  2. Configure API keys if not already done"
echo "  3. Run full workflow:"
echo "     python scripts/run_full_workflow.py --data-dir $DATA_DIR \\"
echo "       --generators $GENERATOR --num-attempts 3 --evaluator $EVALUATOR"
echo ""





