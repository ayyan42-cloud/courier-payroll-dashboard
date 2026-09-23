import streamlit as st
import pandas as pd
import plotly.express as px
from google_sheets and XLSX import load_data, upsert_rows
from payslip import render_payslip

st.set_page_config(page_title="Courier Payroll Dashboard", page_icon="🚴", layout="wide")

# ── BULLETPROOF LOGIN SYSTEM ──────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    st.caption("Please log in to access the payroll dashboard.")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # Check credentials against Streamlit Secrets
        correct_user = st.secrets.get("auth", {}).get("username", "admin")
        correct_pass = st.secrets.get("auth", {}).get("password", "admin123")
        
        if username == correct_user and password == correct_pass:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()  # This stops the rest of the app from loading until logged in
# ──────────────────────────────────────────────────────────────────────

# If we get here, the user is logged in!
st.sidebar.success("Logged in successfully!")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ── LOAD DATA ─────────────────────────────────────────────────────────
st.title("📊 Courier Payroll Dashboard")

@st.cache_data(ttl=300)
def get_data():
    try:
        return load_data()
    except Exception as e:
        st.error(f"Could not connect to Google Sheet: {e}")
        st.stop()

df = get_data()

if df.empty:
    st.info("No data yet. Upload an Excel file from the sidebar.")
    st.stop()

# ── SIDEBAR FILTERS & UPLOAD ──────────────────────────────────────────
st.sidebar.markdown("### 📤 Upload New Data")
uploaded = st.sidebar.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
if uploaded:
    df_upload = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
    if st.sidebar.button("Import to Google Sheet"):
        upsert_rows(df_upload)
        st.cache_data.clear()
        st.sidebar.success("Data imported!")

st.sidebar.markdown("### 🔎 Filters")
months = sorted(df["pay month"].dropna().unique())
sel_months = st.sidebar.multiselect("Pay Month", months, default=months)

riders = sorted(df["courier name"].dropna().unique())
sel_riders = st.sidebar.multiselect("Courier", riders, default=riders)

fdf = df[df["pay month"].isin(sel_months) & df["courier name"].isin(sel_riders)].copy()

# ── KPI ROW ───────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("💰 Total Earnings", f"AED {fdf['rider earnings'].sum():,.0f}")
k2.metric("🏢 Company Expenses", f"AED {fdf['Company Expenses'].sum():,.0f}")
k3.metric("📦 Delivered Orders", f"{fdf['delivered orders'].sum():,.0f}")
k4.metric("💵 Total Payable", f"AED {fdf['rider payable amount'].sum():,.0f}")
k5.metric("📈 Avg / Order", f"AED {(fdf['rider earnings'].sum() / fdf['delivered orders'].sum()):,.2f}")

st.divider()

# ── VISUALS & DATA ────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Trends", "🥇 Riders", "📋 Data & Pay Slip"])

with tab1:
    monthly = fdf.groupby("pay month", as_index=False).agg(Earnings=("rider earnings", "sum"), Payable=("rider payable amount", "sum"))
    fig = px.line(monthly, x="pay month", y=["Earnings", "Payable"], markers=True, title="Monthly Earnings vs Payable")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    rider_summary = fdf.groupby("courier name", as_index=False).agg(Earnings=("rider earnings", "sum"), Orders=("delivered orders", "sum")).sort_values("Earnings", ascending=False).head(15)
    fig3 = px.bar(rider_summary, x="Earnings", y="courier name", orientation="h", title="Top 15 Riders by Earnings")
    st.plotly_chart(fig3, use_container_width=True)

with tab3:
    st.dataframe(fdf, use_container_width=True, height=400)
    st.subheader("🖨️ Generate Pay Slip")
    rider_sel = st.selectbox("Select Rider", sorted(fdf["courier name"].unique()))
    month_sel = st.selectbox("Select Month", sorted(fdf["pay month"].unique()))
    target = fdf[(fdf["courier name"] == rider_sel) & (fdf["pay month"] == month_sel)]
    if not target.empty:
        render_payslip(target.iloc[0])
