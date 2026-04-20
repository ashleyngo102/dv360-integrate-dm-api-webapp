#!/bin/bash

DETECTED_PROJECT=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}

PROJECT_ID=$DETECTED_PROJECT
while [[ -z "$PROJECT_ID" ]]; do
    echo "❌ ERROR: No Project ID detected!"
    read -p "Please enter your Google Cloud Project ID: " PROJECT_ID
done

D_SERVICE="dv360-audience-manager"
D_BUCKET="${PROJECT_ID}-dv360-data"
D_REGION="us-central1"
D_SA="${PROJECT_ID}@appspot.gserviceaccount.com"

deploy_python_service() {
    echo "----------------------------------------------------"
    echo "DEPLOYMENT CONFIG (Hit Enter to use defaults)"
    echo "----------------------------------------------------"

    read -p "1. Project ID      [$PROJECT_ID]: " USER_PROJECT
    PROJECT_ID=${USER_PROJECT:-$PROJECT_ID}

    read -p "2. Service Name    [$D_SERVICE]: " SERVICE_NAME
    SERVICE_NAME=${SERVICE_NAME:-$D_SERVICE}

    read -p "3. Bucket Name     [$D_BUCKET]: " BUCKET_NAME
    BUCKET_NAME=${BUCKET_NAME:-$D_BUCKET}

    read -p "4. Region          [$D_REGION]: " REGION
    REGION=${REGION:-$D_REGION}

    read -p "5. Service Account [$D_SA]: " SERVICE_ACCOUNT
    SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-$D_SA}

    echo "----------------------------------------------------"
    echo "Deploying to:    $PROJECT_ID"
    echo "Service Name:    $D_SERVICE"
    echo "Bucket Name:     $D_BUCKET"
    echo "Region:          $D_REGION"
    echo "Service Accoun:  $SERVICE_ACCOUNT"
    echo "----------------------------------------------------"

    # Create the Bucket
    gcloud storage buckets describe "gs://$D_BUCKET" >/dev/null 2>&1 || \
    gcloud storage buckets create "gs://$D_BUCKET" --location="$REGION"

    gcloud run deploy "$SERVICE_NAME" \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --source="." \
        --service-account="$SERVICE_ACCOUNT" \
        --timeout=3600 \
        --memory=4Gi \
        --cpu=2 \
        --no-allow-unauthenticated \
        --set-env-vars="PROJECT_ID=$PROJECT_ID,GCS_BUCKET=$BUCKET_NAME,ENV=prod"
    
    # The Security Handshake
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    
    gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
        --role="roles/run.invoker" --quiet

    echo "----------------------------------------------------"
    echo "Deployment Complete! Target: $PROJECT_ID"
}

deploy_python_service
