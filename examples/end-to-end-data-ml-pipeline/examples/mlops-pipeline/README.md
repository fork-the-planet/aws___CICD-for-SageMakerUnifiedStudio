# MLOps Pipeline — Bank Marketing Classification

End-to-end ML pipeline that trains an XGBoost binary classifier using SageMaker Airflow operators, with a notebook-based model creation step for robustness on reruns.

**Prerequisite:** The [DataOps pipeline](../dataops-pipeline/) must run first to create the `bank_mktg_dev.campaign_results` table.

## Architecture

```text
validate_data (Glue)
  → feature_engineering (Glue)
    → train_model (SageMakerTrainingOperator)
      → create_model (SageMakerNotebookOperator)
        → batch_transform (SageMakerTransformOperator)
          → deploy_endpoint (SageMakerEndpointConfigOperator)
            → create_endpoint (SageMakerEndpointOperator)
```

| Step | Operator | Description |
| ---- | -------- | ----------- |
| Data Validation | GlueJobOperator | Validates data from the DataOps Athena table |
| Feature Engineering | GlueJobOperator | Encodes features, splits train/val/test (70/15/15) |
| Model Training | SageMakerTrainingOperator | XGBoost with custom script mode and early stopping |
| Create Model | SageMakerNotebookOperator | Finds latest training job, creates model dynamically |
| Batch Transform | SageMakerTransformOperator | Batch evaluation on held-out test set |
| Deploy Endpoint | SageMakerEndpointConfigOperator + SageMakerEndpointOperator | Real-time prediction endpoint |

## Prerequisites

```bash
pip install aws-smus-cicd-cli

export AWS_ACCOUNT_ID=<your-account-id>
export DEV_DOMAIN_NAME=<your-domain-name>
export DEV_DOMAIN_REGION=<your-region>
export DEV_PROJECT_NAME=<your-project-name>
export PROJECT_ROLE=<your-login-role-name>
export DEV_MLFLOW_SERVER_NAME=bank-mktg-dev
```

MLflow tracking server must be set up first:

```bash
./scripts/setup-mlflow.sh dev <account-id> <region>
```

## Deploy and Run

```bash
# Package the custom training script
cd src && tar -czf sourcedir.tar.gz train_xgboost.py && cd ..

# Validate connectivity
aws-smus-cicd-cli describe --manifest manifest.yaml --targets dev --connect

# Deploy
aws-smus-cicd-cli deploy --manifest manifest.yaml --targets dev

# Run
aws-smus-cicd-cli run --manifest manifest.yaml --targets dev --workflow training_pipeline

# Monitor
aws-smus-cicd-cli monitor --manifest manifest.yaml --targets dev --live
```

## Project Structure

```text
mlops-pipeline/
├── manifest.yaml                        # Deployment manifest
├── workflows/
│   └── training_pipeline.yaml           # Airflow workflow definition
├── src/
│   ├── preprocess.py                    # Data validation (Glue)
│   ├── feature_engineering.py           # Feature encoding + split (Glue)
│   ├── train_xgboost.py                 # Custom XGBoost training script
│   ├── sourcedir.tar.gz                 # Packaged training script for SageMaker
│   └── notebooks/
│       ├── create_model.ipynb           # Finds latest training job, creates model
│       └── validate_mlops.ipynb         # Post-pipeline validation
└── data/
    └── bank-mktg-sample.csv             # Sample dataset
```

## Resource Naming

SageMaker resources use `{{ ts_nodash }}` (Airflow template) for unique naming per DAG run:

```text
TrainingJobName:    bank-mktg-af-xgb-<ts_nodash>
ModelName:          bank-mktg-af-model-<ts_nodash>-<suffix>
TransformJobName:   bank-mktg-af-eval-<ts_nodash>
EndpointConfigName: bank-mktg-af-ep-config-<ts_nodash>
EndpointName:       bank-mktg-af-prediction-endpoint (fixed)
```

> **Note:** For same-day reruns, trigger a new DAG run (new execution date) rather than retrying. The `create_model` notebook handles name collisions by deleting existing models.

## Validation

After the pipeline completes, run the validation notebook to verify:

```bash
# Checks: training job status, model exists, endpoint InService, inference works
# See src/notebooks/validate_mlops.ipynb
```

## Troubleshooting

**Training job name collision:** SageMaker appends a suffix if a job with the same name exists. The `create_model` notebook handles this by finding the latest job by prefix.

**NoRegionError in notebook:** The `create_model` notebook requires the `region` parameter. Ensure the workflow YAML passes `region: "{domain.region}"`.

**Endpoint already exists:** The `SageMakerEndpointOperator` updates an existing endpoint if one with the same name exists.
