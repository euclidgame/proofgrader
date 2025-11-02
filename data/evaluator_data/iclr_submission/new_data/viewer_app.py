import gradio as gr
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Load the dataset
def load_data(filepath: str) -> List[Dict]:
    """Load JSONL data file."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

# Get unique problem IDs and models
def get_filters(data: List[Dict]) -> Tuple[List[str], Dict[str, List[str]]]:
    """Extract unique problem IDs and map problems to their available models."""
    problem_ids = []
    problem_to_models = {}
    
    for entry in data:
        problem_id = entry['problem_id']
        model = entry['generator']
        
        if problem_id not in problem_to_models:
            problem_ids.append(problem_id)
            problem_to_models[problem_id] = []
        
        problem_to_models[problem_id].append(model)
    
    return problem_ids, problem_to_models

# Format the display content
def format_content(entry: Dict) -> str:
    """Format entry as HTML with LaTeX support."""
    
    # Extract metadata
    metadata = entry.get('metadata', {})
    contest = metadata.get('contest', 'N/A')
    contest_year = metadata.get('contest_year', 'N/A')
    problem_id = entry.get('problem_id', 'N/A')
    generator = entry.get('generator', 'N/A')
    expert_rating = entry.get('expert_rating', 'N/A')
    
    # Format the content with proper structure
    html_content = f"""
<div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.8; max-width: 100%;">

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
    <h1 style="margin: 0 0 10px 0; font-size: 2.2em; font-weight: 700;">📐 Problem Viewer</h1>
    <p style="margin: 0; font-size: 1.1em; opacity: 0.95;">Mathematical Olympiad Solutions</p>
</div>

<div style="background: #f8f9fa; padding: 25px; border-radius: 12px; margin-bottom: 25px; border-left: 5px solid #667eea;">
    <h2 style="color: #667eea; margin-top: 0; font-size: 1.5em; display: flex; align-items: center;">
        <span style="margin-right: 10px;">ℹ️</span> Metadata
    </h2>
    <div style="display: grid; gap: 12px;">
        <div><strong style="color: #764ba2;">Problem ID:</strong> <span style="color: #2d3748;">{problem_id}</span></div>
        <div><strong style="color: #764ba2;">Contest:</strong> <span style="color: #2d3748;">{contest} {contest_year}</span></div>
        <div><strong style="color: #764ba2;">Model:</strong> <span style="color: #2d3748; font-family: 'Courier New', monospace; background: #e2e8f0; padding: 2px 8px; border-radius: 4px;">{generator}</span></div>
    </div>
</div>

<div style="background: white; padding: 30px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
    <h2 style="color: #667eea; margin-top: 0; font-size: 1.5em; display: flex; align-items: center; border-bottom: 3px solid #667eea; padding-bottom: 10px;">
        <span style="margin-right: 10px;">❓</span> Problem Statement
    </h2>
    <div style="color: #2d3748; font-size: 1.05em; padding: 15px 0;">
        {entry.get('problem', 'N/A')}
    </div>
</div>

<div style="background: white; padding: 30px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
    <h2 style="color: #667eea; margin-top: 0; font-size: 1.5em; display: flex; align-items: center; border-bottom: 3px solid #667eea; padding-bottom: 10px;">
        <span style="margin-right: 10px;">🤖</span> Model Solution
    </h2>
    <div style="color: #2d3748; font-size: 1.05em; padding: 15px 0; white-space: pre-wrap;">
        {entry.get('model_solution', 'N/A')}
    </div>
</div>

<div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.15);">
    <h2 style="color: white; margin-top: 0; font-size: 1.5em; display: flex; align-items: center;">
        <span style="margin-right: 10px;">⭐</span> Expert Rating
    </h2>
    <div style="color: white; font-size: 2.5em; font-weight: bold; text-align: center; padding: 10px;">
        {expert_rating} / 7
    </div>
    <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; overflow: hidden; margin-top: 15px;">
        <div style="background: white; height: 100%; width: {(expert_rating/7)*100 if isinstance(expert_rating, (int, float)) else 0}%; border-radius: 4px; transition: width 0.3s ease;"></div>
    </div>
</div>

</div>
"""
    
    return html_content

def format_reference(entry: Dict) -> str:
    """Format reference solution."""
    html_content = f"""
<div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.8;">
<div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
    <h2 style="color: #10b981; margin-top: 0; font-size: 1.5em; display: flex; align-items: center; border-bottom: 3px solid #10b981; padding-bottom: 10px;">
        <span style="margin-right: 10px;">✅</span> Reference Solution
    </h2>
    <div style="color: #2d3748; font-size: 1.05em; padding: 15px 0; white-space: pre-wrap;">
        {entry.get('reference_solution', 'N/A')}
    </div>
</div>
</div>
"""
    return html_content

def format_marking_scheme(entry: Dict) -> str:
    """Format marking scheme."""
    html_content = f"""
