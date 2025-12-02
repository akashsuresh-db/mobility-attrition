# Talent Mobility & Attrition Chatbot

A Databricks AI agent application that analyzes talent mobility and attrition data with natural language queries. Built with Dash, LangGraph, and Databricks Model Serving.

---

## 🎯 Features

- **Natural language queries** about employee data (attrition, promotions, compensation, work-life balance)
- **Row-Level Security (RLS)** via On-Behalf-Of authentication - users see only their permitted data
- **Interactive chat UI** with conversation history
- **Automated data insights** powered by Genie AI
- **Real-time analytics** on 2,000+ employees across 6 business units

---

## 📊 What Questions Can You Ask?

The agent can answer questions like:

1. **Attrition Analysis**
   - "What are the major reasons for attrition?"
   - "Which business unit has the highest attrition rate?"
   - "Show me attrition trends over time"

2. **Career Mobility**
   - "How many employees are promoted in each business unit?"
   - "What's the average promotion rate?"
   - "Show me career progression patterns"

3. **Compensation**
   - "Are our salaries competitive with industry averages?"
   - "Which grades are underpaid?"
   - "Show me the salary gap by business unit"

4. **Work-Life Balance**
   - "Are work-life balance issues causing attrition?"
   - "Which teams work the longest hours?"
   - "Show me burnout rates by department"

---

## 🚀 Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your Databricks token:**
   ```bash
   export DATABRICKS_TOKEN='your_databricks_token_here'
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   Navigate to `http://localhost:8050`

---

## 🏗️ Project Structure

```
mobility-attrition/
├── app.py                           # Main Dash web application
├── app.yaml                         # Databricks App deployment config
├── requirements.txt                 # Python dependencies
├── langgraph-agent-with-summary.ipynb  # Agent definition (LangGraph)
├── talent_Data.ipynb                # Data generation notebook (full version)
├── talent_data_FINAL_TESTED.py      # Data generation script (tested, ready to use)
└── README.md                        # This file
```

---

## 📦 Data Generation

### Using the Tested Python Script (Recommended)

The easiest way to generate the synthetic HR data:

1. **Upload to Databricks:**
   - Download `talent_data_FINAL_TESTED.py`
   - In Databricks, click **Import** → Upload file
   - It converts to a notebook automatically

2. **Run the notebook:**
   - Click **"Run All"**
   - Wait ~10-15 minutes
   - ✅ Done!

### What Data Gets Generated

**5 tables in `akash_s_demo.talent` catalog:**

1. **dim_employees_v1** (2,000 employees)
   - Demographics, tenure, current role/grade
   - 6 business units: Engineering, Sales, HR, Finance, Operations, Customer Success

2. **fact_role_history_v1** (~15,000 role changes)
   - Promotion history (14% annual rate)
   - BU-differentiated rates (Engineering 18%, HR 7%)

3. **fact_performance_v1** (12,000 records)
   - Yearly performance ratings (1-5 scale)
   - High-potential flags

4. **fact_compensation_v1** (12,000 records)
   - Salaries with industry benchmark comparison
   - Identifies employees paid below market (<10% gap)

5. **fact_attrition_snapshots_v1** (2,000 snapshots)
   - Monthly attrition tracking
   - Logic-based reasons: Low Pay (35%), Career Stagnation (20%), Work-Life Balance (15%)
   - Work hours, stress levels, burnout flags

### Key Data Characteristics

- **Attrition rates by BU:** Sales 28%, Customer Success 22%, Engineering 15%, Finance 12%, HR 10%
- **Work hours by BU:** Sales 52/wk, Customer Success 48/wk, Engineering 42/wk, HR 40/wk
- **Salary gap:** ~30-40% of employees paid below market, correlated with attrition
- **Promotions:** ~2,200 total over time period, BU-differentiated

---

## 🤖 Agent Architecture

The agent uses **LangGraph** with multiple specialized sub-agents:

1. **Supervisor Router** - Directs queries to appropriate sub-agents
2. **Genie Agent** - Executes SQL queries via Databricks Genie Space
3. **Summarizer Agent** - Formats results for presentation

The agent is deployed as a **Databricks Model Serving Endpoint** with OBO authentication.

---

## ☁️ Deploying to Databricks Apps

### Prerequisites

1. ✅ Databricks workspace with Apps enabled
2. ✅ Model Serving endpoint created from `langgraph-agent-with-summary.ipynb`
3. ✅ Genie Space configured with your talent tables
4. ✅ Service Principal with appropriate permissions

### Deployment Steps

1. **Configure the app:**
   - Update `MODEL_NAME` and `BASE_URL` in `app.py` if different
   - Ensure `app.yaml` points to `app.py`

