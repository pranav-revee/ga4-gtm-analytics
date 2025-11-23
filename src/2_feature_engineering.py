"""
Feature Engineering for GA4 Data
Transforms raw GA4 events into user-level features for lead scoring
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

def load_raw_data(file_path='data/raw/ga4_events_raw.parquet'):
    """Load raw GA4 event data"""
    print("Loading raw GA4 data...")
    df = pd.read_parquet(file_path)
    print(f"✓ Loaded {len(df):,} events for {df['user_pseudo_id'].nunique():,} users")
    return df

def engineer_user_features(df):
    """
    Create user-level features from event data

    Args:
        df: Raw event-level DataFrame

    Returns:
        DataFrame with one row per user and engineered features
    """
    print("\nEngineering user-level features...")

    # Convert event_date to datetime
    df['event_date_dt'] = pd.to_datetime(df['event_date'], format='%Y%m%d')

    # Calculate analysis period
    max_date = df['event_date_dt'].max()
    min_date = df['event_date_dt'].min()

    print(f"Analysis period: {min_date.date()} to {max_date.date()}")

    # Group by user and calculate features
    user_features = []

    for user_id in tqdm(df['user_pseudo_id'].unique(), desc="Processing users"):
        user_df = df[df['user_pseudo_id'] == user_id].copy()

        # --- ENGAGEMENT METRICS ---
        total_events = len(user_df)
        unique_event_types = user_df['event_name'].nunique()
        unique_days_active = user_df['event_date'].nunique()

        # --- TEMPORAL FEATURES ---
        first_visit = user_df['event_date_dt'].min()
        last_visit = user_df['event_date_dt'].max()
        days_since_first_visit = (max_date - first_visit).days
        days_since_last_visit = (max_date - last_visit).days
        user_lifetime_days = (last_visit - first_visit).days + 1

        # Activity frequency
        events_per_day = total_events / max(user_lifetime_days, 1)
        active_days_ratio = unique_days_active / max(days_since_first_visit, 1)

        # --- FEATURE ADOPTION ---
        # Key events that indicate product engagement
        key_events = {
            'page_view': 'view_item',
            'search': 'search',
            'add_to_cart': 'add_to_cart',
            'begin_checkout': 'begin_checkout',
            'purchase': 'purchase',
            'video_start': 'video_start',
            'file_download': 'file_download',
            'sign_up': 'sign_up',
            'login': 'login'
        }

        feature_adoption_count = 0
        for event_type in key_events.values():
            if event_type in user_df['event_name'].values:
                feature_adoption_count += 1

        # --- CONVERSION METRICS ---
        has_purchased = ('purchase' in user_df['event_name'].values)
        purchase_count = (user_df['event_name'] == 'purchase').sum()

        # Revenue metrics
        total_revenue = user_df['purchase_revenue_in_usd'].fillna(0).sum()
        avg_order_value = total_revenue / purchase_count if purchase_count > 0 else 0

        # --- ENGAGEMENT QUALITY ---
        # Session engagement (simplified - counting consecutive events within 30min)
        page_views = (user_df['event_name'] == 'view_item').sum()
        add_to_carts = (user_df['event_name'] == 'add_to_cart').sum()
        cart_conversion_rate = add_to_carts / page_views if page_views > 0 else 0

        # --- DEVICE & CHANNEL ---
        primary_device = user_df['device_category'].mode()[0] if len(user_df['device_category'].mode()) > 0 else 'unknown'
        primary_country = user_df['country'].mode()[0] if len(user_df['country'].mode()) > 0 else 'unknown'
        primary_traffic_source = user_df['traffic_source'].mode()[0] if len(user_df['traffic_source'].mode()) > 0 else 'unknown'

        # --- BEHAVIORAL PATTERNS ---
        # Power user indicator
        is_power_user = total_events > user_df['user_pseudo_id'].map(df['user_pseudo_id'].value_counts()).median()

        # Recency category
        if days_since_last_visit <= 7:
            recency_category = 'active'
        elif days_since_last_visit <= 30:
            recency_category = 'at_risk'
        else:
            recency_category = 'churned'

        # --- ENGAGEMENT SCORE (0-100) ---
        # Composite score based on multiple factors
        engagement_score = min(100, (
            (unique_days_active * 5) +  # Consistency
            (feature_adoption_count * 10) +  # Feature adoption
            (purchase_count * 15) +  # Conversion
            (min(events_per_day * 5, 20))  # Activity level (capped)
        ))

        # --- ESTIMATED VALUE ---
        # For users who haven't purchased, estimate based on engagement
        if total_revenue > 0:
            estimated_value = total_revenue
        else:
            # Estimate based on engagement patterns
            estimated_value = (
                engagement_score * 10 +  # Base engagement value
                feature_adoption_count * 500 +  # Feature adoption value
                unique_days_active * 100  # Retention value
            )

        # Compile features
        user_features.append({
            'user_pseudo_id': user_id,

            # Engagement metrics
            'total_events': total_events,
            'unique_event_types': unique_event_types,
            'unique_days_active': unique_days_active,
            'events_per_day': round(events_per_day, 2),
            'active_days_ratio': round(active_days_ratio, 3),

            # Temporal features
            'days_since_first_visit': days_since_first_visit,
            'days_since_last_visit': days_since_last_visit,
            'user_lifetime_days': user_lifetime_days,

            # Feature adoption
            'feature_adoption_count': feature_adoption_count,
            'page_views': page_views,
            'add_to_carts': add_to_carts,
            'cart_conversion_rate': round(cart_conversion_rate, 3),

            # Conversion metrics
            'has_purchased': has_purchased,
            'purchase_count': purchase_count,
            'total_revenue': round(total_revenue, 2),
            'avg_order_value': round(avg_order_value, 2),

            # Behavioral patterns
            'is_power_user': is_power_user,
            'recency_category': recency_category,
            'engagement_score': round(engagement_score, 2),
            'estimated_value': round(estimated_value, 2),

            # Demographics
            'primary_device': primary_device,
            'primary_country': primary_country,
            'primary_traffic_source': primary_traffic_source,
        })

    user_features_df = pd.DataFrame(user_features)

    print(f"\n✓ Engineered features for {len(user_features_df):,} users")
    print(f"✓ Created {len(user_features_df.columns)} features per user")

    return user_features_df

def add_rfm_scores(df):
    """
    Add RFM (Recency, Frequency, Monetary) scores

    Args:
        df: User features DataFrame

    Returns:
        DataFrame with RFM scores added
    """
    print("\nCalculating RFM scores...")

    # Recency score (inverse of days_since_last_visit)
    df['recency_score'] = pd.qcut(
        df['days_since_last_visit'],
        q=5,
        labels=[5, 4, 3, 2, 1],
        duplicates='drop'
    ).astype(int)

    # Frequency score (based on unique_days_active)
    df['frequency_score'] = pd.qcut(
        df['unique_days_active'],
        q=5,
        labels=[1, 2, 3, 4, 5],
        duplicates='drop'
    ).astype(int)

    # Monetary score (based on total_revenue or estimated_value)
    df['monetary_value'] = df.apply(
        lambda row: row['total_revenue'] if row['total_revenue'] > 0 else row['estimated_value'],
        axis=1
    )

    df['monetary_score'] = pd.qcut(
        df['monetary_value'],
        q=5,
        labels=[1, 2, 3, 4, 5],
        duplicates='drop'
    ).astype(int)

    # Overall RFM score
    df['rfm_score'] = (
        df['recency_score'] * 100 +
        df['frequency_score'] * 10 +
        df['monetary_score']
    )

    # RFM segment
    df['rfm_segment'] = df['rfm_score'].apply(classify_rfm_segment)

    print("✓ RFM scores calculated")

    return df

def classify_rfm_segment(score):
    """Classify RFM score into business segments"""
    if score >= 444:
        return 'Champions'
    elif score >= 344:
        return 'Loyal Customers'
    elif score >= 243:
        return 'Potential Loyalists'
    elif score >= 233:
        return 'New Customers'
    elif score >= 133:
        return 'At Risk'
    else:
        return 'Lost'

def save_features(df, output_path='data/processed/user_features.parquet'):
    """Save engineered features"""
    print(f"\nSaving features to {output_path}...")
    df.to_parquet(output_path, compression='snappy', index=False)

    # Also save CSV for inspection
    csv_path = output_path.replace('.parquet', '.csv')
    df.to_csv(csv_path, index=False)

    print(f"✓ Saved {len(df):,} user records")
    print(f"✓ Feature columns: {', '.join(df.columns.tolist()[:10])}...")

def main():
    """Main execution function"""
    print("="*60)
    print("FEATURE ENGINEERING")
    print("="*60)

    # Load raw data
    df = load_raw_data()

    # Engineer user features
    user_features = engineer_user_features(df)

    # Add RFM scores
    user_features = add_rfm_scores(user_features)

    # Display summary statistics
    print("\n" + "="*60)
    print("FEATURE SUMMARY")
    print("="*60)
    print(f"\nTotal users: {len(user_features):,}")
    print(f"Power users: {user_features['is_power_user'].sum():,} ({user_features['is_power_user'].mean()*100:.1f}%)")
    print(f"Users with purchases: {user_features['has_purchased'].sum():,} ({user_features['has_purchased'].mean()*100:.1f}%)")
    print(f"\nEngagement score - Mean: {user_features['engagement_score'].mean():.1f}, Median: {user_features['engagement_score'].median():.1f}")
    print(f"Estimated value - Mean: ${user_features['estimated_value'].mean():,.0f}, Median: ${user_features['estimated_value'].median():,.0f}")

    print("\nRFM Segment Distribution:")
    print(user_features['rfm_segment'].value_counts())

    # Save features
    save_features(user_features)

    print("\n" + "="*60)
    print("FEATURE ENGINEERING COMPLETE")
    print("="*60)
    print("\nNext step: Run python src/3_lead_scoring.py")

if __name__ == "__main__":
    main()
