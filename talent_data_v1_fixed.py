# Databricks notebook source
# MAGIC %md
# MAGIC # 🎯 Talent Analytics Data Generator V1 (FIXED)
# MAGIC 
# MAGIC Generates 5 tables with meaningful data to answer key talent questions.

# COMMAND ----------

# Cell 1: Setup and Configuration

from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import (
    col, lit, when, concat, lpad, element_at, array, floor, rand, expr,
    datediff, current_date, round as spark_round, avg, sum, count, countDistinct,
    coalesce, lag, lead, row_number, dense_rank, create_map, to_date,
    desc, asc, explode, sequence
)
from pyspark.sql.window import Window

import uuid
import random
import datetime
import builtins  # To avoid conflicts with PySpark functions

# Configuration
SEED = 42
random.seed(SEED)

spark = SparkSession.builder.appName("TalentAnalytics_V1").getOrCreate()

# Parameters
NUM_EMPLOYEES = 2000
SNAPSHOT_MONTHS = 36
YEARS = list(range(2015, 2026))
LATEST_YEAR = builtins.max(YEARS)  # Use Python's max, not PySpark's max
TODAY = datetime.date.today()
HIRE_START = datetime.date(2010, 1, 1)

# Master Data
REGIONS = ["India", "US", "EU", "APAC", "LATAM"]
BUSINESS_UNITS = ["Engineering", "Sales", "HR", "Finance", "Operations", "Customer Success"]
ROLES = ["Analyst", "Senior Analyst", "Lead Analyst", "Engineer I", "Engineer II", "Senior Engineer", "Manager", "Senior Manager", "Director", "VP"]
GRADES = ["G4", "G5", "G6", "G7", "G8", "G9"]

# BU-Specific Settings (for Q2: Which BU has highest attrition?)
BU_ATTRITION_RATES = {
    "Sales": 0.28,
    "Customer Success": 0.22,
    "Operations": 0.18,
    "Engineering": 0.15,
    "Finance": 0.12,
    "HR": 0.10
}

# Work Hours by BU (for Q5: Work-life balance)
BU_WORK_HOURS = {
    "Sales": 52,
    "Customer Success": 48,
    "Operations": 45,
    "Engineering": 42,
    "Finance": 42,
    "HR": 40
}

# Salary Benchmarks (for Q4: Industry comparison)
INDUSTRY_MEDIAN = {
    "G4": 450000,
    "G5": 750000,
    "G6": 1150000,
    "G7": 1700000,
    "G8": 2600000,
    "G9": 4200000
}

INTERNAL_BASE = {
    "G4": 400000,
    "G5": 700000,
    "G6": 1100000,
    "G7": 1700000,
    "G8": 2500000,
    "G9": 4000000
}

REGION_MULT = {
    "India": 1.0,
    "US": 3.5,
    "EU": 2.5,
    "APAC": 1.2,
    "LATAM": 1.1
}

print("✅ Configuration complete")
print(f"Generating data for {NUM_EMPLOYEES} employees across {len(YEARS)} years")

# COMMAND ----------

# Cell 2: Generate Employees

print("=" * 80)
print("📊 STEP 1: Generating Employees")
print("=" * 80)

employees_df = spark.range(NUM_EMPLOYEES).withColumn(
    "employee_id", concat(lit("EMP"), lpad(col("id").cast("string"), 6, "0"))
).withColumn(
    "name", concat(lit("Employee_"), col("id").cast("string"))
).withColumn(
    "gender", 
    when(rand(seed=SEED) < 0.48, lit("Male"))
    .when(rand(seed=SEED*2) < 0.96, lit("Female"))
    .otherwise(lit("Other"))
).withColumn(
    "region",
    element_at(array([lit(r) for r in REGIONS]), (floor(rand(seed=SEED+1) * len(REGIONS)) + 1).cast("int"))
).withColumn(
    "business_unit",
    element_at(array([lit(b) for b in BUSINESS_UNITS]), (floor(rand(seed=SEED+2) * len(BUSINESS_UNITS)) + 1).cast("int"))
).withColumn(
    "current_role",
    element_at(array([lit(r) for r in ROLES]), (floor(rand(seed=SEED+3) * len(ROLES)) + 1).cast("int"))
).withColumn(
    "current_grade",
    element_at(array([lit(g) for g in GRADES]), (floor(rand(seed=SEED+4) * len(GRADES)) + 1).cast("int"))
).withColumn(
    "date_of_joining",
    expr(f"date_add('{HIRE_START.isoformat()}', cast(floor(rand(seed={SEED+5})*{(TODAY - HIRE_START).days}) as int))")
).withColumn(
    "tenure_years",
    spark_round(datediff(current_date(), col("date_of_joining")) / 365.0, 2)
)

