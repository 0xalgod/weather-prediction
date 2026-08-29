# Data Layers

- `raw/`: immutable source payloads as received
- `interim/`: normalized intermediate data
- `processed/`: model-ready versioned datasets
- `external/`: licensed or manually supplied reference data

Data contents are ignored by Git. Commit manifests, schemas, checksums, and data dictionaries—not raw or generated datasets.
