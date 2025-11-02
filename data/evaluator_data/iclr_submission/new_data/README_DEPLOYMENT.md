# 🎓 Mathematical Olympiad Solution Viewer - Deployment Guide

A beautiful, accessible web interface for viewing mathematical olympiad solutions with LaTeX support.

## 🚀 Quick Start (Local)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python viewer_app.py
```

The app will be available at: `http://localhost:7860`

## 🌐 Deployment Options

### Option 1: Gradio Share (Quickest - Temporary Link)

Modify the launch command in `viewer_app.py`:

```python
app.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=True,  # Change this to True
    show_error=True
)
```

This creates a **temporary public link** (valid for 72 hours) that you can share with anyone!

### Option 2: Hugging Face Spaces (Recommended - Free & Permanent)

Hugging Face Spaces provides **free hosting** for Gradio apps!

1. **Create a Hugging Face account** at https://huggingface.co/

2. **Create a new Space**:
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Name: `math-olympiad-viewer` (or your choice)
   - License: Choose appropriate license
   - SDK: Select "Gradio"
   - Hardware: Free CPU (sufficient for this app)

3. **Upload files**:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/math-olympiad-viewer
   cd math-olympiad-viewer
   
   # Copy your files
   cp viewer_app.py app.py  # Hugging Face expects app.py
   cp final_dataset.jsonl .
   cp requirements.txt .
   
   # Create a simple README
   echo "# Mathematical Olympiad Solution Viewer" > README.md
   
   # Commit and push
   git add .
   git commit -m "Initial commit"
   git push
   ```

4. **Your app will be live** at: `https://huggingface.co/spaces/YOUR_USERNAME/math-olympiad-viewer`

**Important**: Update the `data_file` path in `viewer_app.py` before deploying:
```python
# Change from:
data_file = "/home/ubuntu/wenjie-cal/ProofGym/evaluator_design/data/iclr_submission/new_data/final_dataset.jsonl"

# To:
data_file = "final_dataset.jsonl"  # Relative path for deployment
```

### Option 3: Google Colab (No Installation Required)

Create a Colab notebook with this code:

```python
!pip install gradio

# Upload final_dataset.jsonl and viewer_app.py to Colab
# Or download from GitHub/URL

from google.colab import files
files.upload()  # Upload your files

# Run the app
!python viewer_app.py
```

The notebook will provide a public URL you can share!

### Option 4: AWS/GCP/Azure (Production)

For production deployment with custom domain:

1. **Set up a cloud VM** (e.g., AWS EC2, GCP Compute Engine)

2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip nginx -y
   pip3 install -r requirements.txt
   ```

3. **Run with systemd** (persistent service):
   
   Create `/etc/systemd/system/math-viewer.service`:
   ```ini
   [Unit]
   Description=Math Olympiad Viewer
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/app
   ExecStart=/usr/bin/python3 viewer_app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start:
   ```bash
   sudo systemctl enable math-viewer
   sudo systemctl start math-viewer
   ```

4. **Configure Nginx** as reverse proxy:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:7860;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

5. **Add SSL with Let's Encrypt**:
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   sudo certbot --nginx -d your-domain.com
   ```

### Option 5: Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY viewer_app.py .
COPY final_dataset.jsonl .

EXPOSE 7860

CMD ["python", "viewer_app.py"]
```

Build and run:
```bash
docker build -t math-viewer .
docker run -p 7860:7860 math-viewer
```

Deploy to cloud services:
- **Docker Hub** → AWS ECS/Fargate
- **Google Cloud Run**
- **Azure Container Instances**

## 📊 Features

- ✅ **LaTeX Support**: Full MathJax rendering for mathematical formulas
- ✅ **Responsive Design**: Works on mobile, tablet, and desktop
- ✅ **Accessible**: Screen reader friendly, keyboard navigation
- ✅ **Fast Loading**: Efficient data handling
- ✅ **Beautiful UI**: Modern gradient design with smooth animations
- ✅ **Easy Navigation**: Dropdown filters for problems and models
- ✅ **Expandable Sections**: Collapsible reference solutions and marking schemes

## 🎨 Customization

### Change Color Scheme

Edit the gradient colors in `viewer_app.py`:

```python
# Primary gradient (header)
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

# Secondary gradient (rating)
background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
```

### Modify Layout

Adjust the grid layout in the Gradio Blocks:

```python
with gr.Row():
    with gr.Column(scale=2):  # Adjust scale
        # Content
```

## 🔧 Troubleshooting

### LaTeX not rendering?

Make sure your formulas use proper LaTeX delimiters:
- Inline: `\( formula \)` or `$formula$`
- Display: `\[ formula \]` or `$$formula$$`

### Data not loading?

Check the file path in `viewer_app.py`:
```python
data_file = "path/to/final_dataset.jsonl"
```

### Port already in use?

Change the port in `app.launch()`:
```python
app.launch(server_port=7861)  # Use different port
```

## 📝 Data Format

The app expects JSONL format with these fields:

```json
{
  "problem_id": "APMO-2023-2",
  "problem": "Problem statement with \\(LaTeX\\)",
  "generator": "Model-Name",
  "model_solution": "Solution text",
  "reference_solution": "Official solution",
  "expert_rating": 7,
  "marking_scheme": "Grading rubric",
  "metadata": {
    "contest": "APMO",
    "contest_year": "2023"
  }
}
```

## 🌟 Best Practices for Public Deployment

1. **Add authentication** if data is sensitive:
   ```python
   app.launch(auth=("username", "password"))
   ```

2. **Enable HTTPS** in production (use nginx + certbot)

3. **Monitor usage** with analytics:
   ```python
   app.launch(analytics_enabled=True)
   ```

4. **Set resource limits** on cloud platforms to control costs

5. **Add caching** for frequently accessed data

## 📚 Resources

- **Gradio Documentation**: https://gradio.app/docs/
- **Hugging Face Spaces**: https://huggingface.co/docs/hub/spaces
- **MathJax Documentation**: https://docs.mathjax.org/
- **LaTeX Guide**: https://en.wikibooks.org/wiki/LaTeX/Mathematics

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Gradio documentation
3. Open an issue in your repository

---

**Made with ❤️ for the mathematical community**

