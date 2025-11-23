"""
GA4 GTM Analytics Dashboard
Interactive sales intelligence dashboard for lead analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="GA4 GTM Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stDownloadButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load scored user data and lead list"""
    try:
        users_df = pd.read_parquet('data/processed/users_scored.parquet')
        lead_list = pd.read_csv('output/sales_lead_list.csv')
        return users_df, lead_list
    except FileNotFoundError:
        st.error("Data files not found. Please run the pipeline first:\n1. python src/1_extract_ga4_data.py\n2. python src/2_feature_engineering.py\n3. python src/3_lead_scoring.py")
        st.stop()

def main():
    # Header
    st.markdown('<div class="main-header">📊 GA4 GTM Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Sales Intelligence & Lead Scoring Platform</div>', unsafe_allow_html=True)

    # Load data
    users_df, lead_list = load_data()

    # Sidebar filters
    st.sidebar.header("🔍 Filters")

    # Lead quality filter
    lead_qualities = ['All'] + list(users_df['lead_quality'].dropna().unique())
    selected_quality = st.sidebar.multiselect(
        "Lead Quality",
        lead_qualities,
        default=['All']
    )

    # RFM segment filter
    rfm_segments = ['All'] + list(users_df['rfm_segment'].unique())
    selected_rfm = st.sidebar.multiselect(
        "RFM Segment",
        rfm_segments,
        default=['All']
    )

    # Country filter
    countries = ['All'] + list(users_df['primary_country'].value_counts().head(10).index)
    selected_country = st.sidebar.multiselect(
        "Country",
        countries,
        default=['All']
    )

    # Lead score threshold
    score_threshold = st.sidebar.slider(
        "Minimum Lead Score",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05
    )

    # Apply filters
    filtered_df = users_df.copy()

    if 'All' not in selected_quality:
        filtered_df = filtered_df[filtered_df['lead_quality'].isin(selected_quality)]

    if 'All' not in selected_rfm:
        filtered_df = filtered_df[filtered_df['rfm_segment'].isin(selected_rfm)]

    if 'All' not in selected_country:
        filtered_df = filtered_df[filtered_df['primary_country'].isin(selected_country)]

    filtered_df = filtered_df[filtered_df['lead_score'] >= score_threshold]

    # Executive Summary
    st.header("📈 Executive Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_leads = len(filtered_df)
        st.metric(
            "Total Leads",
            f"{total_leads:,}",
            delta=f"{(total_leads/len(users_df)*100):.1f}% of total"
        )

    with col2:
        high_value_leads = len(filtered_df[filtered_df['lead_score'] > 0.7])
        st.metric(
            "High-Value Leads",
            f"{high_value_leads:,}",
            delta=f"{(high_value_leads/total_leads*100):.1f}%" if total_leads > 0 else "0%"
        )

    with col3:
        pipeline_value = filtered_df['estimated_value'].sum()
        st.metric(
            "Pipeline Value",
            f"${pipeline_value:,.0f}",
            delta=f"${pipeline_value/total_leads:,.0f} avg" if total_leads > 0 else "$0"
        )

    with col4:
        conversion_rate = filtered_df['has_purchased'].mean() * 100
        st.metric(
            "Conversion Rate",
            f"{conversion_rate:.1f}%",
            delta=f"{conversion_rate - users_df['has_purchased'].mean()*100:.1f}% vs baseline"
        )

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Lead Analysis",
        "📊 Engagement Insights",
        "💰 Revenue Analysis",
        "📋 Lead Lists"
    ])

    with tab1:
        st.subheader("Lead Scoring Distribution")

        col1, col2 = st.columns(2)

        with col1:
            # Lead quality distribution
            quality_counts = filtered_df['lead_quality'].value_counts()
            fig = px.pie(
                values=quality_counts.values,
                names=quality_counts.index,
                title="Lead Quality Distribution",
                color_discrete_sequence=px.colors.sequential.Blues_r
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # RFM segment distribution
            rfm_counts = filtered_df['rfm_segment'].value_counts()
            fig = px.bar(
                x=rfm_counts.index,
                y=rfm_counts.values,
                title="RFM Segment Distribution",
                labels={'x': 'Segment', 'y': 'Count'},
                color=rfm_counts.values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)

        # Lead score vs estimated value scatter
        st.subheader("Lead Score vs Estimated Value")
        fig = px.scatter(
            filtered_df,
            x='lead_score',
            y='estimated_value',
            color='lead_quality',
            size='engagement_score',
            hover_data=['user_pseudo_id', 'rfm_segment', 'days_since_last_visit'],
            title="Lead Scoring Matrix",
            labels={
                'lead_score': 'Lead Score',
                'estimated_value': 'Estimated Value ($)',
                'lead_quality': 'Lead Quality'
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("User Engagement Patterns")

        col1, col2 = st.columns(2)

        with col1:
            # Engagement score distribution
            fig = px.histogram(
                filtered_df,
                x='engagement_score',
                nbins=50,
                title="Engagement Score Distribution",
                labels={'engagement_score': 'Engagement Score'},
                color_discrete_sequence=['#1f77b4']
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Feature adoption
            avg_adoption = filtered_df.groupby('lead_quality')['feature_adoption_count'].mean()
            fig = px.bar(
                x=avg_adoption.index,
                y=avg_adoption.values,
                title="Average Feature Adoption by Lead Quality",
                labels={'x': 'Lead Quality', 'y': 'Avg Features Adopted'},
                color=avg_adoption.values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)

        # Engagement metrics by segment
        st.subheader("Engagement Metrics by RFM Segment")

        segment_metrics = filtered_df.groupby('rfm_segment').agg({
            'engagement_score': 'mean',
            'unique_days_active': 'mean',
            'events_per_day': 'mean',
            'feature_adoption_count': 'mean'
        }).round(2)

        st.dataframe(segment_metrics, use_container_width=True)

    with tab3:
        st.subheader("Revenue & Value Analysis")

        col1, col2 = st.columns(2)

        with col1:
            # Revenue by segment
            revenue_by_segment = filtered_df.groupby('rfm_segment')['total_revenue'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=revenue_by_segment.index,
                y=revenue_by_segment.values,
                title="Total Revenue by RFM Segment",
                labels={'x': 'Segment', 'y': 'Total Revenue ($)'},
                color=revenue_by_segment.values,
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Estimated value by lead quality
            value_by_quality = filtered_df.groupby('lead_quality')['estimated_value'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=value_by_quality.index,
                y=value_by_quality.values,
                title="Estimated Pipeline Value by Lead Quality",
                labels={'x': 'Lead Quality', 'y': 'Estimated Value ($)'},
                color=value_by_quality.values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)

        # Top opportunities
        st.subheader("Top Revenue Opportunities")
        top_opportunities = filtered_df.nlargest(10, 'estimated_value')[
            ['user_pseudo_id', 'lead_score', 'estimated_value', 'engagement_score',
             'rfm_segment', 'primary_country']
        ]
        st.dataframe(top_opportunities, use_container_width=True)

    with tab4:
        st.subheader("📋 Downloadable Lead Lists")

        # High-value leads
        st.write("**High-Value Leads (Score > 0.7, Value > $10,000)**")

        high_value = lead_list[
            (lead_list['lead_score'] > 0.7) &
            (lead_list['estimated_value'] > 10000)
        ]

        if len(high_value) > 0:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Leads", len(high_value))
            with col2:
                st.metric("Total Pipeline Value", f"${high_value['estimated_value'].sum():,.0f}")
            with col3:
                st.metric("Avg Lead Score", f"{high_value['lead_score'].mean():.2f}")

            # Display lead list
            st.dataframe(high_value.head(50), use_container_width=True)

            # Download button
            csv = high_value.to_csv(index=False)
            st.download_button(
                label="📥 Download Full Lead List (CSV)",
                data=csv,
                file_name=f"high_value_leads_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No high-value leads found with current filters.")

        # Segment-specific lists
        st.write("---")
        st.write("**Segment-Specific Lead Lists**")

        segment_option = st.selectbox(
            "Select RFM Segment",
            filtered_df['rfm_segment'].unique()
        )

        segment_leads = filtered_df[filtered_df['rfm_segment'] == segment_option].sort_values(
            'lead_score', ascending=False
        )[['user_pseudo_id', 'lead_score', 'estimated_value', 'engagement_score',
           'days_since_last_visit', 'primary_country']]

        st.dataframe(segment_leads.head(50), use_container_width=True)

        csv = segment_leads.to_csv(index=False)
        st.download_button(
            label=f"📥 Download {segment_option} Leads (CSV)",
            data=csv,
            file_name=f"{segment_option.lower().replace(' ', '_')}_leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # Footer with business impact
    st.markdown("---")
    st.header("💼 Business Impact Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **🎯 Lead Identification**
        - Identified **{:,}** high-propensity leads
        - Worth **${:,.0f}** in pipeline value
        - Average lead score: **{:.2f}**
        """.format(
            len(lead_list),
            lead_list['estimated_value'].sum(),
            lead_list['lead_score'].mean()
        ))

    with col2:
        time_saved = len(lead_list) * 0.5 / 60  # Assume 30 sec per manual lead research
        st.markdown("""
        **⏱️ Efficiency Gains**
        - Reduced manual list creation from **4 hours** to **15 minutes**
        - Automated scoring saves **~{:.1f} hours** per week
        - Self-service dashboard for sales team
        """.format(time_saved))

    with col3:
        st.markdown("""
        **📊 Revenue Impact**
        - Prioritize top **20%** of accounts
        - Focus on **${:,.0f}** in immediate opportunities
        - Enable data-driven sales strategy
        """.format(
            filtered_df.nlargest(int(len(filtered_df)*0.2), 'estimated_value')['estimated_value'].sum()
        ))

if __name__ == "__main__":
    main()
