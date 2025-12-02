# Databricks notebook source
# MAGIC %md
# MAGIC # 🎯 Talent Analytics - FINAL TESTED VERSION
# MAGIC 
# MAGIC **Tested against serverless with 100 employees, now scaled to 2,000**
# MAGIC 
# MAGIC Generates 5 tables answering your key questions:
# MAGIC 1. What are major reasons for attrition?
# MAGIC 2. Which BU has highest attrition?
# MAGIC 3. How many promotions per BU?
# MAGIC 4. Are salaries competitive with industry?
# MAGIC 5. Do we have work-life balance issues?

# COMMAND ----------

# Setup
from pyspark.sql.functions import *
from pyspark.sql.window import Window
import datetime
import builtins

# Configuration
SEED = 42
NUM_EMPLOYEES = 2000
YEARS = list(range(2020, 2026))
LATEST_YEAR = builtins.max(YEARS)
TODAY = datetime.date.today()

print(f"✅ Configuration: {NUM_EMPLOYEES} employees, {len(YEARS)} years")

# COMMAND ----------

# 1. GENERATE EMPLOYEES
print("=" * 80)
print("📊 STEP 1: Generating Employees")
print("=" * 80)

employees = spark.range(NUM_EMPLOYEES).select(
    concat(lit("EMP"), lpad(col("id"), 6, "0")).alias("employee_id"),
    concat(lit("Employee_"), col("id")).alias("name"),
    when(rand(seed=SEED) < 0.48, lit("Male"))
        .when(rand(seed=SEED) < 0.96, lit("Female"))
        .otherwise(lit("Other")).alias("gender"),
    # Business Units with distribution
    when(rand(seed=SEED+1) < 0.25, lit("Engineering"))
        .when(rand(seed=SEED+1) < 0.45, lit("Sales"))
        .when(rand(seed=SEED+1) < 0.60, lit("Operations"))
        .when(rand(seed=SEED+1) < 0.75, lit("Customer Success"))
        .when(rand(seed=SEED+1) < 0.90, lit("Finance"))
        .otherwise(lit("HR")).alias("business_unit"),
    # Grades
    when(rand(seed=SEED+2) < 0.20, lit("G4"))
        .when(rand(seed=SEED+2) < 0.45, lit("G5"))
        .when(rand(seed=SEED+2) < 0.70, lit("G6"))
        .when(rand(seed=SEED+2) < 0.85, lit("G7"))
        .when(rand(seed=SEED+2) < 0.95, lit("G8"))
        .otherwise(lit("G9")).alias("current_grade"),
    # Regions
    when(rand(seed=SEED+3) < 0.50, lit("India"))
        .when(rand(seed=SEED+3) < 0.75, lit("US"))
        .when(rand(seed=SEED+3) < 0.85, lit("EU"))
        .when(rand(seed=SEED+3) < 0.95, lit("APAC"))
        .otherwise(lit("LATAM")).alias("region"),
    # Dates
    date_add(lit("2010-01-01"), (rand(seed=SEED+4) * 5000).cast("int")).alias("date_of_joining")
).withColumn(
    "tenure_years", round(datediff(current_date(), col("date_of_joining")) / 365, 2)
)

emp_count = employees.count()
print(f"✅ Generated {emp_count} employees")

# COMMAND ----------

# 2. GENERATE ROLE HISTORY (with promotions for Q3)
print("=" * 80)
print("📊 STEP 2: Generating Role History with Promotions")
print("=" * 80)