2. **Create Databricks App:**
   - Source: Git repository (this repo)
   - Branch: `main`
   - Startup command: Defined in `app.yaml`

3. **Enable User Authorization (Critical!):**
   - In App Settings → Enable "User authorization" (Preview)
   - Add required scopes:
     - `serving.serving-endpoints` (to call agent)
     - `dashboards.genie` (for Genie Space access)
     - Default scopes (`iam.current-user:read`, etc.)

4. **Configure Service Principal:**
   - Databricks automatically provides `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET`
   - No manual configuration needed

5. **Deploy and test:**
   - Save → Deploy
   - Open the app URL
   - Test with a query like "How many employees are promoted in each business unit?"

### How OBO Works

```
User opens app → Databricks injects X-Forwarded-Access-Token
                ↓
        app.py extracts user token
                ↓
        Calls Model Serving with user token
                ↓
        Agent executes queries as user
                ↓
        Unity Catalog applies Row-Level Security
                ↓
        Returns only user's permitted data
```

**Result:** Each user sees only the data they're authorized to access.

---

## 🐛 Troubleshooting

### "Invalid scope" error

**Problem:** App can't call the Model Serving endpoint

**Fix:**
1. Go to App Settings → User Authorization
2. Ensure `serving.serving-endpoints` scope is enabled
3. Redeploy the app
4. Clear browser cache and reopen

### "Empty results" from queries

**Problem:** Query executes but returns no data

**Possible causes:**
1. **RLS is working** - User only has access to a subset of data
2. **Query mismatch** - Asking for "all BUs" when user can only see one

**Fix:**
- Ask for data within your scope: "Show me attrition in my department"
- Or have admin grant broader access

### App shows "Agent configuration loaded"

**Problem:** App is running `agent.py` instead of `app.py`

**Fix:**
1. Check `app.yaml` has `command: [python, app.py]`
2. Or set startup command in Databricks Apps UI
3. Restart the app

### Missing business unit in results

**Problem:** Query returns 5 BUs instead of 6 (HR missing)

**Fix:** This was a bug where the app selected the wrong table from duplicate results. Fixed in commit `6bf32b2`.
- Ensure you're running latest code from `main` branch
- HR has very few promotions (0.7x multiplier) which is expected

---

## 📈 Performance Optimizations

**Recent improvements:**
- ✅ Removed excessive DEBUG logging (~90% reduction)
- ✅ Fixed table selection logic (selects most complete data)
- ✅ Reduced I/O overhead for faster response times

**Expected:** Sub-second response times for queries after agent processing completes.

---

## 🔐 Security & Privacy

- **User tokens are never cached** - Each request uses fresh token
- **RLS enforced** - Users see only their permitted data
- **Tokens not logged** - Only user emails logged for debugging
- **Service Principal for infrastructure** - User tokens for data access

---

## 📝 Example Queries

Try these in the chat interface:

```
"How many employees are promoted in each business unit?"

"What are the top reasons for attrition?"

"Show me which departments have the highest attrition rate"

"Are our salaries competitive with the market?"

"Which teams work the longest hours?"

"Show me the promotion rate trend over time"
```

---

## 🛠️ Configuration

### App Settings (`app.py`)

```python
MODEL_NAME = "agents_akash_s_demo-talent-talent_agent_v1"
BASE_URL = "https://adb-984752964297111.11.azuredatabricks.net/serving-endpoints"
```

Update these if your endpoint details differ.

### Dependencies (`requirements.txt`)

Core libraries:
- `dash==2.14.2` - Web UI framework
- `openai>=1.54.0` - Agent SDK client
- `pandas>=2.0.0` - Data processing
- `PyJWT>=2.8.0` - Token validation

---

## 📚 Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Databricks Model Serving](https://docs.databricks.com/en/machine-learning/model-serving/index.html)
- [Unity Catalog Row-Level Security](https://docs.databricks.com/en/data-governance/unity-catalog/row-and-column-filters.html)

---

## 🎉 Success Criteria

Your deployment is successful when:

1. ✅ App loads and shows chat UI
2. ✅ Queries return relevant data
3. ✅ Different users see different data (RLS working)
4. ✅ No permission errors
5. ✅ All 6 business units appear in results when expected
6. ✅ Fast response times (<5 seconds for most queries)

---

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review app deployment logs in Databricks
3. Verify Model Serving endpoint is running
4. Ensure User Authorization is enabled in app settings
5. Test queries directly in Genie Space to isolate issues

---

**Latest Update:** December 2025 - Fixed missing HR business unit bug and improved performance
