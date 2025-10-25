import streamlit as st

st.title("📈 Simple Trading App")

prices = [101, 102, 103, 102, 101, 100, 99, 98]

st.write("### Price Data:", prices)

if prices[-1] > prices[-2]:
    st.success("📈 Buy signal triggered")
elif prices[-1] < prices[-2]:
    st.error("📉 Sell signal triggered")
else:
    st.info("⏸ Hold position")
