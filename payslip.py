import streamlit as st
import pandas as pd
from datetime import datetime

PAYSLIP_CSS = """
<style>
.payslip { max-width: 800px; margin: auto; font-family: 'Segoe UI', sans-serif;
           border: 2px solid #7c3aed; border-radius: 14px; padding: 28px;
           background: #fafafa; }
.payslip h1 { color: #7c3aed; margin: 0; }
.payslip .header { display: flex; justify-content: space-between;
                   border-bottom: 2px dashed #7c3aed; padding-bottom: 12px; }
.payslip table { width: 100%; border-collapse: collapse; margin-top: 16px; }
.payslip th, .payslip td { padding: 8px 12px; text-align: left; }
.payslip tr:nth-child(even) { background: #f3f0ff; }
.payslip .total { font-size: 1.3rem; font-weight: 700; color: #10b981;
                  text-align: right; margin-top: 16px; }
@media print { .no-print { display: none; } .payslip { border: none; } }
</style>
"""

def render_payslip(row: pd.Series):
    st.markdown(PAYSLIP_CSS, unsafe_allow_html=True)

    html = f"""
    <div class="payslip">
      <div class="header">
        <div><h1>🚴 COURIER PAY SLIP</h1>
             <p>Month: <b>{row.get('pay month', 'N/A')}</b></p></div>
        <div style="text-align:right">
             <p><b>Courier ID:</b> {row.get('courier ID', '')}</p>
             <p><b>Name:</b> {row.get('courier name', '')}</p>
             <p><b>Valid:</b> {'✅' if row.get('is valid', '') else '❌'}</p>
        </div>
      </div>

      <table>
        <tr><th>Description</th><th>Amount (AED)</th></tr>
        <tr><td>Delivered Orders</td><td>{row.get('delivered orders', 0):,.0f}</td></tr>
        <tr><td>Rider Earnings</td><td>{row.get('rider earnings', 0):,.2f}</td></tr>
        <tr><td>Company Expenses</td><td>{row.get('Company Expenses', 0):,.2f}</td></tr>
        <tr><td>Previous Balance</td><td>{row.get('Previous Balance', 0):,.2f}</td></tr>
        <tr><td>R.F Deduction</td><td>-{row.get('R.F Deduction', 0):,.2f}</td></tr>
        <tr><td>Advance Money</td><td>-{row.get('Advance Money', 0):,.2f}</td></tr>
        <tr><td>Other Deduction</td><td>-{row.get('Other Deduction', 0):,.2f}</td></tr>
        <tr><td>Leave Fine</td><td>-{row.get('Leave Fine', 0):,.2f}</td></tr>
        <tr><td>Parking</td><td>-{row.get('Parking', 0):,.2f}</td></tr>
        <tr><td>Bike Fine</td><td>-{row.get('Bike Fine', 0):,.2f}</td></tr>
        <tr><td>Salik Payment</td><td>-{row.get('Salik Payment', 0):,.2f}</td></tr>
      </table>

      <div class="total">
        Rider Payable Amount: AED {row.get('rider payable amount', 0):,.2f}
      </div>

      <p style="margin-top:24px; font-size:0.85rem; color:#666;">
        Generated on {datetime.now().strftime('%d %b %Y, %H:%M')} ·
        This is a computer-generated pay slip. No signature required.
      </p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if st.button("🖨️ Print / Save as PDF"):
        st.components.v1.html(
            "<script>window.print();</script>", height=0
        )
    st.markdown('</div>', unsafe_allow_html=True)