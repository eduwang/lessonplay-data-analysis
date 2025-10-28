import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="시나리오별 전체 학생 변화 추이", layout="wide")
st.title("📊 시나리오별 전체 학생 변화 추이 (모든 학생 포함)")

DATA_PATH = "data/summary.csv"

if not os.path.exists(DATA_PATH):
    st.warning("⚠️ summary.csv 파일이 없습니다. 먼저 데이터 정리 페이지에서 생성하세요.")
else:
    df = pd.read_csv(DATA_PATH)

    # ✅ 입력 수가 0인 데이터 제외
    df = df[df["입력 수"] > 0]

    # 날짜 변환 및 정렬
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.sort_values(["시나리오", "사용자", "날짜", "회차"])

    # 시나리오 목록
    scenarios = sorted(df["시나리오"].dropna().unique().tolist())

    # 🎨 밝은 색상 팔레트
    colors = {
        "High": "#4DA6FF",   # 밝은 하늘색
        "Low": "#FF6666",    # 밝은 붉은색
        "입력 수": "#66CC66"  # 밝은 초록색
    }

    for scenario in scenarios:
        st.markdown(f"## 🧩 시나리오: {scenario}")

        sub_df = df[df["시나리오"] == scenario].copy()
        sub_df = sub_df.sort_values(["날짜", "회차"])  # ✅ 정렬 보장

        # x축 레이블: 날짜(회차)
        sub_df["x_label"] = sub_df["날짜"].dt.strftime("%m/%d") + " (" + sub_df["회차"].astype(str) + "회)"
        x_order = sub_df["x_label"].unique().tolist()  # ✅ Plotly에서 이 순서 유지

        # ---------------------------
        # ① High 변화 (모든 학생)
        # ---------------------------
        fig_high = go.Figure()
        for user, user_df in sub_df.groupby("사용자"):
            fig_high.add_trace(go.Scatter(
                x=user_df["x_label"],
                y=user_df["High"],
                mode="lines+markers",
                name=user,
                line=dict(width=3.5, color=colors["High"]),
                marker=dict(size=7, color=colors["High"]),
                opacity=0.8,
                hovertemplate=(
                    f"<b>{user}</b><br>" +
                    "날짜(회차): %{x}<br>" +
                    "High: %{y}<extra></extra>"
                )
            ))

        fig_high.update_layout(
            title=f"{scenario} | High 변화 (모든 학생)",
            xaxis_title="날짜(회차)",
            yaxis_title="횟수",
            xaxis=dict(
                categoryorder="array",
                categoryarray=x_order,
                tickangle=-30
            ),
            height=400,
            margin=dict(l=40, r=40, t=60, b=80),
            showlegend=False,
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_high, use_container_width=True)

        # ---------------------------
        # ② Low 변화 (모든 학생)
        # ---------------------------
        fig_low = go.Figure()
        for user, user_df in sub_df.groupby("사용자"):
            fig_low.add_trace(go.Scatter(
                x=user_df["x_label"],
                y=user_df["Low"],
                mode="lines+markers",
                name=user,
                line=dict(width=3.5, color=colors["Low"]),
                marker=dict(size=7, color=colors["Low"]),
                opacity=0.8,
                hovertemplate=(
                    f"<b>{user}</b><br>" +
                    "날짜(회차): %{x}<br>" +
                    "Low: %{y}<extra></extra>"
                )
            ))

        fig_low.update_layout(
            title=f"{scenario} | Low 변화 (모든 학생)",
            xaxis_title="날짜(회차)",
            yaxis_title="횟수",
            xaxis=dict(
                categoryorder="array",
                categoryarray=x_order,
                tickangle=-30
            ),
            height=400,
            margin=dict(l=40, r=40, t=60, b=80),
            showlegend=False,
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_low, use_container_width=True)

        # ---------------------------
        # ③ 입력 수 변화 (모든 학생)
        # ---------------------------
        fig_input = go.Figure()
        for user, user_df in sub_df.groupby("사용자"):
            fig_input.add_trace(go.Scatter(
                x=user_df["x_label"],
                y=user_df["입력 수"],
                mode="lines+markers",
                name=user,
                line=dict(width=3.5, color=colors["입력 수"], dash="dot"),
                marker=dict(size=7, color=colors["입력 수"]),
                opacity=0.8,
                hovertemplate=(
                    f"<b>{user}</b><br>" +
                    "날짜(회차): %{x}<br>" +
                    "입력 수: %{y}<extra></extra>"
                )
            ))

        fig_input.update_layout(
            title=f"{scenario} | 입력 수 변화 (모든 학생)",
            xaxis_title="날짜(회차)",
            yaxis_title="횟수",
            xaxis=dict(
                categoryorder="array",
                categoryarray=x_order,
                tickangle=-30
            ),
            height=400,
            margin=dict(l=40, r=40, t=60, b=80),
            showlegend=False,
            plot_bgcolor="white"
        )
        st.plotly_chart(fig_input, use_container_width=True)
