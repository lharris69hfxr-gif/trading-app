import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="Simple Trading App", layout="wide")
st.title("📈 Simple Trading App")

ticker = st.text_input("Ticker", value="AAPL").upper().strip()
period = st.selectbox("Period", ["1mo","3mo","6mo","1y","2y","5y"], index=3)
interval = st.selectbox("Interval", ["1d","1wk","1mo"], index=0)

if ticker:
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.empty:
        st.warning("No data returned. Try a different ticker/period.")
    else:
        # prices
        last_close = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else last_close
        change = last_close - prev_close
        pct = (change / prev_close * 100) if prev_close else 0.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Last Close", f"${last_close:,.2f}")
        col2.metric("Change", f"${change:,.2f}", f"{pct:+.2f}%")
        col3.write(f"Bars: {len(df):,}")

        # SMAs
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()

        # Candlestick chart
        fig = go.Figure(data=[
            go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Candles"),
            go.Scatter(x=df.index, y=df["SMA20"], mode="lines", name="SMA 20"),
            go.Scatter(x=df.index, y=df["SMA50"], mode="lines", name="SMA 50"),
        ])
        fig.update_layout(xaxis_rangeslider_visible=False, height=520, margin=dict(l=20,r=20,t=20,b=20))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Data (tail)")
        st.dataframe(df.tail(10))
else:
    st.info("Enter a ticker (e.g., AAPL, TSLA).")
