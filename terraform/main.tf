terraform {
  required_version = ">= 1.0"
  backend "local" {}
  required_providers {
    google = {
      source  = "hashicorp/google"
    }
  }
}

provider "google" {
  project = var.project
  region = var.region
}

resource "google_storage_bucket" "data-lake-bucket" {
  name          = "${local.data_lake_bucket}"
  location      = var.region

  # Optional, but recommended settings:
  storage_class = var.storage_class
  uniform_bucket_level_access = true

  versioning {
    enabled     = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 7  // days
    }
  }

  force_destroy = true
}

resource "google_storage_bucket" "events-data-bucket-storage" {
  location = var.region
  name     = "${local.events_bucket}"

  storage_class = var.storage_class
  uniform_bucket_level_access = true


  force_destroy = true
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id = var.bq_dataset
  project    = var.project
  location   = var.region
}

resource "google_bigquery_table" "default" {
  dataset_id = "${google_bigquery_dataset.dataset.dataset_id}"
  table_id   = "${var.table_id}"
  schema = file("schema.json")
  deletion_protection = false
}

resource "google_pubsub_topic" "events" {
  name = var.topic
  message_retention_duration = "86600s"
}

resource "google_pubsub_subscription" "events_sub" {
  name  = var.subscription
  topic = google_pubsub_topic.events.id
  message_retention_duration = "1200s"
  retain_acked_messages = true
  ack_deadline_seconds = 20
  expiration_policy {
    ttl = "300000.5s"
  }

  retry_policy {
    minimum_backoff = "10s"
  }

  enable_message_ordering = false
}

resource "google_storage_bucket_object" "archive" {
  name   = "main.zip"
  bucket = "${google_storage_bucket.data-lake-bucket.name}"
  source = "main.zip"
}

resource "google_cloudfunctions_function" "function" {
  name    = "amazon_reviews_fn"
  description = "This the CF for Amazon Review"
  runtime = "python37"

  available_memory_mb = 128
  source_archive_bucket = "${google_storage_bucket.data-lake-bucket.name}"
  source_archive_object = "${google_storage_bucket_object.archive.name}"
  timeout = 60

  entry_point = "main"
  environment_variables = {
    PROJECT_ID="${var.project}"
    TOPIC="${google_pubsub_topic.events.name}"
    BUCKET_NAME="${google_storage_bucket.data-lake-bucket.name}"
    REGION = "${var.region}"
    CLUSTER_NAME = "${google_dataproc_cluster.events_cluster.name}"
  }

  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = "${google_storage_bucket.events-data-bucket-storage.name}"
  }

}

resource "google_storage_bucket_object" "dataproc" {
  name   = "ingestion.py"
  bucket = "${google_storage_bucket.data-lake-bucket.name}"
  source = "ingestion.py"
}

resource "google_dataproc_cluster" "events_cluster" {
  name = "events-cluster"
  region =  var.region
  project = var.project
  cluster_config {
    staging_bucket = "${google_storage_bucket.data-lake-bucket.name}"
    master_config {
      num_instances = 1
      machine_type  = "n1-standard-2"
      disk_config {
        boot_disk_type    = "pd-ssd"
        boot_disk_size_gb = 30
      }
    }
#      worker_config {
#      num_instances    = 2
#      machine_type     = "n1-standard-2"
#      disk_config {
#        boot_disk_size_gb = 30
#        num_local_ssds    = 1
#      }
#    }
    gce_cluster_config {
      service_account = "${var.service_account}"
      service_account_scopes = ["https://www.googleapis.com/auth/pubsub"]
    }
  }

}
