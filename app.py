"""DriveLegal India Streamlit application.

All runtime data is bundled locally. Calculation and validation logic lives in
app_core.py so it can be tested independently of the UI.
"""

from __future__ import annotations

import streamlit as st

from app_core import (
    ALL_STATES,
    LEGAL_SECTIONS,
    METADATA,
    NATIONAL_FINES,
    STATE_DATA,
    VEHICLE_TYPES,
    CalculatorInputError,
    calculate_fine,
    get_allowed_vehicle_types,
    get_source_details,
    get_violation_options,
)


st.set_page_config(
    page_title="DriveLegal India",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main-header { background: linear-gradient(135deg,#1a237e 0%,#283593 50%,#1565c0 100%); padding:2rem; border-radius:12px; margin-bottom:1.5rem; color:white; text-align:center; }
        .main-header h1 { font-size:2.5rem; margin:0; }
        .main-header p { font-size:1.1rem; opacity:.85; margin:.5rem 0 0; }
        .fine-box { background:#fff3e0; border:2px solid #ff6f00; padding:1.2rem; border-radius:10px; margin-top:1rem; }
        .fine-total { font-size:2rem; font-weight:bold; color:#e65100; }
        .section-badge { background:#1565c0; color:white; padding:.2rem .7rem; border-radius:20px; font-size:.8rem; font-weight:bold; }
        .state-note { background:#e8f5e9; border-left:4px solid #2e7d32; padding:.6rem 1rem; border-radius:4px; margin:.3rem 0; font-size:.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="main-header">
        <h1>🚦 DriveLegal India</h1>
        <p>Location-specific traffic-law reference and challan estimator</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 📍 Select Location")
    selected_state = st.selectbox("State / Union Territory", ALL_STATES, index=ALL_STATES.index("Delhi"))
    state_info = STATE_DATA[selected_state]
    st.markdown("---")
    st.markdown(f"### 🏛 {selected_state}")
    st.metric("City Speed Limit", f"{state_info['speed_city']} km/h")
    st.metric("Highway Speed Limit", f"{state_info['speed_highway']} km/h")
    st.metric("Reference Surcharge", f"{state_info['surcharge'] * 100:.0f}%")
    st.markdown(f"**Helmet Law:** {state_info['helmet_law']}")
    st.markdown("---")
    st.caption("Offline data package: no runtime API or remote image dependency.")
    st.caption(f"Data reviewed: {METADATA['last_reviewed']}")


tab1, tab2, tab3, tab4 = st.tabs([
    "🧮 Challan Estimator",
    "📋 Traffic Laws",
    "🗺️ State-wise Rules",
    "ℹ️ About DriveLegal",
])

with tab1:
    st.markdown(f"## 🧮 Challan Estimator — {selected_state}")
    st.info(METADATA["disclaimer"])

    violation_options = get_violation_options()
    selected_violation_label = st.selectbox("Select violation", list(violation_options))
    selected_violation_key = violation_options[selected_violation_label]
    violation = NATIONAL_FINES[selected_violation_key]
    allowed_vehicles = get_allowed_vehicle_types(selected_violation_key)
    vehicle_type = st.selectbox("Vehicle type", allowed_vehicles)

    quantity = None
    if violation["fine_basis"] == "per_excess_passenger":
        quantity = st.number_input(violation["quantity_label"], min_value=1, value=1, step=1)
    elif violation["fine_basis"] == "base_plus_excess_tonne":
        quantity = st.number_input(violation["quantity_label"], min_value=0.0, value=0.0, step=0.1)

    repeat = False
    if violation["repeat_policy"] == "toggle":
        repeat = st.checkbox("Repeat offence (reference amount doubled)")
    elif violation["repeat_policy"] == "explicit":
        repeat = st.checkbox(f"Use repeat-offence reference amount (₹{violation['repeat_fine']:,})")
    else:
        st.caption("A repeat toggle is not applied to this offence because its statutory record is fixed or quantity-based.")

    with st.expander("🚗 Vehicle-type reference"):
        st.dataframe(
            [{"Vehicle category": name, "Multiplier": f"{factor:.1f}x"} for name, factor in VEHICLE_TYPES.items()],
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Vehicle multipliers are applied only to offence records that explicitly opt in. They are not used to invent statutory fine amounts.")

    if st.button("⚡ Calculate reference amount", type="primary", use_container_width=True):
        try:
            result = calculate_fine(selected_violation_key, vehicle_type, selected_state, repeat, quantity)
        except CalculatorInputError as exc:
            st.error(str(exc))
        else:
            st.markdown("---")
            st.markdown(f"### 📄 Calculation Breakdown — {selected_state}")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Reference Fine", f"₹{result['base_fine']:,.2f}")
            r2.metric("Vehicle Adjustment", f"₹{result['vehicle_adjustment']:,.2f}")
            r3.metric("State Surcharge", f"₹{result['state_surcharge']:,.2f}")
            r4.metric("Repeat Penalty", f"₹{result['repeat_penalty']:,.2f}")
            st.markdown(
                f"""
                <div class="fine-box">
                    <p style="margin:0;font-size:1rem;">Estimated Reference Amount</p>
                    <p class="fine-total">₹{result['total']:,.2f}</p>
                    <span class="section-badge">Rule Section {result['rule_section']} · Penalty Section {result['penalty_section']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if result["imprisonment"]:
                st.warning(f"Potential custodial consequence in the source record: {result['imprisonment']}")
            if result["legal_note"]:
                st.caption(result["legal_note"])
            if result["source_status"] != "act_reference":
                st.warning("This amount is a reference value and must be checked against the latest state notification or official challan portal.")
            with st.expander("🔎 Bundled source references"):
                st.caption(f"Source status: `{result['source_status']}`")
                for source in result["sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']}) (`{source['id']}`)")
            st.markdown("#### 📌 State-specific reference notes")
            for note in state_info["notes"]:
                st.markdown(f'<div class="state-note">• {note}</div>', unsafe_allow_html=True)

    with st.expander("📊 View national fine records"):
        rows = []
        for record in NATIONAL_FINES.values():
            rows.append(
                {
                    "Violation": record["description"],
                    "Rule section": record["rule_section"],
                    "Penalty section": record["penalty_section"],
                    "Reference fine (₹)": f"₹{record['fine']:,}",
                    "Basis": record["fine_basis"],
                    "Source status": record["source_status"],
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("## 📋 Traffic Laws — India")
    st.warning("Sections are shown separately as the rule/duty section and the penalty section. Amounts are informational references, not official challan determinations.")
    for law in LEGAL_SECTIONS:
        with st.expander(f"**Section {law['section']}** — {law['title']}"):
            st.write(law["description"])

    st.markdown("### 🌐 National speed-limit reference")
    st.dataframe(
        [
            {"Category": "Cars / Jeeps / Taxis", "Urban (km/h)": 50, "NH/SH (km/h)": 100, "Expressway (km/h)": 120},
            {"Category": "Two-wheelers", "Urban (km/h)": 50, "NH/SH (km/h)": 80, "Expressway (km/h)": 80},
            {"Category": "Autorickshaw / Three-wheeler", "Urban (km/h)": 40, "NH/SH (km/h)": 60, "Expressway (km/h)": "Not permitted"},
            {"Category": "Buses", "Urban (km/h)": 50, "NH/SH (km/h)": 80, "Expressway (km/h)": 100},
            {"Category": "Trucks / HMV", "Urban (km/h)": 40, "NH/SH (km/h)": 80, "Expressway (km/h)": 80},
            {"Category": "School buses", "Urban (km/h)": 25, "NH/SH (km/h)": 60, "Expressway (km/h)": "Not permitted"},
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.markdown("## 🗺️ State and UT reference rules")
    search_term = st.text_input("🔍 Search state or Union Territory", placeholder="e.g. Maharashtra, Delhi, Goa")
    filtered_states = [state for state in ALL_STATES if not search_term or search_term.lower() in state.lower()]
    for state in filtered_states:
        info = STATE_DATA[state]
        surcharge_text = f"+{info['surcharge'] * 100:.0f}% reference surcharge" if info["surcharge"] else "No reference surcharge"
        with st.expander(f"**{state}** — {info['speed_city']} km/h city · {info['speed_highway']} km/h highway · {surcharge_text}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("City speed", f"{info['speed_city']} km/h")
            c2.metric("Highway speed", f"{info['speed_highway']} km/h")
            c3.metric("Reference surcharge", f"{info['surcharge'] * 100:.0f}%")
            st.markdown(f"**Helmet law:** {info['helmet_law']}")
            for note in info["notes"]:
                st.markdown(f'<div class="state-note">• {note}</div>', unsafe_allow_html=True)
            st.caption(f"Source status: `{info['source_status']}`")
            if info["source_ids"]:
                with st.expander("🔎 Bundled source references"):
                    st.caption("These bundled sources support the general legal context; state-specific values still require the latest local notification.")
                    for source in get_source_details(info["source_ids"]):
                        st.markdown(f"- [{source['title']}]({source['url']}) (`{source['id']}`)")
            st.caption(info["legal_note"])

with tab4:
    st.markdown("## ℹ️ About DriveLegal India")
    st.markdown(
        "DriveLegal India is an offline informational reference and challan estimator covering 28 states and 8 Union Territories. It does not query official challan records, use geolocation, or replace a government portal."
    )
    st.markdown("### Data and legal references")
    for source in METADATA["sources"]:
        st.markdown(f"- **{source['title']}**: {source['url']}")
    st.markdown("### Legal disclaimer")
    st.info(METADATA["disclaimer"])
    c1, c2, c3 = st.columns(3)
    c1.metric("States covered", "28")
    c2.metric("Union Territories", "8")
    c3.metric("Violation records", str(len(NATIONAL_FINES)))
