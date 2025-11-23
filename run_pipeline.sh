#!/bin/bash

# GA4 GTM Analytics Pipeline Runner
# Executes the complete pipeline: Extract → Feature Engineering → Lead Scoring

set -e  # Exit on error

echo "======================================"
echo "GA4 GTM ANALYTICS PIPELINE"
echo "======================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure your credentials"
    exit 1
fi

# Check if credentials file exists
CREDS_FILE=$(grep GOOGLE_APPLICATION_CREDENTIALS .env | cut -d '=' -f2)
if [ ! -f "$CREDS_FILE" ]; then
    echo "❌ Error: Google Cloud credentials file not found: $CREDS_FILE"
    echo "Please download your service account credentials"
    exit 1
fi

echo "✓ Configuration files found"
echo ""

# Step 1: Extract GA4 Data
echo "======================================"
echo "STEP 1: Extracting GA4 Data"
echo "======================================"
python src/1_extract_ga4_data.py
echo ""

# Step 2: Feature Engineering
echo "======================================"
echo "STEP 2: Feature Engineering"
echo "======================================"
python src/2_feature_engineering.py
echo ""

# Step 3: Lead Scoring
echo "======================================"
echo "STEP 3: Lead Scoring"
echo "======================================"
python src/3_lead_scoring.py
echo ""

# Summary
echo "======================================"
echo "PIPELINE COMPLETE ✓"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Launch dashboard: streamlit run dashboard/app.py"
echo "2. View lead list: output/sales_lead_list.csv"
echo "3. Review scored users: data/processed/users_scored.csv"
echo ""
