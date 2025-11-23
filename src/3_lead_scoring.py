"""
Lead Scoring Model
Builds a machine learning model to score leads based on conversion propensity
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import pickle
import warnings
warnings.filterwarnings('ignore')

def load_features(file_path='data/processed/user_features.parquet'):
    """Load engineered user features"""
    print("Loading user features...")
    df = pd.read_parquet(file_path)
    print(f"✓ Loaded {len(df):,} users with {len(df.columns)} features")
    return df

def prepare_training_data(df):
    """
    Prepare features for model training

    Args:
        df: User features DataFrame

    Returns:
        X: Feature matrix
        y: Target variable (conversion)
        feature_names: List of feature names
    """
    print("\nPreparing training data...")

    # Define target variable
    # In this case, we'll predict high-value conversions
    # (users who either purchased or have high engagement indicating purchase intent)
    df['target'] = (
        (df['has_purchased'] == True) |
        ((df['engagement_score'] > 75) & (df['feature_adoption_count'] >= 5))
    ).astype(int)

    print(f"Conversion rate: {df['target'].mean()*100:.2f}%")
    print(f"Positive examples: {df['target'].sum():,}")
    print(f"Negative examples: {(df['target']==0).sum():,}")

    # Select features for modeling
    feature_columns = [
        # Engagement metrics
        'total_events',
        'unique_event_types',
        'unique_days_active',
        'events_per_day',
        'active_days_ratio',

        # Temporal features
        'days_since_first_visit',
        'days_since_last_visit',
        'user_lifetime_days',

        # Feature adoption
        'feature_adoption_count',
        'page_views',
        'add_to_carts',
        'cart_conversion_rate',

        # Behavioral patterns
        'is_power_user',
        'engagement_score',

        # RFM scores
        'recency_score',
        'frequency_score',
        'monetary_score',
    ]

    # Encode categorical features
    le_device = LabelEncoder()
    df['device_encoded'] = le_device.fit_transform(df['primary_device'].fillna('unknown'))
    feature_columns.append('device_encoded')

    # Create feature matrix
    X = df[feature_columns].copy()

    # Handle any remaining missing values
    X = X.fillna(0)

    # Convert boolean to int
    X['is_power_user'] = X['is_power_user'].astype(int)

    y = df['target']

    print(f"✓ Prepared {len(feature_columns)} features for modeling")

    return X, y, feature_columns, df

def train_model(X, y, feature_names):
    """
    Train lead scoring model

    Args:
        X: Feature matrix
        y: Target variable
        feature_names: List of feature names

    Returns:
        Trained model, scaler, and performance metrics
    """
    print("\nTraining lead scoring model...")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    print(f"Training set: {len(X_train):,} samples")
    print(f"Test set: {len(X_test):,} samples")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train Random Forest model
    print("\nTraining Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'  # Handle imbalanced data
    )

    model.fit(X_train_scaled, y_train)

    # Cross-validation
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='roc_auc')
    print(f"Cross-validation AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")

    # Evaluate on test set
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

    # Performance metrics
    print("\n" + "="*60)
    print("MODEL PERFORMANCE")
    print("="*60)

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Low Value', 'High Value']))

    auc_score = roc_auc_score(y_test, y_pred_proba)
    print(f"\nROC-AUC Score: {auc_score:.3f}")

    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nTop 10 Most Important Features:")
    print(feature_importance.head(10).to_string(index=False))

    return model, scaler, feature_importance

def generate_lead_scores(df, model, scaler, feature_names):
    """
    Generate lead scores for all users

    Args:
        df: User features DataFrame
        model: Trained model
        scaler: Fitted scaler
        feature_names: List of feature names

    Returns:
        DataFrame with lead scores
    """
    print("\n" + "="*60)
    print("GENERATING LEAD SCORES")
    print("="*60)

    # Prepare features (same encoding as training)
    le_device = LabelEncoder()
    df['device_encoded'] = le_device.fit_transform(df['primary_device'].fillna('unknown'))

    X = df[feature_names].copy()
    X = X.fillna(0)
    X['is_power_user'] = X['is_power_user'].astype(int)

    # Scale features
    X_scaled = scaler.transform(X)

    # Generate predictions
    df['lead_score'] = model.predict_proba(X_scaled)[:, 1]
    df['lead_prediction'] = model.predict(X_scaled)

    # Classify lead quality
    df['lead_quality'] = pd.cut(
        df['lead_score'],
        bins=[0, 0.3, 0.5, 0.7, 1.0],
        labels=['Cold', 'Warm', 'Hot', 'Very Hot']
    )

    print(f"✓ Generated lead scores for {len(df):,} users")

    print("\nLead Quality Distribution:")
    print(df['lead_quality'].value_counts().sort_index())

    return df

def create_sales_lead_list(df, score_threshold=0.7, min_value=10000):
    """
    Create prioritized sales lead list

    Args:
        df: DataFrame with lead scores
        score_threshold: Minimum lead score
        min_value: Minimum estimated value

    Returns:
        DataFrame with high-value leads
    """
    print("\n" + "="*60)
    print("CREATING SALES LEAD LIST")
    print("="*60)

    # Filter high-value leads
    high_value_leads = df[
        (df['lead_score'] > score_threshold) &
        (df['estimated_value'] > min_value)
    ].copy()

    # Sort by lead score and estimated value
    high_value_leads = high_value_leads.sort_values(
        ['lead_score', 'estimated_value'],
        ascending=False
    )

    # Select key columns for sales team
    sales_columns = [
        'user_pseudo_id',
        'lead_score',
        'lead_quality',
        'estimated_value',
        'engagement_score',
        'feature_adoption_count',
        'days_since_last_visit',
        'recency_category',
        'rfm_segment',
        'has_purchased',
        'total_revenue',
        'primary_country',
        'primary_device',
        'primary_traffic_source'
    ]

    lead_list = high_value_leads[sales_columns].copy()

    # Add recommended action
    def recommend_action(row):
        if row['has_purchased'] and row['days_since_last_visit'] <= 7:
            return 'Upsell - Active Customer'
        elif row['has_purchased'] and row['days_since_last_visit'] > 7:
            return 'Re-engage - Past Customer'
        elif row['engagement_score'] > 75:
            return 'Convert - High Intent'
        else:
            return 'Nurture - Warm Lead'

    lead_list['recommended_action'] = lead_list.apply(recommend_action, axis=1)

    print(f"\n✓ Identified {len(lead_list):,} high-value leads")
    print(f"✓ Total estimated pipeline value: ${lead_list['estimated_value'].sum():,.0f}")
    print(f"✓ Average estimated value per lead: ${lead_list['estimated_value'].mean():,.0f}")

    print("\nRecommended Actions:")
    print(lead_list['recommended_action'].value_counts())

    return lead_list

def save_outputs(df, lead_list, model, scaler, feature_importance):
    """Save all outputs"""
    print("\n" + "="*60)
    print("SAVING OUTPUTS")
    print("="*60)

    # Save scored users
    df.to_parquet('data/processed/users_scored.parquet', compression='snappy', index=False)
    df.to_csv('data/processed/users_scored.csv', index=False)
    print("✓ Saved scored users")

    # Save lead list
    lead_list.to_csv('output/sales_lead_list.csv', index=False)
    print("✓ Saved sales lead list to output/sales_lead_list.csv")

    # Save model
    with open('output/lead_scoring_model.pkl', 'wb') as f:
        pickle.dump({'model': model, 'scaler': scaler}, f)
    print("✓ Saved model to output/lead_scoring_model.pkl")

    # Save feature importance
    feature_importance.to_csv('output/feature_importance.csv', index=False)
    print("✓ Saved feature importance")

def main():
    """Main execution function"""
    print("="*60)
    print("LEAD SCORING MODEL")
    print("="*60)

    # Load features
    df = load_features()

    # Prepare training data
    X, y, feature_names, df = prepare_training_data(df)

    # Train model
    model, scaler, feature_importance = train_model(X, y, feature_names)

    # Generate lead scores
    df = generate_lead_scores(df, model, scaler, feature_names)

    # Create sales lead list
    lead_list = create_sales_lead_list(df, score_threshold=0.7, min_value=10000)

    # Save outputs
    save_outputs(df, lead_list, model, scaler, feature_importance)

    print("\n" + "="*60)
    print("LEAD SCORING COMPLETE")
    print("="*60)
    print("\n🎯 Key Results:")
    print(f"  • High-value leads identified: {len(lead_list):,}")
    print(f"  • Estimated pipeline value: ${lead_list['estimated_value'].sum():,.0f}")
    print(f"  • Model AUC: {roc_auc_score(y, model.predict_proba(scaler.transform(X))[:, 1]):.3f}")
    print("\nNext step: Launch dashboard with: streamlit run dashboard/app.py")

if __name__ == "__main__":
    main()
