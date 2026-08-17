

import streamlit as st
import json
import pathlib
from datetime import datetime



# National fine schedule — Motor Vehicles (Amendment) Act 2019
# Data is now stored in structured JSON files under data/ (see data/README.md).
_DATA_DIR = pathlib.Path(__file__).parent / "data"

with open(_DATA_DIR / "national_fines.json") as _f:
    NATIONAL_FINES = json.load(_f)

with open(_DATA_DIR / "vehicle_types.json") as _f:
    VEHICLE_TYPES = json.load(_f)

with open(_DATA_DIR / "state_data.json") as _f:
    STATE_DATA = json.load(_f)

ALL_STATES = sorted(STATE_DATA.keys())

# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def calculate_fine(violation_key: str, vehicle_key: str, state: str, repeat: bool) -> dict:
    base = NATIONAL_FINES[violation_key]["fine"]
    multiplier = VEHICLE_TYPES[vehicle_key]
    surcharge_rate = STATE_DATA[state]["surcharge"]
    repeat_mult = 2.0 if repeat else 1.0

    adjusted = base * multiplier
    state_surcharge = adjusted * surcharge_rate
    repeat_penalty = adjusted * (repeat_mult - 1)
    total = adjusted + state_surcharge + repeat_penalty

    return {
        "base_fine": base,
        "vehicle_adjustment": adjusted - base,
        "state_surcharge": state_surcharge,
        "repeat_penalty": repeat_penalty,
        "total": total,
        "section": NATIONAL_FINES[violation_key]["section"],
        "imprisonment": NATIONAL_FINES[violation_key]["imprisonment"],
    }


def get_violation_options():
    return {v["description"]: k for k, v in NATIONAL_FINES.items()}


# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="DriveLegal India",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #1565c0 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
    }
    .main-header h1 { font-size: 2.5rem; margin: 0; }
    .main-header p  { font-size: 1.1rem; opacity: 0.85; margin: 0.5rem 0 0; }

    .info-card {
        background: #f8f9ff;
        border-left: 5px solid #1565c0;
        padding: 1rem 1.2rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }
    .fine-box {
        background: #fff3e0;
        border: 2px solid #ff6f00;
        padding: 1.2rem;
        border-radius: 10px;
        margin-top: 1rem;
    }
    .fine-total {
        font-size: 2rem;
        font-weight: bold;
        color: #e65100;
    }
    .section-badge {
        background: #1565c0;
        color: white;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .state-note {
        background: #e8f5e9;
        border-left: 4px solid #2e7d32;
        padding: 0.6rem 1rem;
        border-radius: 4px;
        margin: 0.3rem 0;
        font-size: 0.9rem;
    }
    .warning-box {
        background: #ffebee;
        border-left: 4px solid #c62828;
        padding: 0.8rem 1rem;
        border-radius: 4px;
    }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🚦 DriveLegal India</h1>
    <p>Location-specific traffic laws, violations & challan calculator</p>
</div>
""", unsafe_allow_html=True)

# Sidebar — location selector
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/41/Flag_of_India.svg", width=100)
    st.markdown("## 📍 Select Location")
    selected_state = st.selectbox("State / Union Territory", ALL_STATES, index=ALL_STATES.index("Delhi"))

    st.markdown("---")
    state_info = STATE_DATA[selected_state]
    st.markdown(f"### 🏛 {selected_state}")
    st.metric("City Speed Limit", f"{state_info['speed_city']} km/h")
    st.metric("Highway Speed Limit", f"{state_info['speed_highway']} km/h")

    surcharge_pct = state_info['surcharge'] * 100
    st.metric("State Surcharge", f"{surcharge_pct:.0f}%")

    st.markdown(f"**Helmet Law:** {state_info['helmet_law']}")

    st.markdown("---")
    st.caption("Data source: Motor Vehicles Act 1988 & Amendment Act 2019 (MV Amendment Act)")
    st.caption(f"Last updated: {datetime.now().strftime('%B %Y')}")

# ──────── TABS ────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🧮 Challan Calculator",
    "📋 Traffic Laws",
    "🗺️ State-wise Rules",
    "ℹ️ About DriveLegal",
])

# ══════════════════════════════════════════════════════════
#  TAB 1 — CHALLAN CALCULATOR
# ══════════════════════════════════════════════════════════
with tab1:
    st.markdown(f"## 🧮 Challan Calculator — {selected_state}")
    st.markdown("Calculate your exact challan amount including state surcharges and vehicle-type adjustments.")

    col1, col2 = st.columns(2)

    with col1:
        violation_options = get_violation_options()
        violation_labels = list(violation_options.keys())
        selected_violation_label = st.selectbox("Select Violation", violation_labels)
        selected_violation_key = violation_options[selected_violation_label]

        vehicle_type = st.selectbox("Vehicle Type", list(VEHICLE_TYPES.keys()))

    with col2:
        is_repeat = st.checkbox("⚠️ Repeat Offence (double fine applies)")
        st.markdown("&nbsp;", unsafe_allow_html=True)

        st.info(f"""
**📍 Current Location:** {selected_state}
**🏎️ City Limit:** {STATE_DATA[selected_state]['speed_city']} km/h
**🛣️ Highway Limit:** {STATE_DATA[selected_state]['speed_highway']} km/h
**🪖 Helmet Rule:** {STATE_DATA[selected_state]['helmet_law']}
        """)

    if st.button("⚡ Calculate Challan", type="primary", use_container_width=True):
        result = calculate_fine(selected_violation_key, vehicle_type, selected_state, is_repeat)
        viol_info = NATIONAL_FINES[selected_violation_key]

        st.markdown("---")
        st.markdown(f"### 📄 Challan Breakdown — {selected_state}")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Base Fine", f"₹{result['base_fine']:,.0f}")
        r2.metric("Vehicle Adj.", f"₹{result['vehicle_adjustment']:,.0f}")
        r3.metric("State Surcharge", f"₹{result['state_surcharge']:,.0f}")
        r4.metric("Repeat Penalty", f"₹{result['repeat_penalty']:,.0f}")

        st.markdown(f"""
<div class="fine-box">
    <p style="margin:0;font-size:1rem;">Total Payable Challan Amount</p>
    <p class="fine-total">₹{result['total']:,.0f}</p>
    <span class="section-badge">Section {result['section']} MV Act</span>
    {'<br><br><b>⚠️ Imprisonment possible: ' + result["imprisonment"] + '</b>' if result["imprisonment"] else ''}
</div>
""", unsafe_allow_html=True)

        # State-specific notes
        st.markdown("#### 📌 State-specific Enforcement Notes")
        for note in STATE_DATA[selected_state]["notes"]:
            st.markdown(f'<div class="state-note">• {note}</div>', unsafe_allow_html=True)

        if result["imprisonment"]:
            st.markdown(f"""
<div class="warning-box">
⚖️ <b>Legal Warning:</b> This violation (Section {result['section']}) carries potential imprisonment of <b>{result['imprisonment']}</b>
under the Motor Vehicles Act. A First Information Report (FIR) may be filed.
</div>
""", unsafe_allow_html=True)

    # Fine schedule table
    with st.expander("📊 View Full National Fine Schedule (MV Act 2019)"):
        rows = []
        for k, v in NATIONAL_FINES.items():
            rows.append({
                "Violation": v["description"],
                "Section": v["section"],
                "Base Fine (₹)": f"₹{v['fine']:,}",
                "Imprisonment": v["imprisonment"] or "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
#  TAB 2 — TRAFFIC LAWS
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 📋 Traffic Laws — India")

    st.markdown("### 🏛️ Motor Vehicles Act 1988 (Amended 2019) — Key Provisions")

    laws = [
        ("Section 112", "Speed Limits", "Central Government prescribes speed limits for different vehicle classes and road types. State governments may prescribe lower limits."),
        ("Section 119", "Traffic Signals & Signs", "Drivers must obey all traffic signals, signs, and road markings. Violation is an offence punishable with fine."),
        ("Section 128", "Safety of Passengers", "No vehicle shall carry more passengers than its registered capacity."),
        ("Section 129", "Protective Headgear", "Every person driving or riding on a motorcycle must wear a BIS-certified helmet."),
        ("Section 138(3)", "Seat Belts", "Every person occupying a seat in a motor vehicle must wear a seat belt as prescribed."),
        ("Section 177A", "Offences by Juveniles", "Guardian/owner liable for juvenile driving — ₹25,000 fine, juvenile ineligible for DL till 25 years."),
        ("Section 183", "Driving at Excessive Speed", "Punishable with fine up to ₹2,000 for LMV and ₹4,000 for heavier vehicles; repeat offence may lead to DL cancellation."),
        ("Section 184", "Dangerous Driving", "Driving dangerously, racing, or using mobile phone — fine up to ₹5,000 or imprisonment up to 6 months."),
        ("Section 185", "Drunk Driving", "BAC >30 mg/100 ml — first offence: fine ₹10,000 or 6 months imprisonment; repeat: fine ₹15,000 or 2 years imprisonment."),
        ("Section 194", "Overloading", "Goods vehicle overloading — fine ₹20,000 + ₹2,000 per extra tonne."),
        ("Section 196", "Insurance", "Driving without valid third-party insurance — fine ₹2,000 or imprisonment up to 3 months."),
        ("Section 199A", "Minor Driving", "Guardian / owner liable — ₹25,000 fine; vehicle registration cancelled for 12 months."),
    ]

    for sec, title, desc in laws:
        with st.expander(f"**{sec}** — {title}"):
            st.write(desc)

    st.markdown("---")
    st.markdown("### 🌐 Speed Limits — National Standard (MoRTH Notification)")

    speed_data = [
        {"Category": "Cars / Jeeps / Taxis", "Urban (km/h)": 50, "NH/SH (km/h)": 100, "Expressway (km/h)": 120},
        {"Category": "Two-wheelers", "Urban (km/h)": 50, "NH/SH (km/h)": 80, "Expressway (km/h)": 80},
        {"Category": "Autorickshaw / Three-wheeler", "Urban (km/h)": 40, "NH/SH (km/h)": 60, "Expressway (km/h)": "Not permitted"},
        {"Category": "Buses", "Urban (km/h)": 50, "NH/SH (km/h)": 80, "Expressway (km/h)": 100},
        {"Category": "Trucks / HMV", "Urban (km/h)": 40, "NH/SH (km/h)": 80, "Expressway (km/h)": 80},
        {"Category": "School Buses", "Urban (km/h)": 25, "NH/SH (km/h)": 60, "Expressway (km/h)": "Not permitted"},
    ]
    st.dataframe(speed_data, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 📱 How to Pay e-Challan (National Portal)")
    st.markdown("""
1. Visit **Parivahan Sewa** portal: `https://echallan.parivahan.gov.in`
2. Enter challan number **or** vehicle registration number
3. View pending challans — verify details
4. Pay via UPI / Net Banking / Credit-Debit Card
5. Download digital receipt

*State-specific portals may also be available — check sidebar for your state.*
""")

# ══════════════════════════════════════════════════════════
#  TAB 3 — STATE-WISE RULES
# ══════════════════════════════════════════════════════════
with tab3:
    st.markdown("## 🗺️ State & UT Specific Regulations")

    search_term = st.text_input("🔍 Search state/UT", placeholder="e.g. Maharashtra, Delhi, Goa…")

    filtered_states = [s for s in ALL_STATES if search_term.lower() in s.lower()] if search_term else ALL_STATES

    for state in filtered_states:
        info = STATE_DATA[state]
        surcharge_text = f"+{info['surcharge']*100:.0f}% surcharge" if info["surcharge"] > 0 else "No additional surcharge"

        with st.expander(f"**{state}** — 🏙️ {info['speed_city']} km/h city | 🛣️ {info['speed_highway']} km/h highway | {surcharge_text}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("City Speed Limit", f"{info['speed_city']} km/h")
            c2.metric("Highway Speed Limit", f"{info['speed_highway']} km/h")
            c3.metric("State Surcharge", f"{info['surcharge']*100:.0f}%")

            st.markdown(f"**🪖 Helmet Law:** {info['helmet_law']}")
            st.markdown("**📌 Enforcement Notes:**")
            for note in info["notes"]:
                st.markdown(f'<div class="state-note">• {note}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  TAB 4 — ABOUT
# ══════════════════════════════════════════════════════════
with tab4:
    st.markdown("## ℹ️ About DriveLegal India")
    st.markdown("""
**DriveLegal India** is an offline-capable, location-specific traffic law information and challan 
calculation tool covering all **28 states** and **8 Union Territories** of India.

### 🎯 Purpose
Citizens often lack easy access to clear, location-specific information about traffic laws, 
penalties, and enforcement procedures. DriveLegal bridges this gap by providing a centralized, 
user-friendly platform with:

- **Geo-fenced challan lookup** per state/UT
- **Automated Challan Calculator** based on violation type and vehicle category
- **Offline functionality** — all data embedded, no API calls
- **State-specific enforcement notes** for better compliance

### 📚 Data Sources
| Source | Coverage |
|--------|----------|
| Motor Vehicles Act 1988 | Base framework |
| MV Amendment Act 2019 | Updated fine schedule |
| MoRTH Notifications | Speed limits |
| State Transport Dept Rules | State surcharges & local rules |

### ⚖️ Legal Disclaimer
This tool is for **informational purposes only**. Fine amounts may vary based on court 
orders, latest government notifications, and enforcement discretion. Always verify with 
the official **Parivahan Sewa** portal or your state transport department for the most 
current information.

### 🛠️ Technology
- Python 
- Streamlit (UI framework)
- No external APIs 
    """)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("States Covered", "28")
    c2.metric("Union Territories", "8")
    c3.metric("Violations Catalogued", str(len(NATIONAL_FINES)))
