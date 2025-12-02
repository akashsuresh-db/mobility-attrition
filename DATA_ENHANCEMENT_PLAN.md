# 📊 Talent Data Enhancement Plan

## Current Data Analysis

### Existing Tables:
1. **dim_employees** (2,000 employees)
   - 6 Business Units: Engineering, Sales, HR, Finance, Operations, Customer Success
   - 5 Regions: India, US, EU, APAC, LATAM
   - 10 Roles, 6 Grades (G4-G9)

2. **fact_role_history** (Role changes, promotions)
3. **fact_performance** (Yearly ratings)
4. **fact_compensation** (Salary, bonus by year)
5. **fact_attrition_snapshots** (Monthly snapshots, ~18% exit rate)

### Current Issues:
- Attrition reasons are random (not meaningful)
- BU attrition rates may be similar
- Promotion numbers may be too low
- No industry salary comparison
- No work-life balance metrics

---

## 🎯 Enhancements for Your 5 Questions

### 1. **What are major reasons for attrition?**

**Current:** Random reasons with no pattern  
**Enhancement:**
- **Low Pay (35%)** - Correlated with low compa_ratio (<0.9)
- **Manager Issues (25%)** - More common with certain managers
- **Career Stagnation (20%)** - Linked to 0 promotions in 3+ years
- **Work-Life Balance (12%)** - New metric, linked to overtime/stress
- **Personal (5%)** - Random
- **Relocation (3%)** - Random

**Implementation:**
```python
# Logic-based attrition reasons instead of random
attrition_reason = CASE
    WHEN compa_ratio < 0.9 AND salary_growth_pct < 3.0 THEN "Low Pay"
    WHEN manager_has_high_attrition THEN "Manager Issues"
    WHEN mobility_count == 0 AND tenure_years > 3 THEN "Career Stagnation"
    WHEN work_hours_avg > 50 AND stress_level > 7 THEN "Work-Life Balance"
    ELSE random_choice(["Personal", "Relocation"])
```

---

### 2. **Which BU has the highest attrition percentage?**

**Current:** May be uniform across BUs  
**Enhancement:** Create clear differentiation

**Target Attrition Rates by BU:**
- Sales: **28%** (high pressure, commission-based)
- Customer Success: **22%** (burnout, customer demands)
- Operations: **18%** (average)
- Engineering: **15%** (competitive salaries, good retention)
- Finance: **12%** (stable, good pay)
- HR: **10%** (best retention, work-life balance)

**Implementation:**
```python
# BU-specific attrition multipliers
bu_attrition_mult = {
    "Sales": 1.8,
    "Customer Success": 1.4,
    "Operations": 1.2,
    "Engineering": 1.0,
    "Finance": 0.8,
    "HR": 0.6
}

# Assign exits proportionally
exit_prob_by_bu = base_exit_prob * bu_attrition_mult[business_unit]
```

---

### 3. **On average, how many employees are promoted in each BU?**

**Current:** May have low promotion counts  
**Enhancement:** Add meaningful promotion numbers

**Target Annual Promotions per BU:**
- Engineering: **80-100** promotions/year (large, career growth)
- Sales: **60-75** promotions/year (performance-based)
- Operations: **50-60** promotions/year
- Customer Success: **40-50** promotions/year
- Finance: **35-45** promotions/year
- HR: **25-35** promotions/year (smaller team)

**Average Promotion Rate:** 12-15% of employees/year

**Implementation:**
```python
# Ensure each BU has minimum promotions
# Increase promotion_flag probability in role_history
promotion_prob_by_bu = {
    "Engineering": 0.18,  # 18% chance per role change
    "Sales": 0.16,
    "Operations": 0.14,
    "Customer Success": 0.13,
    "Finance": 0.12,
    "HR": 0.10
}

# Also ensure grade progression over time (G4→G5→G6→G7...)
```

---

### 4. **Are salaries on par with industry average? Wage gap leading to attrition?**

**Current:** No industry comparison  
**Enhancement:** Add industry benchmark comparison

**New Columns in fact_compensation:**
- `industry_median_salary` (by grade + region)
- `salary_gap_pct` (your salary vs industry)
- `below_market_flag` (if gap < -10%)

**Industry Benchmarks (by Grade, India base):**
```python
industry_median_by_grade = {
    "G4": 450000,   # vs your avg 400000 (10% below)
    "G5": 750000,   # vs your avg 700000 (7% below)
    "G6": 1150000,  # vs your avg 1100000 (4% below)
    "G7": 1700000,  # on par
    "G8": 2600000,  # vs your avg 2500000 (4% below)
    "G9": 4200000   # vs your avg 4000000 (5% below)
}
```

**Key Insight for Question:**
- **30-40%** of employees are paid **below market** (compa_ratio < 0.9 AND salary_gap < -10%)
- **These employees have 2-3x higher attrition** (60% of "Low Pay" exits)
- **Clear correlation:** Below-market pay → Higher attrition

**Implementation:**
```python
comp_df = comp_df.withColumn(
    "industry_median",
    industry_median_map[grade] * region_mult_map[region]
)
.withColumn(
    "salary_gap_pct",
    round((salary - industry_median) / industry_median * 100, 1)
)
.withColumn(
    "below_market_flag",
    when(col("salary_gap_pct") < -10, lit(1)).otherwise(lit(0))
)

# Correlate with attrition
# below_market employees → 2.5x exit probability
```

---

### 5. **Do we have work-life balance issues leading to attrition?**

