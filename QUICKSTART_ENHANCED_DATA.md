# 🚀 Quick Start: Enhanced Talent Data

## What Changed?

Your `talent_Data.ipynb` notebook now includes **7 new enhancement cells (16-23)** that make the data meaningful and realistic.

---

## ⚡ Quick Run Guide

### Option 1: Run All Cells (Recommended for First Time)
1. Open `talent_Data.ipynb` in Databricks
2. Click **"Run All"** at the top
3. Wait ~5-10 minutes for all cells to complete
4. Check Cell 23 output to confirm all tables are written

### Option 2: Run Only Enhancement Cells (If Base Data Exists)
If you already have the base data generated (Cells 1-14), you can run just:
- **Cell 16-23**: Enhancement cells only
- This will update the existing tables with enhanced data

---

## 📋 Cell-by-Cell Breakdown

| Cell | What It Does | Time |
|------|--------------|------|
| 1-2 | Setup + Generate 2,000 employees | ~30s |
| 3-6 | Generate fact tables (role history, performance, compensation, attrition) | ~2-3 min |
| 7-10 | Create enriched employees, validate counts, write to Delta | ~1-2 min |
| 11-14 | Example queries (optional) | ~10s |
| **16** | ✨ **Fix attrition rates by BU (10%-28%)** | ~1 min |
| **17** | ✨ **Apply logic-based attrition reasons** | ~1 min |
| **18** | ✨ **Increase promotion numbers (12-15% rate)** | ~30s |
| **19** | ✨ **Add industry salary comparison** | ~30s |
| **20** | ✨ **Add work-life balance metrics** | ~1 min |
| **21** | ✨ **Refine attrition reasons with WLB + salary** | ~1 min |
| **22** | ✨ **Rebuild enriched employees with all metrics** | ~1 min |
| **23** | ✨ **Write all enhanced tables to Delta** | ~2-3 min |
| 24 | 📖 Summary + SQL queries (markdown, no execution) | - |

**Total Time:** ~10-15 minutes

---

## ✅ Verification Checklist

After running all cells, verify the enhancements worked:

### 1. Check BU Attrition Rates (Should be differentiated)
```python
# Run this in a new cell
display(
    attrition_snap_df.filter(col("snapshot_date") == lit(latest_snapshot))
    .groupBy("business_unit")
    .agg(
        count("*").alias("employees"),
        sum("attrition_flag").alias("attritions"),
        round(sum("attrition_flag") * 100.0 / count("*"), 1).alias("attrition_rate_pct")
    )
    .orderBy(desc("attrition_rate_pct"))
)
```
**Expected:** Sales ~28%, HR ~10%

### 2. Check Attrition Reasons (Should be logic-based)
```python
# Run this in a new cell
display(
    attrition_snap_df.filter(col("attrition_flag") == 1)
    .groupBy("attrition_reason")
    .agg(count("*").alias("count"))
    .withColumn("percentage", round(col("count") * 100.0 / sum("count").over(Window.partitionBy()), 1))
    .orderBy(desc("count"))
)
```
**Expected:** Low Pay ~30-35%, Manager Issues ~20-25%, Work-Life Balance ~15-20%

### 3. Check Promotions (Should be meaningful numbers)
```python
# Run this in a new cell
total_promotions = role_history_df.filter(col("promotion_flag") == 1).count()
print(f"Total promotions: {total_promotions}")
print(f"Expected: 250-350")
```
**Expected:** ~250-350 total promotions

### 4. Check Industry Comparison (Should have below_market_flag)
```python
# Run this in a new cell
below_market_pct = comp_df.filter(col("year") == 2025).agg(
    round(sum("below_market_flag") * 100.0 / count("*"), 1)
).collect()[0][0]
print(f"% Below Market: {below_market_pct}%")
print(f"Expected: 30-40%")
```
**Expected:** 30-40% below market

### 5. Check WLB Metrics (Should have burnout_flag)
```python
# Run this in a new cell
burnout_pct = attrition_snap_df.filter(col("snapshot_date") == lit(latest_snapshot)).agg(
    round(sum("burnout_flag") * 100.0 / count("*"), 1)
).collect()[0][0]
print(f"% Burnout: {burnout_pct}%")
print(f"Expected: 8-12%")
```
**Expected:** 8-12% burnout

---

## 🎯 Test Your 5 Key Questions

After running the notebook, test these queries in SQL or Python:

### Q1: Major reasons for attrition?
```sql
SELECT attrition_reason, COUNT(*) as count, 
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM akash_s_demo.talent.fact_attrition_snapshots
WHERE attrition_flag = 1
GROUP BY attrition_reason
ORDER BY count DESC;
```

