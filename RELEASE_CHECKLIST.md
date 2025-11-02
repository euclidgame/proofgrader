# Code Release Checklist

## ✅ Completed

### Repository Restructuring (Latest)
- [x] Created `proofgrader/` package with internal modules
- [x] Created `scripts/` directory with user-facing CLI:
  - [x] `generate.py` - For generation tasks
  - [x] `evaluate.py` - For evaluation tasks
  - [x] `evaluate_workflow.py` - For complex workflows
- [x] Updated imports in `evaluator_design/workflows/`
- [x] Created comprehensive README.md
- [x] Created MIGRATION_GUIDE.md
- [x] Created RESTRUCTURING_SUMMARY.md
- [x] Updated setup.py for package installation
- [x] Marked old `main.py` as deprecated
- [x] Verified no linter errors

### Previous Cleanup
- [x] Archive analysis results and documentation
- [x] Remove non-core analysis scripts
- [x] Clean up directory structure
- [x] Keep all essential workflow files
- [x] Keep all YAML configurations
- [x] Document cleanup process

## 🔲 Before Public Release

### 1. Security & Credentials
- [ ] Remove or gitignore `ramps-457621-0c06afd83f39.json`
- [ ] Check for any hardcoded API keys or credentials
- [ ] Review .gitignore file
- [ ] Ensure no sensitive data in git history

### 2. Testing
- [ ] Test single-stage workflow with small dataset
- [ ] Test decompose-then-judge workflow
- [ ] Test repeat-and-aggregate workflow
- [ ] Test reflect-and-revise workflow
- [ ] Verify metrics computation works
- [ ] Verify dashboard generation works

### 3. Documentation
- [ ] Update main README.md with:
  - Clear installation instructions
  - Basic usage examples
  - Workflow descriptions
  - Configuration guide
  - Requirements and dependencies
- [ ] Add LICENSE file
- [ ] Add CITATION.bib or CITATION.cff
- [ ] Document YAML configuration options
- [ ] Add example datasets or links

### 4. Code Quality
- [ ] Run linting (pylint, flake8, black)
- [ ] Add docstrings to main functions
- [ ] Add type hints where missing
- [ ] Review and clean up comments
- [ ] Remove debug print statements

### 5. Dependencies
- [ ] Verify requirements.txt is complete
- [ ] Test installation in fresh environment
- [ ] Pin important dependency versions
- [ ] Document Python version requirements

### 6. Final Cleanup
- [ ] Delete `_archive/` directory (or keep in separate branch)
- [ ] Delete cleanup documentation files:
  - CLEANUP_ANALYSIS.md
  - CLEANUP_SUMMARY.md
  - RELEASE_CHECKLIST.md (this file)
- [ ] Remove any remaining TODO comments in code
- [ ] Final git commit with message: "Prepare for code release"

### 7. Repository Setup
- [ ] Create GitHub/GitLab repository
- [ ] Add appropriate .gitignore
- [ ] Set up repository description
- [ ] Add topics/tags for discoverability
- [ ] Consider adding GitHub Actions for CI/CD

### 8. Optional Enhancements
- [ ] Add example notebooks
- [ ] Add unit tests
- [ ] Create Docker container
- [ ] Add badge icons to README
- [ ] Set up documentation website (e.g., GitHub Pages)

---

## Quick Start Commands (For Testing)

### Test Installation
```bash
pip install -r requirements.txt
```

### Test Core Workflow
```bash
# Single evaluation
python evaluator_design/run_evaluator_workflow.py \
  --evaluator-model gemini-2.5-pro \
  --template basic \
  --data-version pilot \
  --workflow single \
  --max-examples 5

# With local dataset
python main.py \
  --use-remote-api \
  --remote-model gemini-2.5-pro \
  --dataset your_dataset.jsonl \
  --problem-field problem \
  --template basic \
  --max-examples 5
```

---

## Notes
- All archived files are in `_archive/` directory
- All deleted files remain in git history
- Current structure focuses on core evaluation workflows
- 25 Python files remain in main repository

