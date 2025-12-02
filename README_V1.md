# 🎯 Talent Data V1 - Clean, Working Solution

## What is This?

A **brand new, clean notebook** that generates all 5 tables with "_v1" suffix. No errors, no complexity - just working code.

## 📊 What It Generates

1. **dim_employees_v1** (2,000 employees with full profile)
2. **fact_role_history_v1** (~20,000 role changes with promotions)
3. **fact_performance_v1** (22,000 yearly ratings)
4. **fact_compensation_v1** (22,000 salary records with industry comparison)
5. **fact_attrition_snapshots_v1** (~65,000 monthly snapshots with WLB metrics)

## 🎯 Your 5 Questions - Answered!

This data is **specifically designed** to answer:

1. **What are major reasons for attrition?**
   - ✅ Low Pay: ~30-35%
   - ✅ Work-Life Balance: ~15-20%
   - ✅ Career Stagnation: ~15-20%
   - ✅ Manager Issues: ~20-25%

2. **Which BU has highest attrition?**
   - ✅ Sales: 28%
   - ✅ Customer Success: 22%
   - ✅ Operations: 18%
   - ✅ Engineering: 15%
   - ✅ Finance: 12%
   - ✅ HR: 10%

3. **How many employees are promoted in each BU?**
   - ✅ Engineering: ~80-100 promotions/year
   - ✅ Sales: ~60-75
   - ✅ Operations: ~50-60
   - ✅ Customer Success: ~40-50
   - ✅ Finance: ~35-45
   - ✅ HR: ~25-35

4. **Are salaries on par with industry?**
   - ✅ 30-40% of employees are paid below market
   - ✅ Clear correlation: below_market_flag → higher attrition
   - ✅ Industry benchmarks built-in for comparison

5. **Do we have work-life balance issues?**
   - ✅ Sales: 52 hrs/week (worst)
   - ✅ HR: 40 hrs/week (best)
   - ✅ 8-12% experiencing burnout
   - ✅ Clear correlation: burnout → 3x higher attrition

## 🚀 How to Use

### Step 1: Import to Databricks

**Option A: Import Python File**
1. Go to Databricks Workspace
2. Click "Import"
3. Upload `talent_data_v1.py`
4. It will convert to a notebook automatically

**Option B: Create New Notebook**
1. Create a new Python notebook in Databricks
2. Copy the content from `talent_data_v1.py`
3. Paste into cells

### Step 2: Run

1. Open the notebook
2. Click **"Run All"**
3. Wait ~10-15 minutes
4. Done! ✅

### Step 3: Query Your Data

```sql
-- Q1: Major reasons for attrition
SELECT attrition_reason, COUNT(*) as count
FROM akash_s_demo.talent.fact_attrition_snapshots_v1
WHERE attrition_flag = 1
GROUP BY attrition_reason
ORDER BY count DESC;

-- Q2: BU with highest attrition
SELECT business_unit,
       ROUND(SUM(attrition_flag) * 100.0 / COUNT(DISTINCT employee_id), 1) as attrition_pct
FROM akash_s_demo.talent.fact_attrition_snapshots_v1
GROUP BY business_unit
ORDER BY attrition_pct DESC;

-- Q3: Promotions per BU
SELECT business_unit, SUM(promotion_flag) as total_promotions
FROM akash_s_demo.talent.fact_role_history_v1
GROUP BY business_unit
ORDER BY total_promotions DESC;

-- Q4: Salary vs industry
SELECT current_grade,
       ROUND(AVG(salary_gap_pct), 1) as avg_gap_pct,
       ROUND(SUM(below_market_flag) * 100.0 / COUNT(*), 1) as pct_below_market
FROM akash_s_demo.talent.fact_compensation_v1
WHERE year = 2025
GROUP BY current_grade;

-- Q5: Work-life balance by BU
SELECT business_unit,
       ROUND(AVG(work_hours_per_week), 1) as avg_hours,
       ROUND(SUM(burnout_flag) * 100.0 / COUNT(*), 1) as pct_burnout
FROM akash_s_demo.talent.fact_attrition_snapshots_v1
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM akash_s_demo.talent.fact_attrition_snapshots_v1)
GROUP BY business_unit
ORDER BY avg_hours DESC;
```

## ✨ Key Features

### Built-In from Start
- ✅ BU-specific attrition rates
- ✅ Logic-based attrition reasons (not random!)
- ✅ Meaningful promotions (250-350/year)
- ✅ Industry salary comparison
- ✅ Work-life balance metrics
- ✅ Burnout indicators
- ✅ Career stagnation flags

### No Errors
- ✅ All column names are consistent
- ✅ No cell dependency issues
- ✅ Clean, simple code
- ✅ Works in one run

## 📊 Data Quality

### Realistic Patterns
- Attrition reasons correlate with:
  - Below-market pay → "Low Pay"
  - High work hours + stress → "Work-Life Balance"
  - No promotions + tenure >3yr → "Career Stagnation"

### BU Differentiation
- Sales: High attrition (28%), long hours (52/week)
- HR: Low attrition (10%), good hours (40/week)
- Engineering: Medium attrition (15%), best promotions

### Industry Benchmarking
- Internal salaries: 4-10% below market on average
- 30-40% of employees are significantly below market (<-10%)
- Clear correlation with attrition

## 🎓 What's Different from Old Notebook?

| Old (talent_Data.ipynb) | New (talent_data_v1.py) |
|-------------------------|-------------------------|
| 24 cells with complex dependencies | 8 clean, simple cells |
| Column name conflicts | Consistent naming |
| Enhancements added later | Built-in from start |
| Errors with cell order | Works in any order |
| Complex to debug | Simple & clear |

## 🔧 Troubleshooting

**Q: Import failed in Databricks?**
- A: Make sure you select "Python" as the language when importing

**Q: Tables not created?**
- A: Check the output of Cell 8 - it shows write confirmation

**Q: Want to re-run?**
- A: Just click "Run All" again - it will overwrite tables

**Q: Need different parameters?**
- A: Edit Cell 1 (Configuration) - change NUM_EMPLOYEES, YEARS, etc.

## ✅ Success Indicators

After running, you should see:

```
📊 Table Counts:
  dim_employees_v1: 2000
  fact_role_history_v1: ~20,000
  fact_performance_v1: 22,000
  fact_compensation_v1: 22,000
  fact_attrition_snapshots_v1: ~65,000

✅ ALL TABLES SUCCESSFULLY WRITTEN!
```

## 🎉 You're Done!

Your data is now ready to:
- Answer all 5 key questions
- Provide meaningful insights
- Support your LangGraph agent
- Generate realistic analytics

**Just run it and it works!** 🚀

