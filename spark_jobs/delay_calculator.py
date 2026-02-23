"""
spark_jobs/delay_calculator.py
Reads raw BART JSON from staging, flattens the nested structure,
calculates delays, and saves clean data as CSV for Snowflake loading.
"""

import os
import glob
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, DoubleType

# Start Spark Session
spark = SparkSession.builder \
    .appName("BART_DelayCalculator") \
    .master("local[*]") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")  # hide verbose Spark logs
print(" Spark session started")

# Read raw JSON files from staging 
staging_path = "staging/etd/*/*.json"
files = glob.glob(staging_path)

if not files:
    print(" No staged files found. Run bart_client.py first!")
    exit()

print(f"📂 Found {len(files)} staged file(s)")

raw_df = spark.read \
    .option("multiline", "true") \
    .json(staging_path)

print(f"Raw schema:")
raw_df.printSchema()

# Flatten station → etd → estimate (3 levels deep)
# Level 1: explode stations (one row per station)
stations_df = raw_df.select(
    F.col("ingested_at"),
    F.col("feed_type"),
    F.explode("payload.root.station").alias("station")
)

# Level 2: explode etd (one row per destination per station)
etd_df = stations_df.select(
    F.col("ingested_at"),
    F.col("station.name").alias("station_name"),
    F.col("station.abbr").alias("station_abbr"),
    F.explode("station.etd").alias("etd")
)

# Level 3: explode estimate (one row per train)
trains_df = etd_df.select(
    F.col("ingested_at"),
    F.col("station_name"),
    F.col("station_abbr"),
    F.col("etd.destination").alias("destination"),
    F.col("etd.abbreviation").alias("destination_abbr"),
    F.explode("etd.estimate").alias("est")
).select(
    F.col("ingested_at"),
    F.col("station_name"),
    F.col("station_abbr"),
    F.col("destination"),
    F.col("destination_abbr"),
    F.when(F.col("est.minutes") == "Leaving", 0)
 .otherwise(F.col("est.minutes").cast(IntegerType()))
 .alias("minutes_to_departure"),
    F.col("est.delay").cast(IntegerType()).alias("delay_seconds"),
    F.col("est.platform").alias("platform"),
    F.col("est.direction").alias("direction"),
    F.col("est.color").alias("line_color"),
    F.col("est.length").cast(IntegerType()).alias("train_cars"),
)

#  Add calculated columns
processed_df = trains_df.withColumns({
    # Convert delay to minutes
    "delay_minutes": F.round(
        F.col("delay_seconds") / 60, 2
    ).cast(DoubleType()),

    # Flag as delayed if > 2 minutes (120 seconds)
    "is_delayed": F.when(
        F.col("delay_seconds") > 120, "Yes"
    ).otherwise("No"),

    # Categorize delay severity
    "delay_category": F.when(F.col("delay_seconds") == 0, "On Time")
                       .when(F.col("delay_seconds") <= 120, "Minor")
                       .when(F.col("delay_seconds") <= 300, "Moderate")
                       .otherwise("Severe"),

    # Extract date and hour for partitioning
    "ingestion_date": F.to_date("ingested_at"),
    "ingestion_hour": F.hour(F.to_timestamp("ingested_at")),
})

# Show sample output 
print("\n Sample processed trains:")
processed_df.select(
    "station_name", "destination", "line_color",
    "minutes_to_departure", "delay_seconds", "delay_minutes",
    "is_delayed", "delay_category"
).show(20, truncate=False)

# Summary stats 
print(" Delay summary by line:")
processed_df.groupBy("line_color").agg(
    F.count("*").alias("total_trains"),
    F.sum(F.when(F.col("is_delayed") == "Yes", 1).otherwise(0)).alias("delayed"),
    F.round(F.avg("delay_seconds"), 1).alias("avg_delay_sec"),
    F.max("delay_seconds").alias("max_delay_sec"),
).orderBy("avg_delay_sec", ascending=False).show()

# Save clean data to CSV for Snowflake
output_path = "staging/processed/"
processed_df.coalesce(1).write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv(output_path)

print(f"Clean data saved to {output_path}")
spark.stop()