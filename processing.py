from time import sleep
import json

import google.generativeai as genai
import apache_beam as beam
from apache_beam.io import BigQueryDisposition
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions

import google.auth
from google.cloud import pubsub
from dotenv import load_dotenv
import os
load_dotenv()


credentials, _ = google.auth.default()
#https://www.kaggle.com/datasets/abdallahwagih/amazon-reviews


GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')


def google_gen(row):
    message = "Based on the following electronics reviews determine the possible product and product category the review is for and if the customer may refer the product i.e a net promoter or not with reponses [Promoter,Passives,Distractors], the only fields I want are product,NPS and Category reply with this with only this schema alone and nothing else {\"product\":\"Iphone\",\"NPS\":\"Promoter\",\"Category\":\"Phones\"}  " + row["reviewText"]
    sleep(2)
    response = model.generate_content(message)
    json_data = json.loads(response.text)

    final_res = {**row, **json_data}

    return final_res

def get_sub_path(project_id:str,sub_name:str):
    client = pubsub.PublisherClient(credentials=credentials)
    return client.subscription_path(project_id, sub_name)
def run():
    options = PipelineOptions(streaming=True)
    google_cloud_options = options.view_as(GoogleCloudOptions)
    project_id = os.getenv("PROJECT_ID")
    google_cloud_options.project = project_id
    google_cloud_options.job_name = os.getenv("JOB_NAME")
    google_cloud_options.staging_location = os.getenv("STAGING_LOCATION")
    google_cloud_options.temp_location = os.getenv("TEMP_LOCATION")
    google_cloud_options.region = os.getenv("REGION")

    table_id = os.getenv("TABLE")

    subscription = get_sub_path(project_id, os.getenv("SUBSCRIPTION"))
    # Create the pipeline
    pipeline = beam.Pipeline(options=options)

    reviews = (pipeline | "Read Message" >>  beam.io.ReadFromPubSub(subscription=subscription)
                    | "Decode Mesage" >> beam.Map(lambda x: x.decode('utf-8'))
                    | "Parse Messages" >> beam.Map(lambda x: json.loads(x))
            )
    res = reviews | "Update reviews with fields" >> beam.Map(google_gen)

    res| "print" >> beam.Map(print)


    res | "stream to BQ" >> beam.io.WriteToBigQuery(table=table_id,
                                                    write_disposition=BigQueryDisposition.WRITE_APPEND, create_disposition=BigQueryDisposition.CREATE_IF_NEEDED)


    pipeline.run().wait_until_finish()




if __name__ == '__main__':
    run()



