import sys

from dotenv import load_dotenv
from google.api_core.client_options import ClientOptions
import os
from google.cloud import dataproc_v1
import uuid
load_dotenv()

def main(event,context):
    print(f"event: {event}")
    print(f"context:{context}")
    project_id = os.getenv("PROJECT_ID")
    topic_name =os.getenv("TOPIC")
    URI = "gs://" + event["bucket"] + "/" + event["name"]
    region = os.getenv("REGION")
    cluster_name = os.getenv("CLUSTER_NAME")
    bucket = os.getenv("BUCKET_NAME")

    client_options = ClientOptions(api_endpoint=f"{region}-dataproc.googleapis.com:443")

    dataproc_client = dataproc_v1.JobControllerClient(client_options=client_options)

    job = {
        "placement": {"cluster_name": cluster_name},
        "pyspark_job": {
            "main_python_file_uri": "gs://" + bucket + "/" + "ingestion.py",
            "args": [URI, topic_name, project_id]
        }
    }

    try:
        operation = dataproc_client.submit_job(request={"project_id": project_id, "region": region, "job": job})
        response = operation.status
        print("Job submitted successfully:", response)
        return "Job submission successful"
    except Exception as e:
        print(f"Error submitting job: {e}")
        return "Job submission failed"

