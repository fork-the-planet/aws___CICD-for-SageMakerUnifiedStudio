"""
Glue Job: Data Quality Checks
=============================
Validates data quality on transformed bank marketing data.
Checks: null rates, duplicates, row count, value ranges.
Writes a structured report to S3.
"""

import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql.functions import col, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType

args = getResolvedOptions(sys.argv, [
    "JOB_NAME", "analytics_path", "dq_results_path", "report_date"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

report_date = args["report_date"]
print(f"Reading from: {args['analytics_path']}")
print(f"Report date: {report_date}")

df = spark.read.parquet(args["analytics_path"])
total_rows = df.count()
print(f"Total rows: {total_rows}")

# Consistent schema for all quality results
schema = StructType([
    StructField("check_type", StringType(), False),
    StructField("column_name", StringType(), False),
    StructField("metric_value", DoubleType(), False),
    StructField("threshold", DoubleType(), False),
    StructField("status", StringType(), False),
])

results = []

# Check 1: Null rate per column (threshold: 10%)
for col_name in df.columns:
    null_count = df.filter(col(col_name).isNull()).count()
    null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0
    status = "PASS" if null_pct < 10 else "WARN"
    results.append(("null_rate", col_name, null_pct, 10.0, status))

# Check 2: Duplicate rows (threshold: 0)
dup_count = total_rows - df.dropDuplicates().count()
results.append(("duplicates", "all", float(dup_count), 0.0,
                "PASS" if dup_count == 0 else "WARN"))

# Check 3: Row count (threshold: > 0)
results.append(("row_count", "all", float(total_rows), 1.0,
                "PASS" if total_rows > 0 else "FAIL"))

# Check 4: Age range (17-100)
if "age" in df.columns:
    bad_age = df.filter((col("age") < 17) | (col("age") > 100)).count()
    results.append(("range_check", "age", float(bad_age), 0.0,
                    "PASS" if bad_age == 0 else "WARN"))

# Check 5: Target column has expected values
if "y" in df.columns:
    unexpected = df.filter(~col("y").isin("yes", "no")).count()
    results.append(("value_check", "y", float(unexpected), 0.0,
                    "PASS" if unexpected == 0 else "FAIL"))

results_df = spark.createDataFrame(results, schema)
print("Quality check results:")
results_df.show(truncate=False)

output_path = f"{args['dq_results_path']}/{report_date}/"
print(f"Writing results to: {output_path}")
results_df.coalesce(1).write.mode("overwrite").parquet(output_path)

# Fail on critical issues
failed = results_df.filter(col("status") == "FAIL").count()
if failed > 0:
    raise Exception(f"Data quality failed: {failed} critical issues")

job.commit()
