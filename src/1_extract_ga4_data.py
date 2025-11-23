"""
GA4 Data Extraction from BigQuery
Extracts event data from Google Analytics 4 sample dataset
"""

import pandas as pd
from google.cloud import bigquery
from datetime import datetime
import os
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

def create_bigquery_client():
    """Initialize BigQuery client"""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    return bigquery.Client(project=project_id)

def extract_ga4_events(client, start_date='20210101', end_date='20210131'):
    """
    Extract GA4 events from BigQuery public dataset

    Args:
        client: BigQuery client
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format

    Returns:
        DataFrame with GA4 event data
    """

    query = f"""
    SELECT
        user_pseudo_id,
        event_date,
        event_timestamp,
        event_name,
        event_params,
        event_previous_timestamp,
        event_value_in_usd,
        event_bundle_sequence_id,
        event_server_timestamp_offset,
        user_id,
        user_properties,
        user_first_touch_timestamp,
        user_ltv,
        device.category as device_category,
        device.mobile_brand_name as device_brand,
        device.mobile_model_name as device_model,
        device.operating_system as os,
        device.operating_system_version as os_version,
        device.language as device_language,
        device.web_info.browser as browser,
        device.web_info.browser_version as browser_version,
        geo.continent as continent,
        geo.country as country,
        geo.region as region,
        geo.city as city,
        app_info.id as app_id,
        app_info.version as app_version,
        traffic_source.name as traffic_source_name,
        traffic_source.medium as traffic_source_medium,
        traffic_source.source as traffic_source,
        ecommerce.total_item_quantity,
        ecommerce.purchase_revenue_in_usd,
        ecommerce.purchase_revenue,
        ecommerce.refund_value_in_usd,
        ecommerce.shipping_value_in_usd,
        ecommerce.tax_value_in_usd,
        ecommerce.transaction_id,
        ecommerce.unique_items
    FROM
        `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE
        _TABLE_SUFFIX BETWEEN '{start_date}' AND '{end_date}'
    """

    print(f"Extracting GA4 data from {start_date} to {end_date}...")
    print("This may take a few minutes for 1M+ events...")

    # Execute query
    df = client.query(query).to_dataframe()

    print(f"✓ Extracted {len(df):,} events")
    print(f"✓ Date range: {df['event_date'].min()} to {df['event_date'].max()}")
    print(f"✓ Unique users: {df['user_pseudo_id'].nunique():,}")

    return df

def extract_event_parameters(df):
    """
    Extract common event parameters from nested structure

    Args:
        df: DataFrame with event_params column

    Returns:
        DataFrame with expanded event parameters
    """
    print("\nExtracting event parameters...")

    # Common event parameters to extract
    param_keys = [
        'page_location', 'page_title', 'page_referrer',
        'engagement_time_msec', 'session_engaged',
        'value', 'currency', 'items', 'item_id', 'item_name',
        'item_category', 'price', 'quantity'
    ]

    # This is a simplified version - in production you'd parse the nested structure
    # For now, we'll work with the existing columns

    return df

def save_raw_data(df, output_path='data/raw/ga4_events_raw.parquet'):
    """Save raw data to parquet file"""
    print(f"\nSaving raw data to {output_path}...")
    df.to_parquet(output_path, compression='snappy', index=False)
    print(f"✓ Saved {len(df):,} rows")

    # Also save a sample CSV for quick inspection
    sample_path = output_path.replace('.parquet', '_sample.csv')
    df.head(1000).to_csv(sample_path, index=False)
    print(f"✓ Saved sample (1000 rows) to {sample_path}")

def main():
    """Main execution function"""
    print("="*60)
    print("GA4 DATA EXTRACTION")
    print("="*60)

    # Get parameters from environment or use defaults
    start_date = os.getenv('START_DATE', '20210101')
    end_date = os.getenv('END_DATE', '20210131')

    # Create BigQuery client
    client = create_bigquery_client()

    # Extract GA4 events
    df = extract_ga4_events(client, start_date, end_date)

    # Extract event parameters
    df = extract_event_parameters(df)

    # Save raw data
    save_raw_data(df)

    print("\n" + "="*60)
    print("DATA EXTRACTION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Run: python src/2_feature_engineering.py")
    print("2. Run: python src/3_lead_scoring.py")
    print("3. Launch dashboard: streamlit run dashboard/app.py")

if __name__ == "__main__":
    main()
