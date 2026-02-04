# --- 1. Потоковая передача (Pub/Sub) ---

resource "google_pubsub_topic" "openaq_topic" {
  name = "openaq-data-topic"
  labels = { project = "pet_project_openaq" }
}

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

# --- 2. Вычислительные ресурсы (Functions & Storage) ---

data "archive_file" "incremental_sync_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_functions/incremental_sync"
  output_path = "${path.module}/files/incremental_sync.zip"
}

resource "google_storage_bucket" "function_bucket" {
  name                        = "${data.google_project.project.project_id}-gcf-source"
  location                    = "EU"
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket_object" "incremental_sync_object" {
  name   = "incremental_sync_${data.archive_file.incremental_sync_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.incremental_sync_zip.output_path
}

resource "google_cloudfunctions2_function" "incremental_sync_fn" {
  name        = "openaq-incremental-sync"
  location    = "europe-west3"
  description = "Incremental data fetch for OpenAQ"

  build_config {
    runtime     = "python311"
    entry_point = "fetch_incremental_data"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.incremental_sync_object.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    environment_variables = {
      OPENAQ_API_KEY = var.openaq_api_key
      PROJECT_ID     = data.google_project.project.project_id
    }
  }
}

# --- 3. Автоматизация (Scheduler) ---

resource "google_cloud_scheduler_job" "incremental_sync_job" {
  name             = "trigger-incremental-sync"
  description      = "Triggers OpenAQ sync every 10 minutes"
  schedule         = "*/10 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.incremental_sync_fn.url
    oidc_token {
      service_account_email = google_service_account.function_sa.email
    }
  }
}

# --- 4. Безопасность (IAM) ---

resource "google_service_account" "function_sa" {
  account_id   = "openaq-fn-sa"
  display_name = "Service Account for Cloud Functions"
}

resource "google_pubsub_topic_iam_member" "fn_publisher" {
  topic  = google_pubsub_topic.openaq_topic.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_cloudfunctions2_function_iam_member" "invoker" {
  location       = google_cloudfunctions2_function.incremental_sync_fn.location
  cloud_function = google_cloudfunctions2_function.incremental_sync_fn.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.function_sa.email}"
}