### Q2: Which BU has highest attrition?
```sql
SELECT business_unit,
       ROUND(SUM(attrition_flag) * 100.0 / COUNT(DISTINCT employee_id), 1) as attrition_rate_pct
FROM akash_s_demo.talent.fact_attrition_snapshots
GROUP BY business_unit
ORDER BY attrition_rate_pct DESC;
```

### Q3: Promotions per BU?
```sql
SELECT business_unit,
       SUM(promotion_flag) as total_promotions
FROM akash_s_demo.talent.fact_role_history
GROUP BY business_unit
ORDER BY total_promotions DESC;
```

### Q4: Are salaries competitive?
```sql
SELECT 
    'Below Market (<-10%)' as salary_category,
    SUM(CASE WHEN below_market_flag = 1 THEN 1 ELSE 0 END) as employee_count,
    ROUND(SUM(CASE WHEN below_market_flag = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as percentage
FROM akash_s_demo.talent.fact_compensation
WHERE year = 2025;
```

### Q5: Work-life balance issues?
```sql
SELECT 
  business_unit,
  ROUND(AVG(work_hours_per_week), 1) as avg_hours,
  ROUND(SUM(burnout_flag) * 100.0 / COUNT(*), 1) as pct_burnout,
  ROUND(SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as attrition_rate
FROM akash_s_demo.talent.fact_attrition_snapshots
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM akash_s_demo.talent.fact_attrition_snapshots)
GROUP BY business_unit
ORDER BY avg_hours DESC;
```

---

## 🔧 Troubleshooting

### Issue: "Column not found: below_market_flag"
**Solution:** Run enhancement Cell 19 (Industry Salary Comparison) and Cell 23 (Write to Delta)

### Issue: "Column not found: work_hours_per_week"
**Solution:** Run enhancement Cell 20 (Work-Life Balance) and Cell 23 (Write to Delta)

### Issue: "Attrition rates are still uniform across BUs"
**Solution:** Run enhancement Cell 16 (BU-Specific Attrition) and Cell 23 (Write to Delta)

### Issue: "Promotion count is still low (<100 total)"
**Solution:** Run enhancement Cell 18 (Increase Promotions) and Cell 23 (Write to Delta)

### Issue: "Tables not updating in Unity Catalog"
**Solution:** Ensure Cell 23 runs successfully. Check output for confirmation messages.

---

## 📊 New Columns Available

### dim_employees (Enhanced)
- `total_role_changes`: Number of role changes
- `total_promotions`: Number of promotions received
- `current_salary`: Current year salary
- `current_bonus`: Current year bonus
- `current_compa_ratio`: Salary vs grade median
- `below_market_flag`: 1 if paid <10% below industry median
- `salary_gap_pct`: % difference from industry median
- `industry_median_salary`: Industry benchmark for grade+region
- `work_hours_per_week`: Average work hours
- `stress_level`: Stress score (1-10)
- `burnout_flag`: 1 if working >55 hrs/week + stress >7
- `wlb_score`: Work-life balance score (1-10)
- `attrition_risk_score`: Comprehensive attrition risk (0-1)
- `manager_attrition_rate_pct`: Manager's team attrition rate

### fact_compensation (Enhanced)
- `industry_median_salary`: Industry benchmark
- `salary_gap_pct`: % vs industry
- `below_market_flag`: If paid below market

### fact_attrition_snapshots (Enhanced)
- `work_hours_per_week`: Work hours
- `overtime_hours_per_month`: Overtime hours
- `stress_level`: Stress score
- `burnout_flag`: Burnout indicator
- `wlb_score`: WLB score
- `attrition_reason`: Enhanced logic-based reasons

### fact_role_history (Enhanced)
- `promotion_flag`: Now has meaningful numbers (12-15% rate)

---

## 🎉 Success Indicators

You'll know it worked when:
1. ✅ Sales has ~28% attrition, HR has ~10%
2. ✅ "Low Pay" is the #1 attrition reason (~30-35%)
3. ✅ Total promotions are 250-350/year
4. ✅ 30-40% of employees are below market
5. ✅ 8-12% of employees have burnout
6. ✅ Clear correlation: below_market_flag → higher attrition
7. ✅ Clear correlation: burnout_flag → higher attrition

---

## 🚀 Next: Use in LangGraph Agent

Your LangGraph agent can now intelligently answer questions like:
- "Why are people leaving?" → Shows logic-based reasons with correlations
- "Which BU has highest attrition?" → Shows realistic 10%-28% range
- "Are we paying competitively?" → Compares to industry benchmarks
- "Do we have work-life balance issues?" → Shows burnout metrics by BU
- "Who is at risk of leaving?" → Uses comprehensive attrition_risk_score

**Your data is now production-ready! 🎯**

