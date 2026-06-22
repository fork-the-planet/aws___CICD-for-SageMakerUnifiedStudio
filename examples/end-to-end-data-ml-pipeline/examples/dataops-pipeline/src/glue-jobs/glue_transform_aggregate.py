"""
Glue Job: Transform and Aggregate
=================================
Cleans, enriches, and transforms bank marketing data for ML consumption.
Adds derived features: age_group, contact_intensity, previous_outcome_flag.
"""

import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql.functions import col, when, lit

args = getResolvedOptions(sys.argv, ["JOB_NAME", "staging_path", "analytics_path"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

print(f"Reading from: {args['staging_path']}")
df = spark.read.parquet(args["staging_path"])
print(f"Input rows: {df.count()}, columns: {df.columns}")

# --- Transformations ---

# 1. Age group bucketing
df = df.withColumn("age_group", when(col("age") < 30, "young")
                   .when(col("age") < 50, "middle")
                   .otherwise("senior"))

# 2. Contact intensity flag (contacted more than median ~2 times)
df = df.withColumn("high_contact", when(col("campaign") > 3, 1).otherwise(0))

# 3. Previous outcome binary flag
df = df.withColumn("prev_success", when(col("poutcome") == "success", 1).otherwise(0))

# 4. Filter out unknown job entries (noise reduction)
before = df.count()
df = df.filter(col("job") != "unknown")
print(f"Filtered unknown jobs: {before} -> {df.count()}")

print(f"Output columns: {df.columns}")
print(f"Writing to: {args['analytics_path']}")
df.coalesce(1).write.mode("overwrite").parquet(args["analytics_path"])

job.commit()
