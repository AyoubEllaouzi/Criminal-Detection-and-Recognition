from pyspark.sql.functions import split, udf
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, upper, trim, lower, when
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
import mysql.connector
import os

os.environ["PYSPARK_SUBMIT_ARGS"] = "--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2 pyspark-shell"


# Create a Spark session


spark = SparkSession.builder \
    .appName("KafkaConsumerApp") \
    .config("spark.driver.extraClassPath", "mysql-connector-java-8.0.30.jar") \
    .getOrCreate()

# Kafka settings
kafka_bootstrap_servers = 'localhost:9092'
kafka_topic = 'test-topic-hadoop-kafka'


# Define Kafka schema
schema = StructType([
    StructField("id", StringType()),
    StructField("STREET", StringType()),
    StructField("OFFENSE_DESCRIPTION", StringType()),
    StructField("OFFENSE_CODE", StringType()),
    StructField("DISTRICT", StringType()),
    StructField("REPORTING_AREA", StringType()),
    StructField("OCCURRED_ON_DATE", StringType()),
    StructField("DAY_OF_WEEK", StringType()),
    StructField("MONTH", StringType()),
    StructField("HOUR", StringType()),
    StructField("YEAR", StringType()),
    StructField("Location", StringType()),
    StructField("Long", StringType()),
    StructField("Lat", StringType()),
    StructField("INCIDENT_NUMBER", StringType()),
    StructField("OFFENSE_CODE_GROUP", StringType()),
    StructField("UCR_PART", StringType()),
    StructField("SHOOTING", IntegerType(), True),
])

# Define Kafka source
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
    .option("subscribe", kafka_topic) \
    .load()

# Convert the value column from Kafka into a string
value_str = df.selectExpr("CAST(value AS STRING)")

# Parse the JSON data into a DataFrame using the specified schema
parsed_df = value_str.select(from_json("value", schema).alias("data")).select("data.*")

#Add a New Colunm CATEGORY that expalian the cluster of his group
parsed_df = parsed_df.withColumn('CATEGORY', split(col("OFFENSE_DESCRIPTION"), "-")[0])

#fill the NULL values by vamlue of three

parsed_df = parsed_df.na.drop(subset=["Location"])

# Universal Crime Reporting Part number (0,1,2) using  Encoding
parsed_df=parsed_df.withColumn("UCR_PART", 
                                     when(col("UCR_PART") == "Part Three",2)
                                    .when(col("UCR_PART") == "Part Two", 1)
                                    .when(col("UCR_PART") == "Part One", 0)
                                    .otherwise(col("UCR_PART")))
#parsed_df=parsed_df.na.drop('UCR_PART')



# drop colunms that's we not use in phase of processing 
parsed_df = parsed_df.drop('OCCURRED_ON_DATE')
parsed_df = parsed_df.drop('SHOOTING')
parsed_df = parsed_df.drop('Long')
parsed_df = parsed_df.drop('Lat')
parsed_df = parsed_df.drop('OFFENSE_CODE_GROUP')
parsed_df.printSchema()
parsed_df=parsed_df.select(['INCIDENT_NUMBER','STREET','OFFENSE_DESCRIPTION','CATEGORY','DISTRICT','UCR_PART','DAY_OF_WEEK','MONTH','YEAR','HOUR','Location'])
#parsed_df=parsed_df.select(['OFFENSE_DESCRIPTION',,])


# Define MySQL connection properties
mysql_properties = {
    "user": "root",
    "password": "",
    "driver": "com.mysql.jdbc.Driver",
    "url": "jdbc:mysql://localhost:3306/TestDB"
}
# Save the DataFrame to MySQL
query0 = parsed_df.writeStream \
    .outputMode("append") \
    .foreachBatch(lambda df, epoch_id: df.write.jdbc(url=mysql_properties["url"],
                                                     table="spark_table",
                                                     mode="append",  # Use "append" or "overwrite" based on your requirement
                                                     properties=mysql_properties)) \
    .start()


query0.awaitTermination()




query = parsed_df \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

# Wait for the query to terminate
query.awaitTermination()