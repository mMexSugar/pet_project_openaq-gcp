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