#!/bin/bash

# Mathematical Olympiad Solution Viewer - Quick Launch Script

echo "🎓 Mathematical Olympiad Solution Viewer"
echo "========================================"
echo ""

# Check if gradio is installed
if ! python -c "import gradio" 2>/dev/null; then
    echo "📦 Installing Gradio..."
    pip install gradio
    echo ""
fi

# Check if data file exists
if [ ! -f "final_dataset.jsonl" ]; then
    echo "❌ Error: final_dataset.jsonl not found in current directory"
    echo "Please ensure the data file is in the same directory as this script."
    exit 1
fi

echo "✅ All dependencies installed"
echo "✅ Data file found ($(wc -l < final_dataset.jsonl) entries)"
echo ""
echo "🚀 Launching the application..."
echo "📡 The app will be available at: http://localhost:7860"
echo ""
echo "💡 Tips:"
echo "   - Press Ctrl+C to stop the server"
echo "   - To create a public link, edit app.py and set share=True"
echo ""
echo "---"
echo ""

python app.py

