"""
Streamlit dashboard - production style fintech UI.
"""

import uuid

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_fetch import fetch_stock_data, fetch_fundamental_data, fetch_market_context, fetch_batch_stocks, fetch_latest_price
from decision_engine import evaluate_stock
from risk_management import generate_execution_plan, calculate_atr
from paper_trading import PaperTradingPortfolio
from trade_logging import (
    save_log,
    load_logs,
    filter_logs,
    sort_logs,
    soft_delete_logs,
    soft_delete_all_logs,
)

# PAGE CONFIG
st.set_page_config(
    page_title="Stock Analysis Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# THEME + DESIGN TOKENS
st.markdown(
    """
<style>
    :root {
        --bg: #0F131A;
        --card: #161B22;
        --primary: #2563EB;
        --success: #16A34A;
        --danger: #DC2626;
        --text: #E5E7EB;
        --muted: #9CA3AF;
        --border: #2A3340;
        --metric-bg: #1C2330;
    }

    .stApp {
        background-color: var(--bg);
        color: var(--text);
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 1.6rem;
    }

    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.05rem 1.05rem 1rem 1.05rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.08);
    }

    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 0.7rem;
    }

    .decision-card-buy {
        background: linear-gradient(180deg, rgba(22,163,74,0.12) 0%, var(--card) 100%);
        border-left: 6px solid var(--success);
    }

    .decision-card-sell {
        background: linear-gradient(180deg, rgba(220,38,38,0.12) 0%, var(--card) 100%);
        border-left: 6px solid var(--danger);
    }

    .decision-text {
        font-size: 2.7rem;
        font-weight: 900;
        margin: 0;
    }

    .decision-meta {
        font-size: 1.18rem;
        font-weight: 600;
        color: var(--primary);
        margin-top: 0.35rem;
    }

    .decision-score {
        color: var(--muted);
        margin-top: 0.15rem;
        font-size: 1.05rem;
    }
    .decision-summary {
        margin-top: 0.65rem;
        color: var(--text);
        font-size: 0.96rem;
        line-height: 1.45;
        background: var(--metric-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.6rem 0.7rem;
    }

    .list-header {
        margin-top: 0.8rem;
        margin-bottom: 0.3rem;
        font-weight: 700;
        color: var(--text);
        font-size: 0.9rem;
    }

    .strength {
        color: var(--success);
        font-size: 0.9rem;
        margin: 0.2rem 0;
    }

    .risk {
        color: var(--danger);
        font-size: 0.9rem;
        margin: 0.2rem 0;
    }

    .metric-box {
        background: var(--metric-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.65rem 0.8rem;
        margin-bottom: 0.55rem;
    }
    .metric-box-tight {
        background: var(--metric-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.55rem 0.7rem;
        margin-bottom: 0.45rem;
    }

    .metric-label {
        font-size: 0.76rem;
        color: var(--muted);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.35px;
    }

    .metric-value {
        margin-top: 0.15rem;
        font-size: 1.18rem;
        font-weight: 800;
        color: var(--text);
    }

    h2, h3, h4, label, p, span {
        color: var(--text);
    }

    .stCaption {
        color: var(--muted) !important;
    }
    .section-gap {
        margin-top: 8px;
        margin-bottom: 8px;
    }
    .rr-badge {
        display: inline-block;
        margin-top: 0.4rem;
        padding: 0.2rem 0.5rem;
        border-radius: 8px;
        border: 1px solid var(--border);
        font-size: 0.82rem;
        color: var(--muted);
    }
</style>
""",
    unsafe_allow_html=True,
)

# SESSION STATE
if "portfolio" not in st.session_state:
    st.session_state.portfolio = PaperTradingPortfolio(initial_capital=100000)
if "analysis_session_id" not in st.session_state:
    st.session_state.analysis_session_id = str(uuid.uuid4())

def _safe_number(value, fallback=0.0):
    """Convert value to numeric with NaN fallback."""
    try:
        numeric = float(value)
        if numeric != numeric:  # NaN check
            numeric = float(fallback)
    except (TypeError, ValueError):
        numeric = float(fallback)
    return round(numeric, 2)

def _fmt_inr(value):
    return f"₹{_safe_number(value):,.2f}"


def _recommended_entry_price(analysis, execution, current_price, price_data):
    """
    Compute recommended entry separately from live market price.
    Uses existing signals only: RSI, support/resistance, trend, ATR.
    """
    indicators = analysis.get("indicators", {}) if isinstance(analysis, dict) else {}
    rsi_value = _safe_number(indicators.get("rsi"), 50.0)
    ma_50 = _safe_number(indicators.get("ma_50"), current_price)
    ma_200 = _safe_number(indicators.get("ma_200"), current_price)

    support = _safe_number(execution.get("support_level"), current_price * 0.97)
    resistance = _safe_number(execution.get("resistance_level"), current_price * 1.03)
    atr_value = _safe_number(calculate_atr(price_data), max(current_price * 0.01, 0.01))
    atr_value = max(atr_value, max(current_price * 0.005, 0.01))

    distance_to_support = ((current_price / support) - 1) * 100 if support > 0 else 0.0
    near_ideal_zone = distance_to_support <= 1.0
    uptrend = current_price >= ma_50 >= ma_200
    breakout_setup = uptrend and current_price >= (resistance * 0.995)
    support_within_5pct = distance_to_support <= 5.0

    # Case A: breakout setup -> near current price
    if near_ideal_zone:
        recommended = current_price
    elif breakout_setup:
        recommended = min(current_price, current_price - (0.2 * atr_value))
    # Case B/C: pullback setup using support only if not too deep
    elif support_within_5pct:
        recommended = support
    else:
        # Case C: deep support too far below -> shallow pullback entry
        recommended = current_price * 0.98

    # Case D: RSI overbought override
    if rsi_value > 65:
        recommended = min(recommended, current_price * 0.97)

    if current_price > 0 and abs((recommended - current_price) / current_price) <= 0.004:
        recommended = current_price

    return _safe_number(recommended, current_price)


def _validated_execution_levels(analysis, execution, current_price, entry_price, price_data):
    """
    Enforce long-trade structure: stop_loss < entry < target_min < target_max.
    """
    atr_value = _safe_number(calculate_atr(price_data), max(entry_price * 0.01, 0.01))
    atr_value = max(atr_value, max(entry_price * 0.005, 0.01))

    stop_loss = _safe_number(
        analysis.get("stop_loss", execution.get("stop_loss")),
        entry_price * 0.95,
    )
    target_min = _safe_number(
        analysis.get("target_min", execution.get("target_1")),
        entry_price * 1.05,
    )
    target_max = _safe_number(
        analysis.get("target_max", execution.get("target_2")),
        entry_price * 1.10,
    )

    # Stop-loss validation: always below entry.
    if stop_loss >= entry_price:
        stop_loss = max(entry_price - (2 * atr_value), entry_price * 0.95)
    if stop_loss >= entry_price:
        stop_loss = entry_price * 0.95

    # Target validation: always above entry and ordered.
    if target_min <= entry_price:
        target_min = max(entry_price * 1.03, entry_price + atr_value)
    if target_max <= target_min:
        target_max = max(target_min * 1.03, entry_price * 1.07)
    if target_max <= entry_price:
        target_max = entry_price * 1.08

    # Final hard validation layer.
    if not (stop_loss < entry_price < target_min < target_max):
        stop_loss = entry_price * 0.95
        target_min = entry_price * 1.05
        target_max = entry_price * 1.10

    risk = max(entry_price - stop_loss, 0.01)
    reward = max(target_min - entry_price, 0.0)
    risk_reward = _safe_number(reward / risk, 0.0)

    return {
        "current_price": _safe_number(current_price, 0.0),
        "recommended_entry_price": _safe_number(entry_price, current_price),
        "stop_loss": _safe_number(stop_loss, entry_price * 0.95),
        "target_min": _safe_number(target_min, entry_price * 1.05),
        "target_max": _safe_number(target_max, entry_price * 1.10),
        "risk_reward": risk_reward,
    }


@st.cache_data(show_spinner=False, ttl=15)
def _load_logs_cached():
    """Cached log reader to avoid repeated file reads on UI interactions."""
    return load_logs()

# HEADER
st.markdown(
    """
    <div style="padding: 6px 0 10px 0; max-width: 100%; overflow-wrap: anywhere;">
        <h1 style="
            font-size: 34px;
            font-weight: 700;
            color: #E5E7EB;
            margin-bottom: 5px;
            margin-top: 0;
            line-height: 1.2;
        ">
            Caramel AI
        </h1>
        <p style="
            font-size: 16px;
            color: #9CA3AF;
            margin-top: 0;
            margin-bottom: 0;
        ">
            AI-powered decision support for swing trading
        </p>
    </div>
""",
    unsafe_allow_html=True,
)

# TOP INPUT SECTION
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Input Panel</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1], vertical_alignment="bottom")
    with c1:
        symbol_input = st.text_input("Stock Symbol", placeholder="e.g., RELIANCE.NS", key="single_symbol")
    with c2:
        multi_input = st.text_input("Watchlist", placeholder="e.g., TCS.NS, INFY.NS, HDFC.NS", key="multi_symbols")
    with c3:
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key="csv_upload")
    with c4:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        analyze_button = st.button("Analyze", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ANALYSIS FLOW (UNCHANGED)
if analyze_button:
    symbols_to_analyze = []

    if symbol_input:
        symbols_to_analyze = [symbol_input.strip()]
    elif multi_input:
        symbols_to_analyze = [s.strip() for s in multi_input.split(",")]
    elif uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "symbol" in df.columns:
            symbols_to_analyze = df["symbol"].tolist()

    if symbols_to_analyze:
        market_context = fetch_market_context()

        for symbol in symbols_to_analyze:
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader(symbol)
            st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

            with st.spinner(f"Fetching data for {symbol}..."):
                price_data = fetch_stock_data(symbol)
                fundamental_data = fetch_fundamental_data(symbol)

            if price_data is None:
                st.error(f"Could not fetch data for {symbol}")
                continue

            with st.spinner("Analyzing..."):
                analysis = evaluate_stock(price_data, fundamental_data, market_context)
                execution = generate_execution_plan(analysis, price_data)
                latest_price = fetch_latest_price(symbol)
                current_price = _safe_number(latest_price, _safe_number(analysis.get("price_now"), 0.0))
                analysis["current_price"] = current_price
                analysis["price_now"] = current_price

                recommended_entry = _recommended_entry_price(
                    analysis=analysis,
                    execution=execution,
                    current_price=current_price,
                    price_data=price_data,
                )
                levels = _validated_execution_levels(
                    analysis=analysis,
                    execution=execution,
                    current_price=current_price,
                    entry_price=recommended_entry,
                    price_data=price_data,
                )
                analysis["recommended_entry_price"] = levels["recommended_entry_price"]
                analysis["entry_price"] = levels["recommended_entry_price"]
                analysis["stop_loss"] = levels["stop_loss"]
                analysis["target_min"] = levels["target_min"]
                analysis["target_max"] = levels["target_max"]
                analysis["risk_reward"] = levels["risk_reward"]

            save_log(
                {
                    "session_id": st.session_state.analysis_session_id,
                    "symbol": symbol,
                    "decision": analysis.get("decision"),
                    "total_score": analysis.get("base_score"),
                    "technical_score": analysis.get("breakdown", {}).get("technical", {}).get("total", 0),
                    "fundamental_score": analysis.get("breakdown", {}).get("fundamental", {}).get("total", 0),
                    "supporting_score": analysis.get("breakdown", {}).get("supporting", {}).get("total", 0),
                    "confidence": analysis.get("confidence"),
                    "current_price": analysis.get("current_price", analysis.get("price_now")),
                    "entry_price": analysis.get("recommended_entry_price", analysis.get("entry_price")),
                    "stop_loss": analysis.get("stop_loss", execution.get("stop_loss")),
                    "target_min": analysis.get("target_min", execution.get("target_1")),
                    "target_max": analysis.get("target_max", execution.get("target_2")),
                    "risk_reward": analysis.get("risk_reward"),
                    "position_size": analysis.get("position_size"),
                }
            )
            _load_logs_cached.clear()

            # MAIN DASHBOARD GRID
            left_col, right_col = st.columns([3, 1], gap="large")

            # LEFT SIDE
            with left_col:
                decision_class = "decision-card-buy" if "BUY" in analysis["decision"] else "decision-card-sell"
                decision_color = "#16A34A" if "BUY" in analysis["decision"] else "#DC2626"
                score_label = analysis.get("score_label", "Unclassified")
                decision_summary = analysis.get("decision_summary", "Decision context unavailable.")
                rr_value = _safe_number(analysis.get("risk_reward"), 0.0)
                if rr_value >= 2:
                    rr_label = "Good Setup"
                elif rr_value >= 1:
                    rr_label = "Neutral"
                else:
                    rr_label = "Avoid"

                st.markdown(f"<div class='card {decision_class}'>", unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <p class='decision-text' style='color:{decision_color};'>{analysis['decision']}</p>
                    <p class='decision-meta'>Confidence: {analysis['confidence']}%</p>
                    <p class='decision-score'>Score: {analysis['base_score']}/100 → {score_label}</p>
                    <p class='decision-score'>RR: {rr_value:.2f} → {rr_label}</p>
                    <p class='decision-summary'>{decision_summary}</p>
                    <p class='list-header'>Key Strengths</p>
                    {''.join([f"<p class='strength'>• {s}</p>" for s in analysis['reasoning']['strengths'][:3]])}
                    <p class='list-header'>Key Risks</p>
                    {''.join([f"<p class='risk'>• {c}</p>" for c in analysis['reasoning']['concerns'][:2]])}
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='card'>", unsafe_allow_html=True)
                chart_head, chart_toggle = st.columns([4, 2], vertical_alignment="center")
                with chart_head:
                    st.markdown("<div class='section-title'>Price Chart & Indicators</div>", unsafe_allow_html=True)
                with chart_toggle:
                    tg1, tg2 = st.columns(2)
                    with tg1:
                        show_rsi = st.checkbox("RSI", value=True, key=f"show_rsi_{symbol}")
                    with tg2:
                        show_macd = st.checkbox("MACD", value=True, key=f"show_macd_{symbol}")

                rows = 1 + int(show_rsi) + int(show_macd)
                if rows == 1:
                    row_heights = [1.0]
                    subplot_titles = ("Price",)
                elif rows == 2:
                    row_heights = [0.68, 0.32]
                    subplot_titles = ("Price", "RSI" if show_rsi else "MACD")
                else:
                    row_heights = [0.56, 0.22, 0.22]
                    subplot_titles = ("Price", "RSI", "MACD")

                fig = make_subplots(
                    rows=rows,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=row_heights,
                    subplot_titles=subplot_titles,
                )

                fig.add_trace(
                    go.Candlestick(
                        x=price_data.index,
                        open=price_data["Open"],
                        high=price_data["High"],
                        low=price_data["Low"],
                        close=price_data["Close"],
                        name="Price",
                    ),
                    row=1,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=price_data.index,
                        y=analysis["indicators"]["ma_50_series"],
                        name="50 MA",
                        line=dict(color="#2563EB", width=1.7),
                    ),
                    row=1,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=price_data.index,
                        y=analysis["indicators"]["ma_200_series"],
                        name="200 MA",
                        line=dict(color="#60A5FA", width=1.7),
                    ),
                    row=1,
                    col=1,
                )

                next_row = 2
                if show_rsi:
                    fig.add_trace(
                        go.Scatter(
                            x=price_data.index,
                            y=analysis["indicators"]["rsi_series"],
                            name="RSI",
                            line=dict(color="#7C3AED", width=2),
                        ),
                        row=next_row,
                        col=1,
                    )
                    fig.add_hline(y=70, line_dash="dash", line_color="#DC2626", row=next_row, col=1, opacity=0.55)
                    fig.add_hline(y=30, line_dash="dash", line_color="#16A34A", row=next_row, col=1, opacity=0.55)
                    next_row += 1

                if show_macd:
                    fig.add_trace(
                        go.Scatter(
                            x=price_data.index,
                            y=analysis["indicators"]["macd_series"],
                            name="MACD",
                            line=dict(color="#2563EB", width=1.9),
                        ),
                        row=next_row,
                        col=1,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=price_data.index,
                            y=analysis["indicators"]["signal_series"],
                            name="Signal",
                            line=dict(color="#F59E0B", width=1.9),
                        ),
                        row=next_row,
                        col=1,
                    )

                chart_height = 560 if rows == 1 else 650 if rows == 2 else 730
                fig.update_layout(
                    height=chart_height,
                    showlegend=True,
                    xaxis_rangeslider_visible=False,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#0F172A"),
                    margin=dict(l=12, r=12, t=30, b=8),
                )
                fig.update_xaxes(showgrid=True, gridcolor="#E2E8F0")
                fig.update_yaxes(showgrid=True, gridcolor="#E2E8F0")
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # RIGHT SIDE
            with right_col:
                price_now = _safe_number(
                    analysis.get("current_price", analysis.get("price_now")),
                    _safe_number(analysis["indicators"].get("price"), 0.0),
                )
                entry_price = _safe_number(analysis.get("recommended_entry_price", analysis.get("entry_price")), price_now)
                stop_loss = _safe_number(analysis.get("stop_loss"), entry_price * 0.95)
                target_min = _safe_number(analysis.get("target_min"), entry_price * 1.05)
                target_max = _safe_number(analysis.get("target_max"), entry_price * 1.10)
                risk_reward = _safe_number(analysis.get("risk_reward"), 0.0)
                if risk_reward >= 2:
                    rr_label = "Good Setup"
                elif risk_reward >= 1:
                    rr_label = "Neutral"
                else:
                    rr_label = "Avoid"

                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("<div class='section-title'>Execution Panel</div>", unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <div class='metric-box-tight'>
                        <div class='metric-label'>Price Now</div>
                        <div class='metric-value'>{_fmt_inr(price_now)}</div>
                    </div>
                    <div class='metric-box-tight'>
                        <div class='metric-label'>Recommended Entry</div>
                        <div class='metric-value'>{_fmt_inr(entry_price)}</div>
                    </div>
                    <div class='metric-box-tight'>
                        <div class='metric-label'>Stop-Loss</div>
                        <div class='metric-value' style='color:#DC2626;'>{_fmt_inr(stop_loss)}</div>
                    </div>
                    <div class='metric-box-tight'>
                        <div class='metric-label'>Target Min</div>
                        <div class='metric-value' style='color:#16A34A;'>{_fmt_inr(target_min)}</div>
                    </div>
                    <div class='metric-box-tight'>
                        <div class='metric-label'>Target Max</div>
                        <div class='metric-value' style='color:#16A34A;'>{_fmt_inr(target_max)}</div>
                    </div>
                    <div class='metric-box-tight'>
                        <div class='metric-label'>Risk-Reward</div>
                        <div class='metric-value' style='font-size:1rem;'>{risk_reward:.2f} → {rr_label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("<div class='section-title'>Score Breakdown</div>", unsafe_allow_html=True)
                tech_score = analysis["breakdown"]["technical"]["total"]
                fund_score = analysis["breakdown"]["fundamental"]["total"]
                supp_score = analysis["breakdown"]["supporting"]["total"]
                st.progress(float(tech_score) / 60.0, text=f"Technical: {tech_score}/60")
                st.progress(float(fund_score) / 25.0, text=f"Fundamental: {fund_score}/25")
                st.progress(float(supp_score) / 15.0, text=f"Supporting: {supp_score}/15")
                st.markdown("</div>", unsafe_allow_html=True)

# STORE LAST ANALYSIS
if analyze_button and "analysis" in locals():
    st.session_state.last_analysis = analysis
    st.session_state.last_execution = execution

st.markdown("<br>", unsafe_allow_html=True)

# PAPER TRADING (FULL WIDTH)
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Paper Trading</div>", unsafe_allow_html=True)

    portfolio_summary = st.session_state.portfolio.get_portfolio_summary()
    p1, p2, p3 = st.columns(3)
    with p1:
        st.metric("Portfolio Value", f"₹{portfolio_summary['current_portfolio_value']:,.0f}")
    with p2:
        st.metric("Total Return", f"{portfolio_summary['total_return_percent']}%")
    with p3:
        st.metric("Open Positions", portfolio_summary["open_positions"])

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    st.markdown("#### Place Paper Trade")
    trade_symbol = st.text_input("Symbol to Trade", key="trade_symbol", placeholder="e.g., RELIANCE.NS")
    investment_amount = st.number_input(
        "Investment Amount (₹)",
        min_value=0.0,
        value=10000.0,
        step=500.0,
        key="investment_amount",
        help="Amount allocated for this simulated position.",
    )
    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    execute_trade_btn = st.button("Simulate Trade", type="primary", use_container_width=True)
    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    if execute_trade_btn:
        if trade_symbol and hasattr(st.session_state, "last_analysis"):
            latest_analysis = st.session_state.last_analysis
            price_now = _safe_number(latest_analysis.get("current_price", latest_analysis.get("price_now")), 0.0)
            entry_price = _safe_number(
                latest_analysis.get("recommended_entry_price", latest_analysis.get("entry_price")),
                price_now,
            )
            target_min = _safe_number(latest_analysis.get("target_min"), entry_price * 1.05)
            target_max = _safe_number(latest_analysis.get("target_max"), entry_price * 1.10)
            stop_loss = _safe_number(
                latest_analysis.get("stop_loss"),
                st.session_state.last_execution.get("stop_loss", entry_price * 0.95),
            )

            trade_metrics = st.session_state.portfolio.calculate_trade_metrics(
                investment_amount=investment_amount,
                price_now=price_now,
                entry_price=entry_price,
                target_min=target_min,
                target_max=target_max,
            )

            if not trade_metrics:
                st.error("Invalid price data. Please run analysis again before placing a trade.")
            else:
                available_capital = st.session_state.portfolio.available_capital
                if available_capital > 0:
                    position_size_percent = max(0.0, min(100.0, (investment_amount / available_capital) * 100.0))
                    result = st.session_state.portfolio.execute_trade(
                        trade_symbol,
                        price_now,
                        position_size_percent,
                        stop_loss,
                    )
                    if result["status"] == "success":
                        st.success(
                            f"Executed trade: {trade_metrics['quantity']} shares @ {_fmt_inr(trade_metrics['price_now'])}"
                        )
                        t1, t2, t3 = st.columns(3)
                        with t1:
                            st.metric("Investment", _fmt_inr(trade_metrics["investment_amount"]))
                        with t2:
                            st.metric("Price Now", _fmt_inr(trade_metrics["price_now"]))
                        with t3:
                            st.metric("Quantity Bought", trade_metrics["quantity"])

                        t4, t5, t6 = st.columns(3)
                        with t4:
                            st.metric("Total Invested", _fmt_inr(trade_metrics["total_invested"]))
                        with t5:
                            st.metric("Current Value", _fmt_inr(trade_metrics["current_value"]))
                        with t6:
                            st.metric("Profit / Loss", _fmt_inr(trade_metrics["profit"]))

                        t7, t8, t9 = st.columns(3)
                        with t7:
                            st.metric("Profit / Loss %", f"{trade_metrics['profit_percent']:.2f}%")
                        with t8:
                            st.metric("Target Min Profit", _fmt_inr(trade_metrics["target_min_profit"]))
                        with t9:
                            st.metric(
                                "Target Profit Range",
                                f"{_fmt_inr(trade_metrics['target_min_profit'])} to {_fmt_inr(trade_metrics['target_max_profit'])}",
                            )
                    else:
                        st.error(result.get("reason", "Trade failed"))
                else:
                    st.error("No available capital to execute trade.")
        else:
            st.warning("Run analysis first, then place a paper trade.")

    st.markdown("</div>", unsafe_allow_html=True)

# LOGS / HISTORY (FULL WIDTH)
_LOG_DISPLAY_COLS = [
    "symbol",
    "decision",
    "total_score",
    "technical_score",
    "fundamental_score",
    "supporting_score",
    "current_price",
    "target_min",
    "stop_loss",
    "confidence",
    "timestamp",
]


def _render_log_page(chunk_df, page_key_prefix):
    """Paginated dataframe with stable Streamlit widget keys."""
    if chunk_df is None or chunk_df.empty:
        st.info("No rows match the current filters.")
        return
    page_size = st.selectbox(
        "Rows per page",
        options=[25, 50, 100, 200],
        index=0,
        key=f"{page_key_prefix}_page_size",
    )
    n = len(chunk_df)
    total_pages = max(1, (n + page_size - 1) // page_size)
    page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key=f"{page_key_prefix}_page_num",
    )
    start = (int(page) - 1) * int(page_size)
    slice_df = chunk_df.iloc[start : start + int(page_size)]
    show = slice_df.copy()
    if "timestamp" in show.columns:
        show["timestamp"] = show["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Showing {start + 1}–{min(start + len(slice_df), n)} of {n} rows")
    st.dataframe(show[_LOG_DISPLAY_COLS], use_container_width=True, hide_index=True)


with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Logs / Analysis History</div>", unsafe_allow_html=True)
    st.caption(
        f"**Current session ID:** `{st.session_state.analysis_session_id}` — new analyses are tagged with this ID."
    )

    history = _load_logs_cached()
    if history.empty:
        st.info("No analysis history yet.")
    else:
        log_search = st.text_input(
            "Search",
            placeholder="Symbol, decision, or log ID…",
            key="log_search_text",
        )

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            selected_decision = st.selectbox(
                "Decision",
                options=["All", "BUY", "HOLD", "NO BUY"],
                index=0,
                key="log_decision_filter",
            )
        with f2:
            total_score_range = st.slider(
                "Total Score",
                min_value=0.0,
                max_value=100.0,
                value=(0.0, 100.0),
                step=1.0,
                key="log_score_range",
            )
        with f3:
            confidence_range = st.slider(
                "Confidence Range",
                min_value=0.0,
                max_value=100.0,
                value=(0.0, 100.0),
                step=1.0,
                key="log_conf_range",
            )
        with f4:
            symbol_filter = st.text_input("Symbol", placeholder="e.g., RELIANCE.NS", key="log_symbol_filter")

        b1, b2, b3 = st.columns(3)
        with b1:
            technical_range = st.slider(
                "Technical Score",
                min_value=0.0,
                max_value=60.0,
                value=(0.0, 60.0),
                step=1.0,
                key="log_technical_range",
            )
        with b2:
            fundamental_range = st.slider(
                "Fundamental Score",
                min_value=0.0,
                max_value=25.0,
                value=(0.0, 25.0),
                step=1.0,
                key="log_fundamental_range",
            )
        with b3:
            supporting_range = st.slider(
                "Supporting Score",
                min_value=0.0,
                max_value=15.0,
                value=(0.0, 15.0),
                step=1.0,
                key="log_supporting_range",
            )

        e1, e2, e3 = st.columns(3)
        with e1:
            current_price_range = st.slider(
                "Current Price",
                min_value=0.0,
                max_value=10000.0,
                value=(0.0, 10000.0),
                step=1.0,
                key="log_current_price_range",
            )
        with e2:
            target_price_range = st.slider(
                "Target Price (Min)",
                min_value=0.0,
                max_value=10000.0,
                value=(0.0, 10000.0),
                step=1.0,
                key="log_target_price_range",
            )
        with e3:
            stop_loss_range = st.slider(
                "Stop Loss",
                min_value=0.0,
                max_value=10000.0,
                value=(0.0, 10000.0),
                step=1.0,
                key="log_stop_loss_range",
            )

        s1, s2 = st.columns(2)
        with s1:
            sort_by = st.selectbox(
                "Sort By",
                options=[
                    "total_score",
                    "confidence",
                    "technical_score",
                    "fundamental_score",
                    "supporting_score",
                    "current_price",
                    "target_min",
                    "timestamp",
                ],
                index=0,
                key="log_sort_by",
            )
        with s2:
            ascending = st.checkbox("Ascending", value=False, key="log_sort_asc")

        filtered_all = filter_logs(
            history,
            decision=selected_decision,
            min_total_score=total_score_range[0],
            max_total_score=total_score_range[1],
            min_confidence=confidence_range[0],
            max_confidence=confidence_range[1],
            symbol=symbol_filter,
            search_text=log_search,
            exclude_deleted=True,
            min_technical_score=technical_range[0],
            max_technical_score=technical_range[1],
            min_fundamental_score=fundamental_range[0],
            max_fundamental_score=fundamental_range[1],
            min_supporting_score=supporting_range[0],
            max_supporting_score=supporting_range[1],
            min_current_price=current_price_range[0],
            max_current_price=current_price_range[1],
            min_target_price=target_price_range[0],
            max_target_price=target_price_range[1],
            min_stop_loss=stop_loss_range[0],
            max_stop_loss=stop_loss_range[1],
        )
        filtered_all = sort_logs(filtered_all, by=sort_by, ascending=ascending)

        df_overall = filtered_all
        df_session = filtered_all[
            filtered_all["session_id"].astype(str) == str(st.session_state.analysis_session_id)
        ].copy()

        tab_overall, tab_session = st.tabs(["Overall History", "Current Session"])

        with tab_overall:
            st.markdown("All entries from **logs.csv** (all sessions), excluding soft-deleted rows.")
            _render_log_page(df_overall, "log_ov")

        with tab_session:
            st.markdown("Entries recorded **in this app session** only.")
            _render_log_page(df_session, "log_cs")

        st.markdown("---")
        st.markdown("#### Delete history")
        st.caption(
            "Recommended: **soft delete** — rows stay in the CSV with `is_deleted=1` for audit/recovery; they are hidden here."
        )

        del_scope = st.radio(
            "Select rows from",
            ["Overall History (filtered)", "Current Session (filtered)"],
            horizontal=True,
            key="log_delete_scope",
        )
        delete_source = df_overall if del_scope.startswith("Overall") else df_session
        id_options = delete_source["log_id"].astype(str).tolist() if not delete_source.empty else []

        selected_ids = st.multiselect(
            "Log IDs to soft-delete",
            options=id_options,
            key="log_ids_to_delete",
            help="List reflects the same filters as above; choose Overall or Current Session.",
        )
        c_del1, c_del2 = st.columns(2)
        with c_del1:
            if st.button("Soft-delete selected", type="primary", key="log_soft_delete_selected"):
                if not selected_ids:
                    st.warning("Select at least one log ID.")
                elif soft_delete_logs(selected_ids):
                    _load_logs_cached.clear()
                    st.success(f"Soft-deleted {len(selected_ids)} row(s).")
                    st.rerun()
                else:
                    st.error("Could not update logs file.")
        with c_del2:
            with st.expander("Delete ALL history (danger)", expanded=False):
                st.warning("This soft-deletes **every** row in logs.csv (hidden from UI).")
                confirm_txt = st.text_input(
                    'Type exactly: DELETE ALL',
                    key="log_delete_all_confirm",
                )
                if st.button("Soft-delete ALL rows", key="log_soft_delete_all"):
                    if confirm_txt == "DELETE ALL":
                        if soft_delete_all_logs():
                            _load_logs_cached.clear()
                            st.success("All log rows soft-deleted.")
                            st.rerun()
                        else:
                            st.error("Could not update logs file.")
                    else:
                        st.error('Confirmation must match exactly: DELETE ALL')

    st.markdown("</div>", unsafe_allow_html=True)