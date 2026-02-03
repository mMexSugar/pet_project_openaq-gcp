terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}


provider "google" {
  project     = "sublime-wavelet-485112-m9" 
  region      = "us-central1"
  credentials = file("keys.json")
}

resource "google_pubsub_topic" "openaq_topic" {
  name = "openaq-data-topic"

  labels = {
    project = "pet_project_openaq"
  }
}

resource "google_bigquery_dataset" "openaq_dataset" {
  dataset_id                  = "openaq_analysis"
  friendly_name               = "OpenAQ Air Quality Analysis"
  description                 = "Dataset for storing air quality data from OpenAQ API"
  location                    = "US"
  delete_contents_on_destroy = true

  labels = {
    env = "default"
  }
}

output "pubsub_topic_name" {
  value = google_pubsub_topic.openaq_topic.name
}

output "bigquery_dataset_id" {
  value = google_bigquery_dataset.openaq_dataset.dataset_id
}

resource "google_bigquery_table" "measurements_fact" {
  dataset_id = google_bigquery_dataset.openaq_dataset.dataset_id
  table_id   = "measurements_fact"

  schema = <<EOF
[
  {"name": "location_id", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "parameter_id", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "value", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"}
]
EOF

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  clustering = ["parameter_id", "location_id"]
}

resource "google_bigquery_table" "locations_dim" {
  dataset_id = google_bigquery_dataset.openaq_dataset.dataset_id
  table_id   = "locations_dim"

  schema = <<EOF
[
  {"name": "location_id", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "country_code", "type": "STRING", "mode": "NULLABLE"},
  {"name": "latitude", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "longitude", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "last_seen", "type": "TIMESTAMP", "mode": "NULLABLE"}
]
EOF
}

#  Pub/Sub
data "google_project" "project" {}


resource "google_project_iam_member" "pubsub_bq_writer" {
  project = data.google_project.project.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "pubsub_bq_metadata" {
  project = data.google_project.project.project_id
  role    = "roles/bigquery.metadataViewer"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "bq_subscription" {
  name  = "openaq-bq-sub"
  topic = google_pubsub_topic.openaq_topic.name

  bigquery_config {
    table = "${data.google_project.project.project_id}.${google_bigquery_dataset.openaq_dataset.dataset_id}.${google_bigquery_table.measurements_fact.table_id}"
    
    use_table_schema = true 
    use_topic_schema = false 
    write_metadata   = false
    
    drop_unknown_fields = true
  }

  depends_on = [google_project_iam_member.pubsub_bq_writer]
}