import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Larry's Paper Trader + AI Assist", page_icon="🤖")

# ---------- STATE ----------
if "cash" not in st.session_state: st.session_state.cash = 10000.0
if "positions" not in st.session_state: st.session_state.positions = {}
if "history" not in st.session_state: st.session_state.history = []
if "last_price" not in st.session_state: st.session_state.last_price = {}

st.title("Larry's Paper Trader 🤖📈")

# ---------- Helpers ----------
def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / (loss.replace(0, np.nan))
    return 100 - (100 / (1 + rs))

def ai_signal(df):
    """Return ('BUY'|'SELL'|'HOLD', confidence 0-100, reason str)."""
    close = df["Close"]
    ma_fast = close.rolling(10).mean()
    ma_slow = close.rolling(30).mean()
    r = rsi(close, 14)

    # defaults
    sig, conf, why = "HOLD", 55, "No strong edge."

    # MA crossover logic
    cross_up = (ma_fast.iloc[-2] < ma_slow.iloc[-2]) and (ma_fast.iloc[-1] > ma_slow.iloc[-1])
    cross_dn = (ma_fast.iloc[-2] > ma_slow.iloc[-2]) and (ma_fast.iloc[-1] < ma_slow.iloc[-1])

    # RSI zones
    r_last = float(r.iloc[-1])
    overbought = r_last > 60
    oversold   = r_last < 40

    if cross_up and oversold:
        sig, conf, why = "BUY", 78, f"Fast MA crossed UP + RSI {r_last:.1f} (recovering from weak zone)."
    elif cross_up:
        sig, conf, why = "BUY", 68, f"Fast MA crossed UP; trend improving. RSI {r_last:.1f}."
    elif cross_dn and overbought:
        sig, conf, why = "SELL", 78, f"Fast MA crossed DOWN + RSI {r_last:.1f} (cooling from hot zone)."
    elif cross_dn:
        sig, conf, why = "SELL", 68, f"Fast MA crossed DOWN; trend weakening. RSI {r_last:.1f}."
    else:
        if oversold:
            sig, conf, why = "HOLD", 60, f"RSI {r_last:.1f} (cheap but no confirmation)."
        elif overbought:
            sig, conf, why = "HOLD", 60, f"RSI {r_last:.1f} (rich but no confirmation)."

    return sig, conf, why, r_last

# ---------- Inputs ----------
colA, colB = st.columns([2,1])
with colA:
    ticker = st.text_input("Ticker (e.g., AAPL, TSLA, SPY)", value="AAPL").upper().strip()
with colB:
    period = st.selectbox("Period", ["1mo","3mo","6mo","1y","2y"], index=2)

if st.button("Fetch / Refresh"):
    df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False)
    if df.empty:
        st.error("No data for that ticker.")
    else:
        st.session_state.df = df
        st.session_state.last_price[ticker] = float(df["Close"].iloc[-1])

# Show chart + AI suggestion
df = st.session_state.get("df")
if df is not None and not df.empty:
    st.line_chart(df["Close"])
    last = st.session_state.last_price[ticker]
    sig, conf, why, r_last = ai_signal(df)
    st.metric("Last Price", f"${last:.2f}")
    st.subheader("🤖 AI Suggestion")
    st.write(f"**{sig}** · confidence **{conf}%**")
    st.caption(why + f" · RSI={r_last:.1f}")

# ---------- Trading ----------
st.subheader("Trade")
qty = st.number_input("Quantity", min_value=1, value=1, step=1)
price = st.session_state.last_price.get(ticker)

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("✅ Buy"):
        if price is None: st.warning("Fetch prices first.")
        else:
            cost = qty * price
            if st.session_state.cash >= cost:
                pos = st.session_state.positions.get(ticker, {"shares":0, "avg":0.0})
                new_shares = pos["shares"] + qty
                new_avg = (pos["avg"]*pos["shares"] + cost) / new_shares
                st.session_state.positions[ticker] = {"shares": new_shares, "avg": new_avg}
                st.session_state.cash -= cost
                st.session_state.history.append({"side":"BUY","ticker":ticker,"qty":qty,"price":price})
                st.success(f"Bought {qty} {ticker} @ ${price:.2f}")
            else:
                st.error("Not enough cash.")
with c2:
    if st.button("🟥 Sell"):
        if price is None: st.warning("Fetch prices first.")
        else:
            pos = st.session_state.positions.get(ticker)
            if not pos or pos["shares"] < qty:
                st.error("Not enough shares.")
            else:
                proceeds = qty * price
                pos["shares"] -= qty
                if pos["shares"] == 0: del st.session_state.positions[ticker]
                else: st.session_state.positions[ticker] = pos
                st.session_state.cash += proceeds
                st.session_state.history.append({"side":"SELL","ticker":ticker,"qty":qty,"price":price})
                st.success(f"Sold {qty} {ticker} @ ${price:.2f}")
with c3:
    # one-tap follow the AI
    if st.button("🤖 Follow AI"):
        if df is None: st.warning("Fetch prices first.")
        else:
            sig, conf, _, _ = ai_signal(df)
            if sig == "BUY":
                st.session_state.history.append({"side":"AI_BUY","ticker":ticker,"qty":qty,"price":price})
                st.experimental_rerun()  # triggers buttons re-run; user can hit Buy
            elif sig == "SELL":
                st.session_state.history.append({"side":"AI_SELL","ticker":ticker,"qty":qty,"price":price})
                st.experimental_rerun()
with c4:
    if st.button("↩️ Reset"):
        st.session_state.cash = 10000.0
        st.session_state.positions = {}
        st.session_state.history = []
        st.session_state.last_price = {}
        st.session_state.pop("df", None)
        st.success("Reset complete.")

# ---------- Portfolio ----------
st.subheader("Portfolio")
rows = []
total_positions = 0.0
for tkr, pos in st.session_state.positions.items():
    lp = st.session_state.last_price.get(tkr)
    if lp is None:
        try:
            lp = float(yf.Ticker(tkr).history(period="1d")["Close"].iloc[-1])
            st.session_state.last_price[tkr] = lp
        except Exception:
            lp = pos["avg"]
    mkt = pos["shares"] * lp
    pnl = (lp - pos["avg"]) * pos["shares"]
    total_positions += mkt
    rows.append([tkr, pos["shares"], f"${pos['avg']:.2f}", f"${lp:.2f}", f"${pnl:.2f}"])
pf = pd.DataFrame(rows, columns=["Ticker","Shares","Avg Price","Last Price","P&L"])
st.write(pf if not pf.empty else "No positions yet.")

net_worth = st.session_state.cash + total_positions
st.metric("Cash", f"${st.session_state.cash:,.2f}")
st.metric("Net Worth", f"${net_worth:,.2f}")

# ---------- History ----------
st.subheader("History")
st.write(pd.DataFrame(st.session_state.history) if st.session_state.history else "No trades yet.")
st.caption("Educational paper trading. Not financial advice.")
