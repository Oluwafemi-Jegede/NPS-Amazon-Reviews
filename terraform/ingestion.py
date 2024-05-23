import google.auth
from pyspark.sql import SparkSession
from google.cloud import pubsub
import sys
import json

credentials, _ = google.auth.default()


def process_file(spark:SparkSession, file_path:str):
    #Read JSON file and publich to PubSub
    df = spark.read.json(file_path).limit(100)
    df.foreach(publish_row_to_pubsub)
def publish_row_to_pubsub(row):
    # Convert the Row object to a dictionary
    data_dict = row.asDict()
    # Convert the dictionary to a JSON string
    data_json = json.dumps(data_dict)
    # Encode the JSON string to a bytestring
    data_bytes = data_json.encode('utf-8')
    print(f"publish: {data_bytes}")
    # Publish the data to Pub/Sub
    publish_to_pubsub(project_id, topic_name, data_bytes)

def publish_to_pubsub(project_id:str,topic_name:str,data):
    client = pubsub.PublisherClient(credentials=credentials)
    topic_path = client.topic_path(project_id,topic_name)
    client.publish(topic_path,data)


if __name__ == '__main__':
    spark = SparkSession.builder.appName("JSON to PubSub").getOrCreate()

    topic_name = sys.argv[2]
    input_file = sys.argv[1]
    project_id = sys.argv[3]

    process_file(spark,input_file)

    spark.stop()