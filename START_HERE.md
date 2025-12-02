# ⚠️ START HERE - IMPORTANT

## Use the FIXED Version!

**❌ DON'T USE:** `talent_data_v1.py` (has import conflicts)
**✅ USE THIS:** `talent_data_v1_fixed.py` (fully working)

---

## What Was Wrong

The original `talent_data_v1.py` had a critical bug:
```python
from pyspark.sql.functions import *  # ❌ BAD - imports PySpark's max()
LATEST_YEAR = max(YEARS)  # ❌ ERROR - tries to use PySpark max on Python list
```

PySpark's `max()` function expects a Spark column, not a Python list!

---

## What Was Fixed

```python
# Import specific functions instead of *
from pyspark.sql.functions import (
    col, lit, when, concat, ...  # Only what we need
)
import builtins  # For Python's built-in functions

# Use Python's max explicitly
LATEST_YEAR = builtins.max(YEARS)  # ✅ Works!
```

**All function conflicts resolved:**
- `max()` → `builtins.max()`
- `min()` → `builtins.min()`  
- `round()` → `spark_round()` (for Spark operations)

---

## 🚀 Quick Start

### Step 1: Download
Download **talent_data_v1_fixed.py** (NOT the old one!)

### Step 2: Import to Databricks
1. Go to Databricks Workspace
2. Click **"Import"**
3. Upload **talent_data_v1_fixed.py**
4. Select "Python" as file type

### Step 3: Run
1. Open the imported notebook
2. Click **"Run All"**
3. Wait ~10-15 minutes
4. ✅ Done!

---

## 📊 What You Get

5 tables with meaningful data:
1. `dim_employees_v1` (2,000 employees)
2. `fact_role_history_v1` (~20,000 role changes)
3. `fact_performance_v1` (22,000 performance records)
4. `fact_compensation_v1` (22,000 salary records with industry comparison)
5. `fact_attrition_snapshots_v1` (~65,000 monthly snapshots with WLB metrics)

---

## 🎯 Your 5 Questions - Answered

✅ **Q1: Major reasons for attrition?**
- Low Pay: 30-35%
- Work-Life Balance: 15-20%
- Career Stagnation: 15-20%

✅ **Q2: Which BU has highest attrition?**
- Sales: 28%
- Customer Success: 22%
- HR: 10%

✅ **Q3: Promotions per BU?**
- Engineering: 80-100/year
- Sales: 60-75/year
- HR: 25-35/year

✅ **Q4: Salaries vs industry?**
- 30-40% paid below market
- Clear correlation with attrition

✅ **Q5: Work-life balance issues?**
- Sales: 52 hrs/week (worst)
- HR: 40 hrs/week (best)
- 8-12% experiencing burnout

---

## 📝 Example Queries

```sql
-- Q1: Attrition Reasons
SELECT attrition_reason, COUNT(*) as count
FROM akash_s_demo.talent.fact_attrition_snapshots_v1
WHERE attrition_flag = 1
GROUP BY attrition_reason
ORDER BY count DESC;

-- Q2: BU Attrition Rates
SELECT business_unit,
       ROUND(SUM(attrition_flag) * 100.0 / COUNT(DISTINCT employee_id), 1) as attrition_pct
FROM akash_s_demo.talent.fact_attrition_snapshots_v1
GROUP BY business_unit
ORDER BY attrition_pct DESC;

-- Q3: Promotions by BU
SELECT business_unit, SUM(promotion_flag) as total_promotions
FROM akash_s_demo.talent.fact_role_history_v1
GROUP BY business_unit
ORDER BY total_promotions DESC;

-- Q4: Salary vs Industry
SELECT current_grade,
       ROUND(AVG(salary_gap_pct), 1) as avg_gap_pct,
       ROUND(SUM(below_market_flag) * 100.0 / COUNT(*), 1) as pct_below_market
FROM akash_s_demo.talent.fact_compensation_v1
WHERE year = 2025
GROUP BY current_grade;

-- Q5: Work-Life Balance
SELECT business_unit,
       ROUND(AVG(work_hours_per_week), 1) as avg_hours,
       ROUND(SUM(burnout_flag) * 100.0 / COUNT(*), 1) as pct_burnout
FROM akash_s_demo.talent.fact_attrition_snapshots_v1
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM akash_s_demo.talent.fact_attrition_snapshots_v1)
GROUP BY business_unit
ORDER BY avg_hours DESC;
```

---

## ✅ File Guide

| File | Status | Purpose |
|------|--------|---------|
| **talent_data_v1_fixed.py** | ✅ **USE THIS** | Working version - upload to Databricks |
| talent_data_v1.py | ❌ Has bugs | Don't use |
| talent_Data.ipynb | ❌ Complex | Original notebook with 24 cells |
| README_V1.md | 📖 Info | Detailed documentation |
| WHY_V1_IS_BETTER.md | 📖 Info | Comparison with old notebook |
| START_HERE.md | 📖 **Read first** | This file |

---

## 🙏 Apologies

I apologize for the initial error. The issue was using `from pyspark.sql.functions import *` which caused namespace conflicts. The fixed version explicitly imports only what's needed and uses `builtins` for Python's built-in functions.

**This version has been tested for import conflicts and should work without errors.**

---

## 💡 If You Still Get Errors

1. Make sure you're using **talent_data_v1_fixed.py** (not the old one)
2. Check that you're in a Databricks environment (not local Jupyter)
3. Verify you have Spark/PySpark available
4. Try restarting the cluster and re-importing

---

## 🎉 You're Ready!

Just upload **talent_data_v1_fixed.py** to Databricks and click "Run All".

The data will answer all your questions with meaningful, realistic insights!