# Assign managers
num_managers = builtins.max(60, NUM_EMPLOYEES // 12)
manager_ids = [row.employee_id for row in employees_df.orderBy(rand(seed=SEED+6)).limit(num_managers).collect()]

employees_df = employees_df.withColumn(
    "manager_id",
    when(rand(seed=SEED+7) < 0.03, lit(None))
    .otherwise(element_at(array([lit(m) for m in manager_ids]), (floor(rand(seed=SEED+8) * len(manager_ids)) + 1).cast("int")))
).drop("id")

print(f"✅ Generated {employees_df.count()} employees")
display(employees_df.limit(5))

# COMMAND ----------

# Cell 3: Generate Role History with Promotions

print("=" * 80)
print("📊 STEP 2: Generating Role History with Promotions")
print("=" * 80)

# Generate 5-15 role changes per employee
role_history = employees_df.select("employee_id", "date_of_joining", "business_unit").withColumn(
    "num_roles",
    (floor(rand(seed=SEED+10) * 11) + 5).cast("int")
).withColumn(
    "pos", explode(sequence(lit(1), col("num_roles")))
)

w_role = Window.partitionBy("employee_id").orderBy("pos")

role_history = role_history.withColumn(
    "months_in_role", (floor(rand(seed=SEED+11) * 25) + 6).cast("int")
).withColumn(
    "cum_months", coalesce(sum("months_in_role").over(w_role.rowsBetween(Window.unboundedPreceding, -1)), lit(0))
).withColumn(
    "role_start_date", expr("date_add(date_of_joining, cast(cum_months*30 as int))")
).withColumn(
    "role_end_date_temp", expr("date_add(role_start_date, cast(months_in_role*30 as int))")
).withColumn(
    "role_end_date", when(col("role_end_date_temp") > current_date(), lit(None)).otherwise(col("role_end_date_temp"))
).withColumn(
    "role", element_at(array([lit(r) for r in ROLES]), (floor(rand(seed=SEED+12) * len(ROLES)) + 1).cast("int"))
).withColumn(
    "grade", element_at(array([lit(g) for g in GRADES]), (floor(rand(seed=SEED+13) * len(GRADES)) + 1).cast("int"))
)

# Grade progression and promotions
grade_rank_map = {"G4": 4, "G5": 5, "G6": 6, "G7": 7, "G8": 8, "G9": 9}
grade_rank_expr = create_map([lit(x) for pair in grade_rank_map.items() for x in pair])

bu_promo_mult = {"Engineering": 1.8, "Sales": 1.5, "Operations": 1.2, "Customer Success": 1.0, "Finance": 0.9, "HR": 0.7}
bu_promo_expr = create_map([lit(x) for pair in bu_promo_mult.items() for x in pair])

role_history = role_history.withColumn(
    "grade_rank", grade_rank_expr[col("grade")]
).withColumn(
    "prev_grade_rank", lag("grade_rank").over(w_role)
).withColumn(
    "bu_promo_factor", bu_promo_expr[col("business_unit")]
).withColumn(
    "promotion_flag",
    when(
        (col("prev_grade_rank").isNotNull()) & 
        (col("grade_rank") > col("prev_grade_rank")) & 
        (rand(seed=SEED+14) < lit(0.15) * col("bu_promo_factor")),
        lit(1)
    ).otherwise(lit(0))
)

role_history_v1 = role_history.select(
    "employee_id", "role", "grade", "role_start_date", "role_end_date", "business_unit", "promotion_flag"
).withColumn(
    "time_in_role_days", datediff(coalesce(col("role_end_date"), current_date()), col("role_start_date"))
)

total_promotions = role_history_v1.filter(col("promotion_flag") == 1).count()
print(f"✅ Generated {role_history_v1.count()} role history records")
print(f"✅ Total promotions: {total_promotions}")

# COMMAND ----------

# Cell 4: Generate Performance

print("=" * 80)
print("📊 STEP 3: Generating Performance Data")
print("=" * 80)

years_df = spark.createDataFrame([(y,) for y in YEARS], ["year"])
perf_df = employees_df.select("employee_id", "current_grade", "manager_id").crossJoin(years_df)

grade_bias = {"G4": -0.2, "G5": -0.1, "G6": 0.0, "G7": 0.1, "G8": 0.2, "G9": 0.3}
grade_bias_expr = create_map([lit(x) for pair in grade_bias.items() for x in pair])

perf_df = perf_df.withColumn(
    "rating_raw", spark_round(rand(seed=SEED+20) * 1.8 + lit(3) + grade_bias_expr[col("current_grade")], 0).cast("int")
).withColumn(
    "rating",
    when(col("rating_raw") < 1, lit(1))
    .when(col("rating_raw") > 5, lit(5))
    .otherwise(col("rating_raw"))
).withColumn(
    "potential_flag", when((col("rating") >= 4) & (rand(seed=SEED+21) < 0.35), lit(1)).otherwise(lit(0))
).withColumnRenamed("manager_id", "reviewer_id")

w_perf = Window.partitionBy("employee_id").orderBy("year").rowsBetween(-2, 0)
fact_performance_v1 = perf_df.withColumn(
    "rating_3yr_avg", spark_round(avg("rating").over(w_perf), 2)
).select("employee_id", "year", "rating", "rating_3yr_avg", "potential_flag", "reviewer_id")

print(f"✅ Generated {fact_performance_v1.count()} performance records")
display(fact_performance_v1.limit(5))

# COMMAND ----------

# Cell 5: Generate Compensation with Industry Comparison

print("=" * 80)
print("📊 STEP 4: Generating Compensation with Industry Benchmarks")
print("=" * 80)

comp_df = employees_df.select("employee_id", "current_grade", "region").crossJoin(years_df)

internal_base_expr = create_map([lit(x) for pair in INTERNAL_BASE.items() for x in pair])
industry_median_expr = create_map([lit(x) for pair in INDUSTRY_MEDIAN.items() for x in pair])
region_mult_expr = create_map([lit(x) for pair in REGION_MULT.items() for x in pair])

min_year = builtins.min(YEARS)

comp_df = comp_df.withColumn(
    "salary",
    (internal_base_expr[col("current_grade")] * 
     region_mult_expr[col("region")] * 
     (lit(1) + lit(0.045) * (col("year") - lit(min_year))) *
     (lit(1) + rand(seed=SEED+30) * 0.12 - 0.04)).cast("long")
).withColumn(
    "bonus",
    (col("salary") * (lit(0.03) + rand(seed=SEED+31) * 0.17)).cast("long")
).withColumn(
    "industry_median_salary",
    (industry_median_expr[col("current_grade")] * region_mult_expr[col("region")]).cast("long")
).withColumn(
    "salary_gap_pct",
    spark_round((col("salary") - col("industry_median_salary")) / col("industry_median_salary") * 100, 1)
).withColumn(
    "below_market_flag",
    when(col("salary_gap_pct") < -10, lit(1)).otherwise(lit(0))
)

# Compa ratio
w_comp = Window.partitionBy("current_grade", "year")
comp_df = comp_df.withColumn(
    "compa_ratio", spark_round(col("salary") / avg("salary").over(w_comp), 3)
)

# Salary growth
w_salary = Window.partitionBy("employee_id").orderBy("year")
fact_compensation_v1 = comp_df.withColumn(
    "salary_prev", lag("salary").over(w_salary)
).withColumn(
    "salary_growth_pct",
    spark_round(
        when(col("salary_prev").isNotNull(), (col("salary") - col("salary_prev")) / col("salary_prev") * 100)
        .otherwise(lit(0)), 2
    )
).select(
    "employee_id", "year", "salary", "bonus", "current_grade", "region",
    "compa_ratio", "salary_growth_pct", "industry_median_salary", "salary_gap_pct", "below_market_flag"
)

print(f"✅ Generated {fact_compensation_v1.count()} compensation records")
print(f"\\n📊 Below Market Analysis (Latest Year):")
fact_compensation_v1.filter(col("year") == LATEST_YEAR).agg(
    spark_round(sum("below_market_flag") * 100.0 / count("*"), 1).alias("pct_below_market")
).show()

# COMMAND ----------

# Cell 6: Generate Attrition with WLB and Logic-Based Reasons

print("=" * 80)
print("📊 STEP 5: Generating Attrition Snapshots")
print("=" * 80)

# Create monthly snapshots
start_date = TODAY - datetime.timedelta(days=30 * (SNAPSHOT_MONTHS - 1))
months = [(start_date + datetime.timedelta(days=30*i)).isoformat() for i in range(SNAPSHOT_MONTHS)]
months_df = spark.createDataFrame([(m,) for m in months], ["snapshot_date_str"]).withColumn(
    "snapshot_date", to_date(col("snapshot_date_str"))
).drop("snapshot_date_str")

snapshots = employees_df.select(
    "employee_id", "date_of_joining", "business_unit", "current_grade", "manager_id", "tenure_years"
).crossJoin(months_df).filter(
    col("snapshot_date") >= col("date_of_joining")
)

# Assign exits based on BU-specific rates
bu_attr_expr = create_map([lit(x) for pair in BU_ATTRITION_RATES.items() for x in pair])
snapshots = snapshots.withColumn(
    "will_exit", when(rand(seed=SEED+40) < bu_attr_expr[col("business_unit")], lit(1)).otherwise(lit(0))
)

# Assign exit month for those who will exit
w_snap = Window.partitionBy("employee_id").orderBy("snapshot_date")
snapshots = snapshots.withColumn(
    "total_months", count("*").over(Window.partitionBy("employee_id"))
).withColumn(
    "exit_month_idx", (floor(rand(seed=SEED+41) * col("total_months")) + 1).cast("int")
).withColumn(
    "row_num", row_number().over(w_snap)
).withColumn(
    "attrition_flag",
    when((col("will_exit") == 1) & (col("row_num") == col("exit_month_idx")), lit(1)).otherwise(lit(0))
).withColumn(
    "exit_date", when(col("attrition_flag") == 1, col("snapshot_date")).otherwise(lit(None))
)

# Work-Life Balance metrics
bu_hours_expr = create_map([lit(x) for pair in BU_WORK_HOURS.items() for x in pair])
grade_hours_add = {"G4": 0, "G5": 2, "G6": 2, "G7": 4, "G8": 6, "G9": 8}
grade_hours_expr = create_map([lit(x) for pair in grade_hours_add.items() for x in pair])

snapshots = snapshots.withColumn(
    "work_hours_per_week",
    spark_round(
        bu_hours_expr[col("business_unit")] + 
        grade_hours_expr[col("current_grade")] + 
        rand(seed=SEED+42) * 10 - 3, 1
    )
).withColumn(
    "overtime_hours_per_month",
    when(col("work_hours_per_week") > 40, ((col("work_hours_per_week") - 40) * 4).cast("int")).otherwise(lit(0))
).withColumn(
    "stress_level",
    spark_round(
        when(col("work_hours_per_week") > 55, lit(8.0) + rand(seed=SEED+43) * 2)
        .when(col("work_hours_per_week") > 50, lit(6.0) + rand(seed=SEED+44) * 2)
        .when(col("work_hours_per_week") > 45, lit(4.0) + rand(seed=SEED+45) * 2)
        .otherwise(lit(2.0) + rand(seed=SEED+46) * 2), 1
    )
).withColumn(
    "burnout_flag",
    when((col("work_hours_per_week") > 55) & (col("stress_level") > 7), lit(1)).otherwise(lit(0))
).withColumn(
    "wlb_score", spark_round(lit(10) - col("stress_level") * 0.8, 1)
)

# Join with comp and mobility for logic-based reasons
latest_comp = fact_compensation_v1.filter(col("year") == LATEST_YEAR).select(
    "employee_id",
    col("compa_ratio").alias("comp_ratio"),
    col("salary_gap_pct").alias("sal_gap"),
    col("below_market_flag").alias("below_market")
)

mobility = role_history_v1.groupBy("employee_id").agg(
    sum("promotion_flag").alias("total_promotions")
)

snapshots_enriched = snapshots.join(latest_comp, "employee_id", "left").join(mobility, "employee_id", "left").na.fill({
    "total_promotions": 0,
    "below_market": 0,
    "comp_ratio": 1.0,
    "sal_gap": 0.0
})

# Logic-based attrition reasons
fact_attrition_snapshots_v1 = snapshots_enriched.withColumn(
    "attrition_reason",
    when(col("attrition_flag") == 0, lit(None))
    .when((col("below_market") == 1) | ((col("comp_ratio") < 0.9) & (col("sal_gap") < -5)), lit("Low Pay"))
    .when(col("burnout_flag") == 1, lit("Work-Life Balance"))
    .when((col("total_promotions") == 0) & (col("tenure_years") > 3), lit("Career Stagnation"))
    .when(rand(seed=SEED+50) < 0.35, lit("Manager Issues"))
    .when((col("work_hours_per_week") > 50) & (col("stress_level") > 6), lit("Work-Life Balance"))
    .when(rand(seed=SEED+51) < 0.50, lit("Personal"))
    .otherwise(lit("Relocation"))
).withColumn(
    "notice_period_days",
    when(col("attrition_flag") == 1,
         element_at(array(lit(0), lit(15), lit(30), lit(60), lit(90)), 
                   (floor(rand(seed=SEED+52) * 5) + 1).cast("int"))
    ).otherwise(lit(None))
).withColumn(
    "career_stagnation_flag",
    when((col("total_promotions") == 0) & (col("tenure_years") > 3), lit(1)).otherwise(lit(0))
).withColumn(
    "attrition_risk_score",
    spark_round(
        lit(0.03) +
        when(col("tenure_years") < 1, 0.15).otherwise(0.0) +
        when(col("career_stagnation_flag") == 1, 0.12).otherwise(0.0) +
        when(col("total_promotions") == 0, 0.08).otherwise(0.0) +
        when(col("below_market") == 1, 0.18).otherwise(0.0) +
        when(col("burnout_flag") == 1, 0.15).otherwise(0.0), 3
    )
).select(
    "employee_id", "snapshot_date", "business_unit", "attrition_flag", "exit_date",
    "attrition_reason", "notice_period_days", "work_hours_per_week", "overtime_hours_per_month",
    "stress_level", "burnout_flag", "wlb_score", "career_stagnation_flag",
    "attrition_risk_score", "manager_id"
)

print(f"✅ Generated {fact_attrition_snapshots_v1.count()} attrition snapshots")

# COMMAND ----------

# Cell 7: Build Enriched Employees Dimension

print("=" * 80)
print("📊 STEP 6: Building dim_employees_v1")
print("=" * 80)

latest_snapshot_date = builtins.max(months)

latest_comp_full = fact_compensation_v1.filter(col("year") == LATEST_YEAR).select(
    "employee_id",
    col("salary").alias("current_salary"),
    col("bonus").alias("current_bonus"),
    "compa_ratio",
    "salary_growth_pct",
    "industry_median_salary",
    "salary_gap_pct",
    "below_market_flag"
)

latest_perf = fact_performance_v1.filter(col("year") == LATEST_YEAR).select(
    "employee_id",
    col("rating").alias("latest_rating"),
    col("rating_3yr_avg").alias("latest_rating_3yr_avg"),
    "potential_flag"
)

latest_snapshot = fact_attrition_snapshots_v1.filter(col("snapshot_date") == lit(latest_snapshot_date)).select(
    "employee_id",
    col("attrition_flag").alias("has_exited"),
    "exit_date",
    "attrition_reason",
    "work_hours_per_week",
    "stress_level",
    "burnout_flag",
    "wlb_score",
    "attrition_risk_score"
)

mobility_agg = role_history_v1.groupBy("employee_id").agg(
    count("*").alias("total_role_changes"),
    sum("promotion_flag").alias("total_promotions")
)

dim_employees_v1 = employees_df.join(
    latest_comp_full, "employee_id", "left"
).join(
    latest_perf, "employee_id", "left"
).join(
    latest_snapshot, "employee_id", "left"
).join(
    mobility_agg, "employee_id", "left"
).na.fill({
    "total_role_changes": 1,
    "total_promotions": 0,
    "has_exited": 0,
    "latest_rating": 3,
    "latest_rating_3yr_avg": 3.0,
    "potential_flag": 0,
    "burnout_flag": 0,
    "work_hours_per_week": 42.0,
    "stress_level": 4.0,
    "wlb_score": 6.0,
    "below_market_flag": 0
})

# Manager aggregates
manager_perf = fact_performance_v1.filter(col("year") == LATEST_YEAR).groupBy("reviewer_id").agg(
    spark_round(avg("rating"), 2).alias("manager_avg_team_rating"),
    count("*").alias("manager_team_size")
)

manager_attr = fact_attrition_snapshots_v1.filter(col("snapshot_date") == lit(latest_snapshot_date)).groupBy("manager_id").agg(
    sum("attrition_flag").alias("manager_attritions_count"),
    spark_round(sum("attrition_flag") * 100.0 / count("*"), 1).alias("manager_attrition_rate_pct")
)

dim_employees_v1 = dim_employees_v1.join(
    manager_perf, dim_employees_v1.manager_id == manager_perf.reviewer_id, "left"
).drop("reviewer_id").join(
    manager_attr, "manager_id", "left"
).na.fill({
    "manager_avg_team_rating": 3.0,
    "manager_team_size": 0,
    "manager_attritions_count": 0,
    "manager_attrition_rate_pct": 0.0
})

print(f"✅ Built dim_employees_v1 with {dim_employees_v1.count()} employees")
display(dim_employees_v1.limit(5))

# COMMAND ----------

# Cell 8: Write All Tables

print("=" * 80)
print("💾 STEP 7: Writing Tables to Delta")
print("=" * 80)

database = "akash_s_demo.talent"
spark.sql(f"CREATE DATABASE IF NOT EXISTS {database}")

print(f"\\nWriting to database: {database}")
print(f"  → dim_employees_v1...")
dim_employees_v1.write.format("delta").mode("overwrite").saveAsTable(f"{database}.dim_employees_v1")

print(f"  → fact_role_history_v1...")
role_history_v1.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_role_history_v1")

print(f"  → fact_performance_v1...")
fact_performance_v1.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_performance_v1")

print(f"  → fact_compensation_v1...")
fact_compensation_v1.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_compensation_v1")

print(f"  → fact_attrition_snapshots_v1...")
fact_attrition_snapshots_v1.write.format("delta").mode("overwrite").saveAsTable(f"{database}.fact_attrition_snapshots_v1")

print("\\n" + "=" * 80)
print("✅ ALL TABLES SUCCESSFULLY WRITTEN!")
print("=" * 80)
print("\\n📊 Table Summary:")
print(f"  • dim_employees_v1: {dim_employees_v1.count()} employees")
print(f"  • fact_role_history_v1: {role_history_v1.count()} role records")
print(f"  • fact_performance_v1: {fact_performance_v1.count()} performance records")
print(f"  • fact_compensation_v1: {fact_compensation_v1.count()} compensation records")
print(f"  • fact_attrition_snapshots_v1: {fact_attrition_snapshots_v1.count()} snapshot records")
print("\\n🎯 Data is ready for your 5 key questions!")

