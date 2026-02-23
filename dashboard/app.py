"""
dashboard/app.py
BART Real-Time Transit Intelligence Dashboard
Run: streamlit run dashboard/app.py
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

# Page config 
st.set_page_config(
    page_title="BART Transit Intelligence",
    page_icon="🚇",
    layout="wide"
)

#  Background Image Configuration 
def set_background_image():
    """Injects custom CSS to set the page background image with a dark overlay."""
    page_bg_img = """
    <style>
    /* Target the main app container */
    [data-testid="stAppViewContainer"] {
        /* Using a verified Unsplash image of the Glen Park BART Station in SF. */
        background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
                          url("https://unsplash.com/photos/xbhez0Z6nkE/download?w=2000");
        background-size: cover;
        
        /* FIX: Shifted from 'center' to 'center 80%' to move the train up behind the title */
        background-position: center 80%; 
        
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    /* Make the top header transparent so it doesn't block the image */
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

# Call the function to apply the background
set_background_image()

# Snowflake connection 
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse="BART_WH",
        database="BART_TRANSIT",
        schema="STAGING",
    )

@st.cache_data(ttl=300)  # refresh every 5 minutes
def load_data() -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT 
            station_name, destination, line_color,
            minutes_to_departure, delay_seconds,
            delay_minutes, is_delayed, delay_category,
            direction, platform, train_cars, ingestion_hour
        FROM TRIPS
        ORDER BY delay_seconds DESC
    """
    cursor = conn.cursor()
    cursor.execute(query)
    # Snowflake returns column names in ALL CAPS by default
    df = cursor.fetch_pandas_all()
    cursor.close()
    return df

# Load data 
df = load_data()

# Header 
st.title("🚇 BART Real-Time Transit Intelligence")
st.markdown("Built with **Python · Spark · Snowflake · Airflow · Streamlit**")
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🚆 Total Trains Tracked",
        value=len(df)
    )
with col2:
    delayed = len(df[df["IS_DELAYED"] == "Yes"])
    st.metric(
        label="⚠️ Delayed Trains",
        value=delayed,
        delta=f"{round(delayed/len(df)*100, 1)}% of all trains",
        delta_color="inverse"
    )
with col3:
    avg_delay = round(df["DELAY_SECONDS"].mean(), 1)
    st.metric(
        label="⏱️ Avg Delay (seconds)",
        value=avg_delay
    )
with col4:
    worst = df["DELAY_SECONDS"].max()
    worst_line = df.loc[df["DELAY_SECONDS"].idxmax(), "LINE_COLOR"]
    st.metric(
        label="🔴 Worst Delay",
        value=f"{worst} sec",
        delta=f"{worst_line} line",
        delta_color="inverse"
    )

st.divider()

# Charts Row 1 
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(" Avg Delay by Line")
    line_stats = df.groupby("LINE_COLOR").agg(
        avg_delay=("DELAY_SECONDS", "mean"),
        total_trains=("LINE_COLOR", "count"),
        delayed=("IS_DELAYED", lambda x: (x == "Yes").sum())
    ).reset_index()
    line_stats["avg_delay"] = line_stats["avg_delay"].round(1)

    color_map = {
        "GREEN":  "#339933",
        "RED":    "#ff0000",
        "YELLOW": "#ffff33",
        "BLUE":   "#0099cc",
        "ORANGE": "#ff9933",
    }

    fig1 = px.bar(
        line_stats.sort_values("avg_delay", ascending=False),
        x="LINE_COLOR",
        y="avg_delay",
        color="LINE_COLOR",
        color_discrete_map=color_map,
        title="Average Delay by BART Line (seconds)",
        labels={"avg_delay": "Avg Delay (sec)", "LINE_COLOR": "Line"},
        text="avg_delay"
    )
    fig1.update_traces(textposition="outside")
    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig1, width="stretch")

with col_right:
    st.subheader(" Delay Category Breakdown")
    cat_counts = df["DELAY_CATEGORY"].value_counts().reset_index()
    cat_counts.columns = ["category", "count"]

    fig2 = px.pie(
        cat_counts,
        names="category",
        values="count",
        title="Train Status Distribution",
        color="category",
        color_discrete_map={
            "On Time":  "#339933",
            "Minor":    "#ffff33",
            "Moderate": "#ff9933",
            "Severe":   "#ff0000",
        },
        hole=0.4
    )
    st.plotly_chart(fig2, width="stretch")

st.divider()

# Charts Row 2
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader(" Top 10 Most Delayed Stations")
    station_delays = df.groupby("STATION_NAME")["DELAY_SECONDS"].mean().reset_index()
    station_delays.columns = ["station", "avg_delay"]
    station_delays = station_delays.sort_values("avg_delay", ascending=False).head(10)
    station_delays["avg_delay"] = station_delays["avg_delay"].round(1)

    fig3 = px.bar(
        station_delays,
        x="avg_delay",
        y="station",
        orientation="h",
        title="Average Delay by Station (seconds)",
        labels={"avg_delay": "Avg Delay (sec)", "station": ""},
        color="avg_delay",
        color_continuous_scale="Reds",
        text="avg_delay"
    )
    fig3.update_traces(textposition="outside")
    fig3.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    st.plotly_chart(fig3, width="stretch")

with col_right2:
    st.subheader(" Delays by Direction")
    dir_stats = df.groupby(["LINE_COLOR", "DIRECTION"])["DELAY_SECONDS"].mean().reset_index()
    dir_stats.columns = ["line", "direction", "avg_delay"]
    dir_stats["avg_delay"] = dir_stats["avg_delay"].round(1)

    fig4 = px.bar(
        dir_stats,
        x="line",
        y="avg_delay",
        color="direction",
        barmode="group",
        title="Avg Delay by Line & Direction",
        labels={"avg_delay": "Avg Delay (sec)", "line": "Line"},
    )
    st.plotly_chart(fig4, width="stretch")

st.divider()

# Live Delayed Trains Table 
st.subheader(" Currently Delayed Trains")
delayed_df = df[df["IS_DELAYED"] == "Yes"][[
    "STATION_NAME", "DESTINATION", "LINE_COLOR",
    "MINUTES_TO_DEPARTURE", "DELAY_SECONDS", "DELAY_CATEGORY", "DIRECTION"
]].sort_values("DELAY_SECONDS", ascending=False)

delayed_df.columns = ["Station", "Destination", "Line", "Departs In (min)", "Delay (sec)", "Category", "Direction"]

st.dataframe(
    delayed_df,
    width="stretch",
    hide_index=True
)

# Footer
st.divider()
st.caption("Built by Yashashree Shinde · MS Applied Data Intelligence · SJSU · Data refreshes every 5 min")