<div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.8;">
<div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
    <h2 style="color: #f59e0b; margin-top: 0; font-size: 1.5em; display: flex; align-items: center; border-bottom: 3px solid #f59e0b; padding-bottom: 10px;">
        <span style="margin-right: 10px;">📝</span> Marking Scheme
    </h2>
    <div style="color: #2d3748; font-size: 1.05em; padding: 15px 0; white-space: pre-wrap;">
        {entry.get('marking_scheme', 'N/A')}
    </div>
</div>
</div>
"""
    return html_content

# Main application
def create_app(data_path: str):
    """Create and configure the Gradio interface."""
    
    # Load data
    data = load_data(data_path)
    problem_ids, problem_to_models = get_filters(data)
    
    # Create lookup dictionary
    data_lookup = {}
    for entry in data:
        key = (entry['problem_id'], entry['generator'])
        data_lookup[key] = entry
    
    def update_models(problem_id: str) -> gr.Dropdown:
        """Update available models based on selected problem."""
        models = problem_to_models.get(problem_id, [])
        return gr.Dropdown(choices=models, value=models[0] if models else None)
    
    def display_content(problem_id: str, model: str):
        """Display formatted content for selected problem and model."""
        if not problem_id or not model:
            return "Please select a problem and model.", "", ""
        
        entry = data_lookup.get((problem_id, model))
        if not entry:
            return "Entry not found.", "", ""
        
        main_content = format_content(entry)
        reference = format_reference(entry)
        marking = format_marking_scheme(entry)
        
        return main_content, reference, marking
    
    # Custom CSS for better styling
    custom_css = """
    .gradio-container {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        max-width: 1400px !important;
        margin: auto !important;
    }
    .gr-button-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
    }
    .gr-button-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4) !important;
    }
    .accordion {
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    footer {
        display: none !important;
    }
    """
    
    # Create Gradio interface
    with gr.Blocks(css=custom_css, title="Mathematical Olympiad Solution Viewer", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("""
        # 🎓 Mathematical Olympiad Solution Viewer
        
        Explore high-quality mathematical proofs from competitions like IMO, APMO, and more. 
        Select a problem and model to view detailed solutions with expert ratings.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                problem_dropdown = gr.Dropdown(
                    choices=problem_ids,
                    label="📋 Select Problem",
                    value=problem_ids[0] if problem_ids else None,
                    info="Choose from various mathematical olympiad problems"
                )
            
            with gr.Column(scale=1):
                model_dropdown = gr.Dropdown(
                    label="🤖 Select Model",
                    info="Different AI models that attempted the problem"
                )
        
        # Update models when problem changes
        problem_dropdown.change(
            fn=update_models,
            inputs=[problem_dropdown],
            outputs=[model_dropdown]
        )
        
        # Initialize model dropdown with first problem's models
        if problem_ids:
            model_dropdown.choices = problem_to_models[problem_ids[0]]
            model_dropdown.value = problem_to_models[problem_ids[0]][0] if problem_to_models[problem_ids[0]] else None
        
        # Main content area
        main_html = gr.HTML(label="Content")
        
        # Expandable sections for reference and marking scheme
        with gr.Accordion("📚 Reference Solution (Official)", open=False):
            reference_html = gr.HTML()
        
        with gr.Accordion("📊 Marking Scheme", open=False):
            marking_html = gr.HTML()
        
        gr.Markdown("""
        ---
        ### 💡 About This Viewer
        
        This interface displays mathematical olympiad problems and their solutions generated by various AI models.
        Each solution includes:
        - **Problem Statement**: The original mathematical challenge
        - **Model Solution**: AI-generated proof or solution
        - **Expert Rating**: Human expert evaluation (0-7 scale)
        - **Reference Solution**: Official or expert solution
        - **Marking Scheme**: Grading rubric used for evaluation
        
        All content supports **LaTeX mathematical notation** for proper formula rendering.
        
        ---
        **Dataset**: ProofGym Evaluator Design | **Models**: Various state-of-the-art AI systems
        """)
        
        # Set up event handlers
        for component in [problem_dropdown, model_dropdown]:
            component.change(
                fn=display_content,
                inputs=[problem_dropdown, model_dropdown],
                outputs=[main_html, reference_html, marking_html]
            )
        
        # Load initial content
        if problem_ids and problem_to_models[problem_ids[0]]:
            app.load(
                fn=display_content,
                inputs=[problem_dropdown, model_dropdown],
                outputs=[main_html, reference_html, marking_html]
            )
    
    return app

if __name__ == "__main__":
    # Path to the data file
    data_file = "/home/ubuntu/wenjie-cal/ProofGym/evaluator_design/data/iclr_submission/new_data/final_dataset.jsonl"
    
    # Create and launch the app
    app = create_app(data_file)
    app.launch(
        server_name="0.0.0.0",  # Makes it accessible from outside
        server_port=7860,
        share=False,  # Set to True for a temporary public link
        show_error=True
    )

