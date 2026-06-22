"""
Glue Job: Ingest Raw Data
=========================
Reads raw CSV files, cleans data, and writes to staging as Parquet.
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql.functions import col, trim
import re

args = getResolvedOptions(sys.argv, ["JOB_NAME", "source_path", "target_path", "data_type"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

print(f"Reading data from: {args['source_path']}")
df = spark.read.option("header", "true") \
              .option("inferSchema", "true") \
              .option("sep", ";") \
              .csv(args["source_path"])

print(f"Original columns: {df.columns}")

# Clean column names - remove all special characters
cleaned_cols = []
for c in df.columns:
    # Remove quotes, brackets, and other special chars, keep only alphanumeric and underscore
    clean_name = re.sub(r'[^a-zA-Z0-9_.]', '', c)
    # Replace dots with underscores
    clean_name = clean_name.replace('.', '_')
    cleaned_cols.append(clean_name)
    print(f"Column: '{c}' -> '{clean_name}'")

df = df.toDF(*cleaned_cols)
print(f"Cleaned columns: {df.columns}")

# Show first few rows
df.show(5, truncate=False)

# Data cleaning
df_cleaned = df.dropDuplicates()

# Check if required columns exist after cleaning
if 'age' in df_cleaned.columns and 'job' in df_cleaned.columns and 'y' in df_cleaned.columns:
    df_cleaned = df_cleaned.dropna(subset=['age', 'job', 'y'])
    print(f"Filtered on required columns")
else:
    print(f"Warning: Required columns not found. Available: {df_cleaned.columns}")

# Trim whitespace from string columns
string_cols = [f.name for f in df_cleaned.schema.fields if str(f.dataType) == 'StringType']
for col_name in string_cols:
    df_cleaned = df_cleaned.withColumn(col_name, trim(col(col_name)))

print(f"Original row count: {df.count()}")
print(f"Cleaned row count: {df_cleaned.count()}")
print(f"Final schema:")
df_cleaned.printSchema()

print(f"Writing to: {args['target_path']}")
df_cleaned.coalesce(1).write.mode("overwrite").parquet(args["target_path"])

job.commit()
