import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="High–Low 변화 분석", layout="wide")
st.title("📈 사용자별 High–Low & 입력 수 변화 추이 (시나리오별)")

DATA_PATH = "data/summary.csv"

if not os.path.exists(DATA_PATH):
    st.warning("⚠️ summary.csv 파일이 없습니다. 먼저 데이터 정리 페이지에서 생성하세요.")
else:
    df = pd.read_csv(DATA_PATH)

    # ✅ 입력 수가 0인 데이터 제외
    df = df[df["입력 수"] > 0]

    # ✅ 사용자 선택 드롭다운
    users = sorted(df["사용자"].dropna().unique().tolist())
    selected_user = st.selectbox("👤 사용자 선택", users)

    # 선택된 사용자 데이터 필터링
    user_df = df[df["사용자"] == selected_user].copy()

    # 날짜 정렬
    user_df["날짜"] = pd.to_datetime(user_df["날짜"], errors="coerce")
    user_df = user_df.sort_values(["날짜", "회차"])

    # ✅ 시나리오별 분석
    grouped = user_df.groupby("시나리오")

    for scenario, sub_df in grouped:
        sub_df = sub_df.sort_values(["날짜", "회차"])

        # x축 레이블: 날짜(회차)
        sub_df["x_label"] = sub_df["날짜"].dt.strftime("%m/%d") + " (" + sub_df["회차"].astype(str) + "회)"

        st.markdown(f"### 🧩 시나리오: {scenario}")

        # Plotly 그래프 생성
        fig = go.Figure()

        # 🔵 High
        fig.add_trace(go.Scatter(
            x=sub_df["x_label"],
            y=sub_df["High"],
            mode="lines+markers",
            name="High",
            line=dict(color="blue", width=3),
            marker=dict(size=8)
        ))

        # 🔴 Low
        fig.add_trace(go.Scatter(
            x=sub_df["x_label"],
            y=sub_df["Low"],
            mode="lines+markers",
            name="Low",
            line=dict(color="red", width=3),
            marker=dict(size=8)
        ))

        # 🟢 입력 수
        fig.add_trace(go.Scatter(
            x=sub_df["x_label"],
            y=sub_df["입력 수"],
            mode="lines+markers",
            name="입력 수",
            line=dict(color="green", width=3, dash="dot"),
            marker=dict(size=8, symbol="triangle-up")
        ))

        # 그래프 설정
        fig.update_layout(
            title=f"{selected_user} | 시나리오: {scenario} | 회차별 High–Low–입력 수 변화",
            xaxis_title="날짜(회차)",
            yaxis_title="횟수",
            title_font=dict(size=16),
            xaxis=dict(tickangle=-30),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=450,
            margin=dict(l=40, r=40, t=60, b=80),
        )

        st.plotly_chart(fig, use_container_width=True)