**Current:** No work-life balance data  
**Enhancement:** Add new metrics

**New Columns (add to snapshots or new fact table):**
- `work_hours_per_week` (40-70 range)
- `overtime_hours_per_month` (0-60)
- `stress_level` (1-10 scale)
- `burnout_flag` (hours > 55/week AND stress > 7)
- `wlb_score` (1-10, inverse of stress)

**Distribution:**
- **20% of employees** work >55 hours/week (poor WLB)
- **12% have high stress + high hours** (burnout)
- **Work-life balance is #4 attrition reason** (12% of exits)

**BU-Specific WLB Issues:**
- Sales: **Worst WLB** (60% work >50 hrs/week)
- Customer Success: **Poor WLB** (50% work >50 hrs/week)
- Operations: **Average WLB** (35% work >50 hrs/week)
- Engineering: **Better WLB** (25% work >50 hrs/week)
- Finance/HR: **Best WLB** (15% work >50 hrs/week)

**Implementation:**
```python
# Add to fact_attrition_snapshots or new fact_wlb table
wlb_df = emp_df.crossJoin(years_df).withColumn(
    "base_hours",
    when(col("business_unit") == "Sales", 52)
    .when(col("business_unit") == "Customer Success", 48)
    .when(col("business_unit") == "Operations", 45)
    .when(col("business_unit").isin(["Engineering","Finance","HR"]), 42)
    .otherwise(44)
)
.withColumn(
    "work_hours_per_week",
    col("base_hours") + (rand() * 10 - 2)  # +/- variation
)
.withColumn(
    "overtime_hours",
    when(col("work_hours_per_week") > 50, 
         (col("work_hours_per_week") - 40) * 4)  # monthly
    .otherwise(0)
)
.withColumn(
    "stress_level",
    when(col("work_hours_per_week") > 55, 8 + rand())
    .when(col("work_hours_per_week") > 50, 6 + rand() * 2)
    .otherwise(3 + rand() * 3)
)
.withColumn(
    "burnout_flag",
    when((col("work_hours_per_week") > 55) & (col("stress_level") > 7), 1)
    .otherwise(0)
)

# Correlate with attrition
# burnout_flag → 3x exit probability
# attrition_reason = "Work-Life Balance" if burnout_flag == 1
```

---

## 📊 Summary of Changes

### Data Quality Improvements:

1. **Attrition Reasons** → Logic-based (not random)
   - Clear correlation with compa_ratio, mobility, manager, WLB

2. **BU Attrition Rates** → Differentiated (10% to 28%)
   - Sales/CS highest, HR/Finance lowest

3. **Promotions** → Increased to 12-15% annual rate
   - 250-350 total promotions/year across all BUs
   - BU-specific rates (Engineering highest)

4. **Industry Salary Comparison** → New columns added
   - `industry_median_salary`, `salary_gap_pct`, `below_market_flag`
   - 30-40% below market → drives attrition

5. **Work-Life Balance** → New fact table/columns
   - `work_hours_per_week`, `stress_level`, `burnout_flag`
   - 12% of attrition due to WLB
   - Sales/CS have worst WLB

---

## 🎯 Expected Query Results (After Enhancement)

### Q1: Major reasons for attrition?
```
Reason              | Count | Percentage
--------------------|-------|------------
Low Pay             | 126   | 35%
Manager Issues      | 90    | 25%
Career Stagnation   | 72    | 20%
Work-Life Balance   | 43    | 12%
Personal            | 18    | 5%
Relocation          | 11    | 3%
```

### Q2: BU with highest attrition?
```
Business Unit       | Attrition Rate
--------------------|----------------
Sales               | 28%
Customer Success    | 22%
Operations          | 18%
Engineering         | 15%
Finance             | 12%
HR                  | 10%
```

### Q3: Promotions per BU?
```
Business Unit       | Avg Promotions/Year
--------------------|--------------------
Engineering         | 92
Sales               | 68
Operations          | 55
Customer Success    | 45
Finance             | 40
HR                  | 30
```

### Q4: Salary vs Industry?
```
Grade | Our Median | Industry | Gap    | Below Market %
------|------------|----------|--------|----------------
G4    | 400K       | 450K     | -11%   | 45%
G5    | 700K       | 750K     | -7%    | 38%
G6    | 1.1M       | 1.15M    | -4%    | 32%
G7    | 1.7M       | 1.7M     | 0%     | 25%
G8    | 2.5M       | 2.6M     | -4%    | 28%
G9    | 4.0M       | 4.2M     | -5%    | 22%

Correlation: Below-market employees have 2.5x higher attrition
35% of exits due to being paid below industry average
```

### Q5: Work-life balance impact?
```
WLB Category        | % of Employees | Attrition Rate
--------------------|----------------|----------------
Good (≤45 hrs/week) | 45%            | 8%
Average (45-50 hrs) | 35%            | 15%
Poor (50-55 hrs)    | 12%            | 28%
Burnout (>55 hrs)   | 8%             | 45%

By BU:
Sales: 60% work >50 hrs (worst WLB, highest attrition)
HR: 85% work ≤45 hrs (best WLB, lowest attrition)

12% of all attrition is due to work-life balance issues
```

---

## ✅ Approval Needed

**Do you approve this enhancement plan?**

Reply:
- **"yes"** or **"approve"** → I'll create the enhanced data generation code
- **"modify X"** → Tell me what to adjust
- **"different approach"** → Suggest alternative

I'll create a NEW cell at the end of the existing notebook to add these enhancements without breaking the existing data generation.