role_history = employees.select("employee_id", "business_unit", "current_grade", "date_of_joining").withColumn(
    "num_roles", (rand(seed=SEED+10) * 8 + 4).cast("int")  # 4-12 roles
).withColumn(
    "role_id", explode(sequence(lit(1), col("num_roles")))
).select(
    "employee_id",
    "business_unit",
    concat(lit("Role_"), col("role_id")).alias("role"),
    col("current_grade").alias("grade"),
    date_add(col("date_of_joining"), (col("role_id") * 200)).alias("role_start_date"),
    date_add(col("date_of_joining"), (col("role_id") * 200 + 200)).alias("role_end_date")
).withColumn(
    # Promotions higher in Engineering, lower in HR (Q3)
    "promotion_flag",
    when(col("business_unit") == "Engineering", when(rand(seed=SEED+11) < 0.18, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Sales", when(rand(seed=SEED+11) < 0.15, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Operations", when(rand(seed=SEED+11) < 0.12, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Customer Success", when(rand(seed=SEED+11) < 0.10, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Finance", when(rand(seed=SEED+11) < 0.09, lit(1)).otherwise(lit(0)))
        .otherwise(when(rand(seed=SEED+11) < 0.07, lit(1)).otherwise(lit(0)))  # HR
)

role_count = role_history.count()
promo_count = role_history.filter(col("promotion_flag") == 1).count()
print(f"✅ Generated {role_count} role records")
print(f"✅ Total promotions: {promo_count}")

# COMMAND ----------

# 3. GENERATE PERFORMANCE
print("=" * 80)
print("📊 STEP 3: Generating Performance")
print("=" * 80)

years_df = spark.createDataFrame([(y,) for y in YEARS], ["year"])
performance = employees.select("employee_id", "current_grade").crossJoin(years_df).select(
    "employee_id",
    "year",
    (round(rand(seed=SEED+20) * 2.5 + 2.5)).cast("int").alias("rating")
).withColumn(
    "rating", when(col("rating") < 1, lit(1)).when(col("rating") > 5, lit(5)).otherwise(col("rating"))
).withColumn(
    "potential_flag", when((col("rating") >= 4) & (rand(seed=SEED+21) < 0.35), lit(1)).otherwise(lit(0))
).withColumn(
    "rating_3yr_avg", 
    round(avg("rating").over(Window.partitionBy("employee_id").orderBy("year").rowsBetween(-2, 0)), 2)
)

perf_count = performance.count()
print(f"✅ Generated {perf_count} performance records")

# COMMAND ----------

# 4. GENERATE COMPENSATION (with industry comparison for Q4)
print("=" * 80)
print("📊 STEP 4: Generating Compensation with Industry Benchmarks")
print("=" * 80)

compensation = employees.select("employee_id", "current_grade", "region").crossJoin(years_df).select(
    "employee_id",
    "year",
    "current_grade",
    "region",
    # Internal base salaries
    when(col("current_grade") == "G4", lit(400000))
        .when(col("current_grade") == "G5", lit(700000))
        .when(col("current_grade") == "G6", lit(1100000))
        .when(col("current_grade") == "G7", lit(1700000))
        .when(col("current_grade") == "G8", lit(2500000))
        .otherwise(lit(4000000)).alias("base_salary"),
    # Industry benchmarks (higher)
    when(col("current_grade") == "G4", lit(450000))
        .when(col("current_grade") == "G5", lit(750000))
        .when(col("current_grade") == "G6", lit(1150000))
        .when(col("current_grade") == "G7", lit(1700000))
        .when(col("current_grade") == "G8", lit(2600000))
        .otherwise(lit(4200000)).alias("industry_median"),
    # Region multipliers
    when(col("region") == "US", lit(3.5))
        .when(col("region") == "EU", lit(2.5))
        .when(col("region") == "APAC", lit(1.2))
        .when(col("region") == "LATAM", lit(1.1))
        .otherwise(lit(1.0)).alias("region_mult")
).withColumn(
    "salary", (col("base_salary") * col("region_mult") * (1 + rand(seed=SEED+30) * 0.15 - 0.05)).cast("long")
).withColumn(
    "bonus", (col("salary") * (rand(seed=SEED+31) * 0.15 + 0.05)).cast("long")
).withColumn(
    "industry_median_salary", (col("industry_median") * col("region_mult")).cast("long")
).withColumn(
    "salary_gap_pct", round((col("salary") - col("industry_median_salary")) / col("industry_median_salary") * 100, 1)
).withColumn(
    "below_market_flag", when(col("salary_gap_pct") < -10, lit(1)).otherwise(lit(0))
).withColumn(
    "compa_ratio", round(col("salary") / avg("salary").over(Window.partitionBy("current_grade", "year")), 3)
).select(
    "employee_id", "year", "salary", "bonus", "current_grade", "compa_ratio",
    "salary_gap_pct", "below_market_flag", "industry_median_salary"
)

comp_count = compensation.count()
below_market = compensation.filter((col("year") == LATEST_YEAR) & (col("below_market_flag") == 1)).count()
below_market_pct = builtins.round(below_market * 100.0 / NUM_EMPLOYEES, 1)
print(f"✅ Generated {comp_count} compensation records")
print(f"✅ {below_market_pct}% employees below market (target: 30-40%)")

# COMMAND ----------

# 5. GENERATE ATTRITION (with WLB metrics and logic-based reasons for Q1, Q2, Q5)
print("=" * 80)
print("📊 STEP 5: Generating Attrition with WLB & Logic-Based Reasons")
print("=" * 80)

# Get promotion counts
promotions_per_emp = role_history.groupBy("employee_id").agg(
    sum("promotion_flag").alias("total_promotions")
)

# Get latest comp data
latest_comp = compensation.filter(col("year") == LATEST_YEAR).select(
    "employee_id",
    col("compa_ratio").alias("comp_ratio"),
    col("salary_gap_pct").alias("sal_gap"),
    col("below_market_flag").alias("below_market")
)

# Build attrition with all data
attrition = employees.select("employee_id", "business_unit", "current_grade", "tenure_years").join(
    promotions_per_emp, "employee_id", "left"
).join(
    latest_comp, "employee_id", "left"
).na.fill({"total_promotions": 0, "below_market": 0, "comp_ratio": 1.0, "sal_gap": 0.0})

# Add WLB metrics (Q5)
attrition = attrition.withColumn(
    "work_hours_per_week",
    when(col("business_unit") == "Sales", lit(52.0))
        .when(col("business_unit") == "Customer Success", lit(48.0))
        .when(col("business_unit") == "Operations", lit(45.0))
        .when(col("business_unit") == "Engineering", lit(42.0))
        .when(col("business_unit") == "Finance", lit(42.0))
        .otherwise(lit(40.0))  # HR
    + (rand(seed=SEED+42) * 8 - 3)  # Add variation
).withColumn(
    "stress_level", round(col("work_hours_per_week") / 5 - 1, 1)
).withColumn(
    "burnout_flag", when((col("work_hours_per_week") > 55) & (col("stress_level") > 7), lit(1)).otherwise(lit(0))
).withColumn(
    "wlb_score", round(lit(10) - col("stress_level") * 0.8, 1)
)

# BU-specific attrition rates (Q2)
attrition = attrition.withColumn(
    "attrition_flag",
    when(col("business_unit") == "Sales", when(rand(seed=SEED+40) < 0.28, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Customer Success", when(rand(seed=SEED+40) < 0.22, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Operations", when(rand(seed=SEED+40) < 0.18, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Engineering", when(rand(seed=SEED+40) < 0.15, lit(1)).otherwise(lit(0)))
        .when(col("business_unit") == "Finance", when(rand(seed=SEED+40) < 0.12, lit(1)).otherwise(lit(0)))
        .otherwise(when(rand(seed=SEED+40) < 0.10, lit(1)).otherwise(lit(0)))  # HR
)

# Logic-based attrition reasons (Q1)
attrition = attrition.withColumn(
    "attrition_reason",
    when(col("attrition_flag") == 0, lit(None))
        # Priority 1: Low Pay
        .when((col("below_market") == 1) | (col("comp_ratio") < 0.9), lit("Low Pay"))
        # Priority 2: Work-Life Balance (burnout)
        .when(col("burnout_flag") == 1, lit("Work-Life Balance"))
        # Priority 3: Career Stagnation
        .when((col("total_promotions") == 0) & (col("tenure_years") > 3), lit("Career Stagnation"))
        # Priority 4: Manager Issues
        .when(rand(seed=SEED+41) < 0.35, lit("Manager Issues"))
        # Priority 5: WLB (high stress)
        .when((col("work_hours_per_week") > 50) & (col("stress_level") > 6), lit("Work-Life Balance"))
        # Priority 6: Personal
        .when(rand(seed=SEED+42) < 0.50, lit("Personal"))
        # Default: Relocation
        .otherwise(lit("Relocation"))
).withColumn(
    "snapshot_date", current_date()
).withColumn(
    "career_stagnation_flag", when((col("total_promotions") == 0) & (col("tenure_years") > 3), lit(1)).otherwise(lit(0))
).select(
    "employee_id", "snapshot_date", "business_unit", "attrition_flag", "attrition_reason",
    "work_hours_per_week", "stress_level", "burnout_flag", "wlb_score", "career_stagnation_flag"
)

attr_count = attrition.count()
attr_exits = attrition.filter(col("attrition_flag") == 1).count()
print(f"✅ Generated {attr_count} attrition records")
print(f"✅ Total attritions: {attr_exits} ({builtins.round(attr_exits*100.0/NUM_EMPLOYEES, 1)}%)")

# COMMAND ----------

# WRITE ALL TABLES TO DELTA
print("=" * 80)
print("💾 STEP 6: Writing All Tables to Delta")
print("=" * 80)

database = "akash_s_demo.talent"
spark.sql(f"CREATE DATABASE IF NOT EXISTS {database}")

print(f"\nWriting to database: {database}")

employees.write.format("delta").mode("overwrite").saveAsTable(f"{database}.dim_employees_v1")
print("  ✅ dim_employees_v1")

role_history.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_role_history_v1")
print("  ✅ fact_role_history_v1")

performance.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_performance_v1")
print("  ✅ fact_performance_v1")

compensation.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_compensation_v1")
print("  ✅ fact_compensation_v1")

attrition.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_attrition_snapshots_v1")
print("  ✅ fact_attrition_snapshots_v1")

print("\n" + "=" * 80)
print("✅ SUCCESS! All 5 tables created with meaningful data!")
print("=" * 80)
print("\n📊 Summary:")
print(f"  • Employees: {emp_count}")
print(f"  • Role History: {role_count} (Promotions: {promo_count})")
print(f"  • Performance: {perf_count}")
print(f"  • Compensation: {comp_count} ({below_market_pct}% below market)")
print(f"  • Attrition: {attr_count} ({builtins.round(attr_exits*100.0/NUM_EMPLOYEES, 1)}% attrition rate)")
print("\n🎯 Data ready for your 5 key questions!")

