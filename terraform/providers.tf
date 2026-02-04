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

data "google_project" "project" {}

output "pubsub_topic_name" {
  value = google_pubsub_topic.openaq_topic.name
}

output "bigquery_dataset_id" {
  value = google_bigquery_dataset.openaq_dataset.dataset_id
}