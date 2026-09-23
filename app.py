import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from datetime import datetime
from google_sheets import load_data, upsert_rows
from payslip import render_payslip

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Courier Payroll Dashboard",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; }
.kpi-card { background: #1e1e2e; border-radius: 12px; padding: 16px;
            border-left: 5px solid #7c3aed; }
</style>
""", unsafe_allow_html=True)

# ── Authentication ───────────────────────────────────────────
# Load auth config from Streamlit Secrets instead of a file
if "credentials" in st.secrets:
    config = {
        "credentials": dict(st.secrets["credentials"]),
        "cookie": dict(st.secrets["cookie"])
    }
else:
    st.error("Authentication secrets are missing! Please check your Secrets settings.")
    st.stop()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
    auto_hash=False,
)

authenticator.login("main")
name = st.session_state.get("name")
auth_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")

if not auth_status:
    st.warning("Please log in to access the payroll dashboard.")
    st.stop()

# ── Role resolution ──────────────────────────────────────────
user_roles = config["credentials"]["usernames"].get(username, {}).get("roles", [])
is_admin = "admin" in user_roles
is_viewer = "viewer" in user_roles and not is_admin

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/delivery.png", width=80)
    st.title("🚴 Courier Payroll")
    st.caption(f"Logged in as **{name}** · {'Admin' if is_admin else 'Viewer'}")
    authenticator.logout("Logout", "sidebar")

    st.divider()

    if is_admin:
        st.subheader("📤 Upload Data")
        uploaded = st.file_uploader(
            "Drop Excel / CSV file",
            type=["xlsx", "xls", "csv"],
            help="Columns must match the payroll header row.",
        )
        if uploaded:
            df_upload = pd.read_excel(uploaded) if uploaded.name.endswith((".xlsx", ".xls")) else pd.read_csv(uploaded)
            st.write("Preview:", df_upload.head(3))
            if st.button("✅ Import & Upsert to Google Sheet"):
                count = upsert_rows(df_upload)
                st.success(f"{count} new row(s) appended. Existing rider-month rows updated in place.")
                st.cache_data.clear()

        st.divider()
        st.subheader("👤 Manage Users")
        with st.expander("Change Username / Password"):
            new_user = st.text_input("New username")
            new_pass = st.text_input("New password", type="password")
            new_role = st.selectbox("Role", ["admin", "viewer"])
            if st.button("Update Credentials"):
                import streamlit_authenticator as sa
                hashed = sa.Hasher([new_pass]).generate()[0]
                config["credentials"]["usernames"][new_user] = {
                    "email": f"{new_user}@company.com",
                    "failed_login_attempts": 0,
                    "first_name": new_user.title(),
                    "last_name": "",
                    "logged_in": False,
                    "password": hashed,
                    "roles": [new_role],
                }
                with open("auth_config.yaml", "w") as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success(f"User '{new_user}' added/updated as {new_role}.")

    st.divider()
    st.caption("v1.0 · Data persisted in Google Sheets")

# ── Load data ────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_data():
    return load_data()

try:
    df = get_data()
except Exception as e:
    st.error(f"Could not load Google Sheet: {e}")
    st.stop()

if df.empty:
    st.info("No data yet. Admin can upload an Excel file from the sidebar.")
    st.stop()

# ── Normalise column names ───────────────────────────────────
df.columns = [c.strip() for c in df.columns]

# ── Filters (Slicers) ────────────────────────────────────────
st.sidebar.markdown("### 🔎 Filters")
months = sorted(df["pay month"].dropna().unique())
sel_months = st.sidebar.multiselect("Pay Month", months, default=months)

riders = sorted(df["courier name"].dropna().unique())
sel_riders = st.sidebar.multiselect("Courier", riders, default=riders)

mask = df["pay month"].isin(sel_months) & df["courier name"].isin(sel_riders)
fdf = df[mask].copy()

# Timeline slider
if "pay month" in fdf.columns:
    fdf["_date"] = pd.to_datetime(fdf["pay month"], errors="coerce")
    date_min, date_max = fdf["_date"].min(), fdf["_date"].max()
    if pd.notna(date_min) and pd.notna(date_max):
        timeline = st.sidebar.date_input(
            "Timeline",
            value=(date_min.date(), date_max.date()),
            min_value=date_min.date(),
            max_value=date_max.date(),
        )
        if isinstance(timeline, tuple):
            fdf = fdf[(fdf["_date"].dt.date >= timeline[0]) & (fdf["_date"].dt.date <= timeline[1])]

# ── KPI Row ──────────────────────────────────────────────────
st.title("📊 Courier Payroll Dashboard")
st.caption(f"Showing {len(fdf):,} rows · {fdf['courier name'].nunique()} riders · {fdf['pay month'].nunique()} month(s)")

k1, k2, k3, k4, k5 = st.columns(5)

total_earnings = fdf["rider earnings"].sum()
total_company = fdf["Company Expenses"].sum()
total_payable = fdf["rider payable amount"].sum()
total_orders = fdf["delivered orders"].sum()
avg_per_order = total_earnings / total_orders if total_orders else 0

k1.metric("💰 Total Rider Earnings", f"AED {total_earnings:,.0f}")
k2.metric("🏢 Company Expenses", f"AED {total_company:,.0f}")
k3.metric("📦 Delivered Orders", f"{total_orders:,.0f}")
k4.metric("💵 Total Payable", f"AED {total_payable:,.0f}")
k5.metric("📈 Avg / Order", f"AED {avg_per_order:,.2f}")

st.divider()

# ── Advanced Visuals ─────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🥇 Riders", "🧾 Deductions", "📋 Data & Pay Slip"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        monthly = fdf.groupby("pay month", as_index=False).agg(
            Earnings=("rider earnings", "sum"),
            Payable=("rider payable amount", "sum"),
        )
        fig = px.line(monthly, x="pay month", y=["Earnings", "Payable"],
                      markers=True, title="Monthly Earnings vs Payable",
                      color_discrete_sequence=["#7c3aed", "#10b981"])
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        orders = fdf.groupby("pay month", as_index=False)["delivered orders"].sum()
        fig2 = px.bar(orders, x="pay month", y="delivered orders",
                      title="Delivered Orders by Month", color="delivered orders",
                      color_continuous_scale="Purples")
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    rider_summary = fdf.groupby("courier name", as_index=False).agg(
        Earnings=("rider earnings", "sum"),
        Payable=("rider payable amount", "sum"),
        Orders=("delivered orders", "sum"),
    ).sort_values("Earnings", ascending=False).head(15)

    fig3 = px.bar(rider_summary, x="Earnings", y="courier name", orientation="h",
                  title="Top 15 Riders by Earnings", color="Payable",
                  color_continuous_scale="Viridis")
    st.plotly_chart(fig3, use_container_width=True)

with tab3:
    ded_cols = ["R.F Deduction", "Advance Money", "Other Deduction",
                "Leave Fine", "Parking", "Bike Fine", "Salik Payment"]
    ded_totals = {c: fdf[c].sum() for c in ded_cols if c in fdf.columns}
    ded_df = pd.DataFrame(list(ded_totals.items()), columns=["Deduction", "Amount"])
    fig4 = px.pie(ded_df, names="Deduction", values="Amount",
                  title="Deduction Breakdown", hole=0.45,
                  color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig4, use_container_width=True)

with tab4:
    st.dataframe(fdf, use_container_width=True, height=400)

    if is_admin:
        st.subheader("🖨️ Generate Pay Slip")
        rider_sel = st.selectbox("Select Rider", sorted(fdf["courier name"].unique()))
        month_sel = st.selectbox("Select Month", sorted(fdf["pay month"].unique()))
        target = fdf[(fdf["courier name"] == rider_sel) & (fdf["pay month"] == month_sel)]
        if not target.empty:
            render_payslip(target.iloc[0])
