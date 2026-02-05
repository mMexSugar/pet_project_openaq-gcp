resource "google_bigquery_dataset" "openaq_dataset" {
  dataset_id                  = "openaq_analysis"
  friendly_name               = "OpenAQ Air Quality Analysis"
  description                 = "Dataset for storing air quality data from OpenAQ API"
  location                    = "US"
  delete_contents_on_destroy  = true

  labels = { env = "default" }
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
  {"name": "city_name", "type": "STRING", "mode": "NULLABLE"},
  {"name": "latitude", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "longitude", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "last_seen", "type": "TIMESTAMP", "mode": "NULLABLE"}
]
EOF
}

resource "google_bigquery_table" "parameters_dim" {
  dataset_id = google_bigquery_dataset.openaq_dataset.dataset_id
  table_id   = "parameters_dim"
  deletion_protection = false

  schema = <<EOF
[
  {"name": "parameter_id", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "display_name", "type": "STRING", "mode": "NULLABLE"},
  {"name": "unit", "type": "STRING", "mode": "NULLABLE"}
]
EOF
}

resource "google_bigquery_table" "v_measurements_2026" {
  dataset_id = google_bigquery_dataset.openaq_dataset.dataset_id
  table_id   = "v_measurements_2026"
  deletion_protection = false

  view {
    query = <<EOF
      SELECT DISTINCT 
          f.timestamp,
          d.country_code,
          d.city_name,
          p.display_name AS pollutant,
          p.unit,
          f.value,
          d.latitude,
          d.longitude,
          f.location_id
      FROM 
          `${data.google_project.project.project_id}.${google_bigquery_dataset.openaq_dataset.dataset_id}.${google_bigquery_table.measurements_fact.table_id}` AS f
      INNER JOIN 
          `${data.google_project.project.project_id}.${google_bigquery_dataset.openaq_dataset.dataset_id}.${google_bigquery_table.locations_dim.table_id}` AS d
          ON f.location_id = d.location_id
      LEFT JOIN 
          `${data.google_project.project.project_id}.${google_bigquery_dataset.openaq_dataset.dataset_id}.${google_bigquery_table.parameters_dim.table_id}` AS p
          ON f.parameter_id = p.parameter_id
      WHERE 
          EXTRACT(YEAR FROM f.timestamp) = 2026
    EOF
    use_legacy_sql = false
  }

  depends_on = [
    google_bigquery_table.measurements_fact,
    google_bigquery_table.locations_dim,
    google_bigquery_table.parameters_dim
  ]
}