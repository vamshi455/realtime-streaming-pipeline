"""Streamlit Synthetic Data Generator Dashboard"""

import streamlit as st
import json
import requests
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/app/../shared')

from data_generator import DataGenerator, parse_natural_language_prompt

# Config
PRODUCER_URL = "http://producer:8000"
st.set_page_config(page_title="Synthetic Data Generator", layout="wide")

# Sidebar config
st.sidebar.title("⚙️ Configuration")
producer_host = st.sidebar.text_input("Producer URL", PRODUCER_URL)

# Main title
st.title("🔧 Synthetic Data Generator")
st.markdown("Generate and emit synthetic data to Kafka. **For testing and learning only.**")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Quick Generate", "🎯 Advanced", "📊 Preview", "📋 History"])

# ==============================================================================
# TAB 1: Quick Generate (NLP)
# ==============================================================================
with tab1:
    st.header("Natural Language Generator")
    st.markdown("Describe what data you want to generate:")

    col1, col2 = st.columns([3, 1])
    with col1:
        prompt = st.text_area(
            "Enter generation prompt:",
            value="Generate 10 LMP ticks for HB_NORTH between 40 and 50",
            height=80,
            help="Examples:\n- Generate 100 LMP ticks for HB_NORTH between 40 and 50\n- Create 50 deal events with volumes 100-500\n- 100 IoT sensor readings for temperature between 20-30"
        )

    with col2:
        st.markdown("### Examples")
        st.markdown("""
        **Power Trading:**
        - Generate 100 LMP ticks between 40-50
        - Create 50 deal events
        - 30 nomination confirmations

        **IoT:**
        - 1000 temperature sensor readings 20-30°C
        - 500 humidity readings 30-80%

        **Finance:**
        - 100 AAPL price ticks 150-200
        """)

    # Parse and generate
    try:
        if st.button("🚀 Generate & Emit", key="quick_emit", use_container_width=True):
            with st.spinner("Parsing prompt..."):
                params = parse_natural_language_prompt(prompt)

            event_type = params["event_type"]
            count = params["count"]
            constraints = params["constraints"]

            st.success(f"✓ Parsed: **{count}** {event_type} events")
            st.json(params)

            # Generate
            with st.spinner(f"Generating {count} events..."):
                gen = DataGenerator()
                events = gen.generate(event_type, count=count, **constraints)

            # Emit to Kafka
            with st.spinner("Emitting to Kafka..."):
                emit_payload = {
                    "event_type": event_type,
                    "count": count,
                    "events": events,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                try:
                    response = requests.post(
                        f"{producer_host}/emit/batch",
                        json=emit_payload,
                        timeout=10
                    )
                    if response.status_code == 200:
                        st.success(f"✅ Emitted {count} events to Kafka!")
                        st.json(response.json())
                    else:
                        st.error(f"Failed: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Error emitting: {e}")

    except ValueError as e:
        st.error(f"❌ Parse error: {e}")


# ==============================================================================
# TAB 2: Advanced (Structured)
# ==============================================================================
with tab2:
    st.header("Advanced Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("1. Event Type")
        event_type = st.selectbox(
            "Select event type:",
            ["lmp_tick", "deal_event", "nomination_event", "iot_sensor", "financial_price"],
            key="event_type_adv"
        )

    with col2:
        st.subheader("2. Count")
        count = st.number_input(
            "Number of events:",
            min_value=1,
            max_value=10000,
            value=100,
            step=10,
            key="count_adv"
        )

    with col3:
        st.subheader("3. Frequency")
        frequency = st.selectbox(
            "Frequency:",
            ["Once", "Every 1 min", "Every 5 min", "Every 15 min", "Every 1 hour"],
            key="frequency_adv"
        )

    # Constraints by event type
    st.subheader("4. Constraints")

    constraints = {}

    if event_type == "lmp_tick":
        col1, col2, col3 = st.columns(3)
        with col1:
            lmp_min = st.number_input("LMP Min", value=35.0, step=0.5)
        with col2:
            lmp_max = st.number_input("LMP Max", value=60.0, step=0.5)
        with col3:
            nodes = st.multiselect(
                "Nodes",
                ["HB_NORTH", "HB_SOUTH", "HB_HOUSTON"],
                default=["HB_NORTH", "HB_SOUTH", "HB_HOUSTON"]
            )
        constraints = {"lmp_range": (lmp_min, lmp_max), "nodes": nodes}

    elif event_type == "deal_event":
        col1, col2 = st.columns(2)
        with col1:
            vol_min = st.number_input("Volume Min (MW)", value=50.0, step=10.0)
        with col2:
            vol_max = st.number_input("Volume Max (MW)", value=500.0, step=10.0)
        deal_types = st.multiselect(
            "Deal Types",
            ["NEW", "AMENDED", "CANCELLED"],
            default=["NEW", "AMENDED"]
        )
        constraints = {"volume_range": (vol_min, vol_max), "deal_types": deal_types}

    elif event_type == "iot_sensor":
        col1, col2, col3 = st.columns(3)
        with col1:
            val_min = st.number_input("Value Min", value=10.0, step=0.5)
        with col2:
            val_max = st.number_input("Value Max", value=40.0, step=0.5)
        with col3:
            location = st.text_input("Location", value="New York")
        sensor_types = st.multiselect(
            "Sensor Types",
            ["temperature", "humidity", "pressure"],
            default=["temperature"]
        )
        constraints = {"value_range": (val_min, val_max), "location": location, "sensor_types": sensor_types}

    elif event_type == "financial_price":
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("Symbol", value="AAPL")
        with col2:
            price_min = st.number_input("Price Min", value=100.0, step=1.0)
        with col3:
            price_max = st.number_input("Price Max", value=200.0, step=1.0)
        constraints = {"symbol": symbol, "price_range": (price_min, price_max)}

    # Emit button
    if st.button("🚀 Generate & Emit", key="adv_emit", use_container_width=True):
        with st.spinner(f"Generating {count} {event_type} events..."):
            gen = DataGenerator()
            events = gen.generate(event_type, count=count, **constraints)

        # Preview
        st.success(f"Generated {count} events:")
        with st.expander("View sample (first 3)"):
            for i, event in enumerate(events[:3]):
                st.json(event)

        # Emit
        with st.spinner("Emitting to Kafka..."):
            emit_payload = {
                "event_type": event_type,
                "count": count,
                "events": events,
                "frequency": frequency,
                "constraints": constraints,
                "timestamp": datetime.utcnow().isoformat(),
            }

            try:
                response = requests.post(
                    f"{producer_host}/emit/batch",
                    json=emit_payload,
                    timeout=10
                )
                if response.status_code == 200:
                    st.success(f"✅ Emitted {count} events!")
                    st.json(response.json())
                else:
                    st.error(f"Failed: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")


# ==============================================================================
# TAB 3: Preview
# ==============================================================================
with tab3:
    st.header("Preview Generated Data")

    col1, col2 = st.columns(2)
    with col1:
        preview_type = st.selectbox(
            "Event Type",
            ["lmp_tick", "deal_event", "nomination_event", "iot_sensor", "financial_price"],
            key="preview_type"
        )
    with col2:
        preview_count = st.number_input("Count", 1, 10, 3, key="preview_count")

    if st.button("🔍 Generate Preview", use_container_width=True):
        with st.spinner("Generating preview..."):
            gen = DataGenerator()
            events = gen.generate(preview_type, count=preview_count)

        st.subheader(f"{preview_count} Sample {preview_type} Events")
        for i, event in enumerate(events, 1):
            with st.expander(f"Event {i}"):
                st.json(event)

        # Table view
        import pandas as pd
        df = pd.DataFrame(events)
        st.subheader("Table View")
        st.dataframe(df, use_container_width=True)

        # Download
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download as CSV",
            csv,
            f"{preview_type}_{datetime.now().isoformat()}.csv",
            "text/csv"
        )


# ==============================================================================
# TAB 4: Status
# ==============================================================================
with tab4:
    st.header("📋 Generation History & Status")

    # Check Producer health
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Check Producer Health"):
            try:
                response = requests.get(f"{producer_host}/health", timeout=5)
                if response.status_code == 200:
                    st.success("✅ Producer is healthy")
                    st.json(response.json())
                else:
                    st.error("❌ Producer is not responding")
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        if st.button("📊 Get Metrics"):
            try:
                response = requests.get(f"{producer_host}/metrics", timeout=5)
                if response.status_code == 200:
                    st.success("✅ Metrics retrieved")
                    metrics = response.json()
                    st.json(metrics)

                    # Show summary
                    st.metric("Total Events Emitted", metrics.get("events_emitted_total", 0))
                else:
                    st.error("Failed to get metrics")
            except Exception as e:
                st.error(f"Error: {e}")

    # Instructions
    st.subheader("📖 How to Use")
    st.markdown("""
    1. **Quick Generate (Tab 1)**: Type what data you want
       - Example: "Generate 100 LMP ticks between 40-50"
       - Supports natural language parsing

    2. **Advanced (Tab 2)**: Fine-grained control
       - Select event type, count, constraints
       - Customize ranges, locations, etc.

    3. **Preview (Tab 3)**: See data before emitting
       - Generate and review
       - Export as CSV

    4. **Status (Tab 4)**: Monitor producer
       - Health checks
       - Event metrics
       - View emission history

    **Data Destinations:**
    - Kafka topic (based on event type)
    - SMB shared drive (via Bronze consumer)
    - Organized by asset_key (delivery_node, deal_id, etc.)
    """)

    st.divider()
    st.caption("🔒 For authorized testing/learning only. Do not use for production data.")
