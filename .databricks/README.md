# Databricks Deployment Guide

## ⚠️ IMPORTANT: Two Separate Deployments

This repository contains code for **TWO different deployments**:

### 1️⃣ Agent (Model Serving Endpoint)
- **File:** `agent.py` (generated from notebook Cell 3)
- **Deploy to:** Model Serving Endpoint
- **Purpose:** MLflow agent with OBO authentication
- **Deployment:** Via notebook cells 11, 12, 13

### 2️⃣ Web App (Databricks Apps)
- **File:** `app.py`
- **Deploy to:** Databricks Apps
- **Purpose:** Chat UI (Dash/Flask web interface)
- **Deployment:** Via Databricks Apps UI
- **Configuration:** `app.yaml`

## 🚨 Common Mistakes

### ❌ WRONG: Running agent.py in Databricks Apps
```
Command: python agent.py  # This is for model serving, not apps!
```

### ✅ CORRECT: Running app.py in Databricks Apps
```
Command: python app.py  # This is the web UI
```

## 📋 Deployment Checklist

### Deploy Agent:
1. ✅ Open `langgraph-agent-with-summary.ipynb`
2. ✅ Run Cell 11 (log model)
3. ✅ Run Cell 12 (register model)
4. ✅ Run Cell 13 (deploy to serving endpoint)

### Deploy App:
1. ✅ Go to Databricks Apps UI
2. ✅ Create/Update app
3. ✅ Point to `app.py` (or use `app.yaml` config)
4. ✅ Ensure command is `python app.py`
5. ✅ Restart app

## 🔄 Architecture

```
User Browser
    ↓
Databricks App (app.py)
    ↓ calls with user token
Model Serving Endpoint (agent.py)
    ↓ uses OBO
Genie Space
    ↓ RLS enforced
Unity Catalog Tables
```

