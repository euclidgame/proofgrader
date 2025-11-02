# 🚀 Quick Start Guide - Mathematical Olympiad Solution Viewer

## ⚡ Fastest Way to Launch (Local)

```bash
./launch.sh
```

That's it! The app will be available at **http://localhost:7860**

---

## 🌐 For Public Access (Choose One)

### Option A: Instant Public Link (72-hour temporary)

1. Edit `app.py`, line 230:
   ```python
   share=True,  # Change from False to True
   ```

2. Run:
   ```bash
   python app.py
   ```

3. You'll get a public URL like: `https://xxxxx.gradio.live`
   Share this link with anyone!

### Option B: Permanent Free Hosting (Recommended)

**Deploy to Hugging Face Spaces** (5 minutes setup):

1. Create account at https://huggingface.co/
2. Create a new Space (select "Gradio" SDK)
3. Upload these files:
   - `app.py` 
   - `final_dataset.jsonl`
   - `requirements.txt`
4. Your app is live at: `https://huggingface.co/spaces/YOUR_USERNAME/SPACE_NAME`

**No server maintenance, no costs, always online!**

---

## 📊 What You Get

✨ **Beautiful Interface** with:
- 🎨 Modern gradient design
- 📱 Mobile-responsive layout
- ♿ Screen reader accessible
- 🔢 Full LaTeX/MathJax support

📚 **Content Organization**:
- 145 unique problems from IMO, APMO, etc.
- 435 AI-generated solutions
- Expert ratings (0-7 scale)
- Official reference solutions
- Detailed marking schemes

---

## 📁 Files Included

```
new_data/
├── app.py                    # Main application (use this!)
├── viewer_app.py             # Alternative with absolute paths
├── final_dataset.jsonl       # Your data (435 entries)
├── requirements.txt          # Dependencies
├── launch.sh                 # Quick launch script
├── README_DEPLOYMENT.md      # Full deployment guide
└── QUICKSTART.md            # This file
```

---

## 🎯 Key Features

### 1. **Dynamic Problem Selection**
- Dropdown menu with 145 olympiad problems
- Auto-updates available models per problem

### 2. **Multi-Model Comparison**
- See solutions from different AI systems
- Compare: OpenAI-o3, DeepSeek-R1, Claude, etc.

### 3. **LaTeX Rendering**
- Perfect mathematical notation display
- Works with `\( inline \)` and `\[ display \]` formulas

### 4. **Expandable Sections**
- Collapsible reference solutions
- Hidden marking schemes (expand when needed)
- Clean, uncluttered interface

### 5. **Expert Ratings**
- Visual rating bars (0-7 scale)
- Human expert evaluation
- Quality assessment at a glance

---

## 🛠️ Customization

### Change Colors
Edit gradients in `app.py`:
```python
# Line ~75: Header gradient
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

# Line ~115: Rating gradient  
background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
```

### Change Port
```python
# Line 230 in app.py
app.launch(server_port=8080)  # Change from 7860
```

### Add Password Protection
```python
# Line 230 in app.py
app.launch(auth=("username", "password"))
```

---

## 🎓 Example Problems Included

Your dataset contains solutions to classic problems like:
- **APMO 2023-2**: Finding integers with special divisor properties
- **APMO 2025-1**: Geometry with circumcircles
- **IMO 2022-Q6**: Nordic squares and uphill paths
- **IMO 2023-Q5**: Japanese triangles and ninja paths
- And 141+ more challenging problems!

---

## 📖 Usage Tips

1. **Select a Problem**: Use the dropdown to choose from 145 problems
2. **Pick a Model**: See which AI systems attempted this problem
3. **Read the Solution**: Scroll through the formatted solution
4. **Check the Rating**: See how experts evaluated it (0-7)
5. **Expand Reference**: Compare with official solution
6. **View Rubric**: Check the marking scheme for grading criteria

---

## 🔧 Troubleshooting

### LaTeX not rendering?
- Gradio automatically loads MathJax
- Use proper delimiters: `\(` `\)` for inline, `\[` `\]` for display
- Clear browser cache and refresh

### Port already in use?
```bash
# Find what's using port 7860
lsof -i :7860

# Or change the port in app.py
```

### Data not loading?
```bash
# Verify data file is present
ls -lh final_dataset.jsonl

# Should show: -rw-r--r-- ... final_dataset.jsonl

# Test data loading
python -c "import json; data=[json.loads(line) for line in open('final_dataset.jsonl')]; print(f'{len(data)} entries loaded')"
```

---

## 🌟 Deployment Comparison

| Option | Setup Time | Cost | Uptime | Custom Domain |
|--------|-----------|------|--------|---------------|
| **Local (./launch.sh)** | 1 min | Free | Manual | ❌ |
| **Gradio Share** | 1 min | Free | 72 hours | ❌ |
| **Hugging Face** | 5 min | Free | 24/7 | ❌ |
| **AWS/GCP/Azure** | 30 min | $5-20/mo | 24/7 | ✅ |

**Recommendation**: Start with local testing → Gradio share → Hugging Face Spaces

---

## 📚 Additional Resources

- **Full Deployment Guide**: See `README_DEPLOYMENT.md`
- **Gradio Docs**: https://gradio.app/docs/
- **Hugging Face Tutorial**: https://huggingface.co/docs/hub/spaces-sdks-gradio
- **LaTeX Reference**: https://www.overleaf.com/learn/latex/Mathematical_expressions

---

## 💬 Questions?

Common issues and solutions are in `README_DEPLOYMENT.md`

---

**Built with Gradio • Powered by MathJax • Made for Math Lovers** 🎓✨

