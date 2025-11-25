#!/usr/bin/env python3
import os
from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def summarize_csv(df: pd.DataFrame) -> pd.DataFrame:
    # 안전하게 컬럼 준비
    if 'Potential' not in df.columns:
        df['Potential'] = '-'
    if '회차' not in df.columns:
        raise RuntimeError("CSV에 '회차' 컬럼이 필요합니다.")
    if '날짜' not in df.columns:
        raise RuntimeError("CSV에 '날짜' 컬럼이 필요합니다.")

    # 형 변환 및 정렬
    df = df.copy()
    df['회차'] = df['회차'].astype(int)
    df['날짜'] = pd.to_datetime(df['날짜']).dt.date

    # 그룹별 집계: High, Low, Total
    groups = df.groupby(['날짜', '회차'])
    summary = groups['Potential'].agg(
        high=lambda s: (s == 'High').sum(),
        low=lambda s: (s == 'Low').sum(),
        total='count'
    ).reset_index()

    summary = summary.sort_values(['날짜', '회차'])
    if summary.empty:
        return summary

    # 라벨 생성
    summary['session_label'] = summary['날짜'].astype(str) + ' #' + summary['회차'].astype(str)
    return summary


def plot_summary(summary: pd.DataFrame):
    # Plotly로 그리기
    x = summary['session_label'].tolist()

    colors = {
        'High': '#4DA6FF',
        'Low': '#FF6666',
        'Total': '#66CC66'
    }

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=summary['high'],
        mode='lines+markers',
        name='High',
        line=dict(color=colors['High'], width=3),
        marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=x,
        y=summary['low'],
        mode='lines+markers',
        name='Low',
        line=dict(color=colors['Low'], width=3),
        marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=x,
        y=summary['total'],
        mode='lines+markers',
        name='Total',
        line=dict(color=colors['Total'], width=3, dash='dot'),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title='날짜-회차별 High / Low / Total 발화 수 추이',
        xaxis_title='날짜 #회차',
        yaxis_title='발화 수',
        xaxis=dict(tickangle=-45),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=20, t=70, b=120),
        template='plotly_white'
    )

    # 한글 폰트: 브라우저에서 로드되는 폰트를 사용하도록 family 지정 (Noto Sans KR 사용 권장)
    fig.update_layout(font=dict(family='Noto Sans KR, sans-serif', size=12))

    return fig


def compute_tmssr_summary(df: pd.DataFrame) -> pd.DataFrame:
    """각 날짜·회차(session)별 TMSSR 카테고리별 개수와 비율을 계산해 반환합니다.

    반환 데이터프레임 컬럼 예시:
    ['날짜', '회차', 'session_label', 'Eliciting', 'Facilitating', 'Responding', 'Extending', 'Unknown', 'total_count']
    비율은 별도 컬럼으로 추가되지 않고, plotting 함수에서 비율로 변환합니다.
    """
    df2 = df.copy()
    if 'TMSSR' not in df2.columns:
        df2['TMSSR'] = 'Unknown'
    df2['TMSSR'] = df2['TMSSR'].fillna('Unknown')
    # '-' 표시는 분석에서 제외
    df2 = df2[df2['TMSSR'] != '-']
    df2['회차'] = df2['회차'].astype(int)
    df2['날짜'] = pd.to_datetime(df2['날짜']).dt.date

    grp = df2.groupby(['날짜', '회차', 'TMSSR']).size().reset_index(name='count')
    pivot = grp.pivot_table(index=['날짜', '회차'], columns='TMSSR', values='count', fill_value=0)
    pivot = pivot.reset_index()
    # 총합 컬럼
    pivot['total_count'] = pivot.loc[:, pivot.columns.difference(['날짜','회차'])].sum(axis=1)
    pivot['session_label'] = pivot['날짜'].astype(str) + ' #' + pivot['회차'].astype(str)
    return pivot


def plot_tmssr_proportions(pivot_df: pd.DataFrame):
    """100% 스택형 막대(세션별 TMSSR 비율)를 Plotly로 생성해서 반환합니다."""
    # TMSSR 카테고리 열 목록 (index 컬럼 제외)
    value_cols = [c for c in pivot_df.columns if c not in ('날짜', '회차', 'total_count', 'session_label')]
    labels = pivot_df['session_label'].tolist()

    fig = go.Figure()
    # 누적 스택을 위해 각 카테고리의 비율(0..1)을 계산
    totals = pivot_df['total_count'].replace(0, 1)  # 0으로 나누는 것을 방지
    for col in value_cols:
        vals = pivot_df[col].astype(float).fillna(0.0)
        frac = (vals / totals).tolist()
        # hover에 원래 개수도 표시
        hover = [f'{col}<br>{lbl}<br>count: {int(c)}<br>pct: {p:.1%}' for lbl, c, p in zip(labels, vals, frac)]
        fig.add_trace(go.Bar(
            x=labels,
            y=frac,
            name=col,
            hovertext=hover,
            hoverinfo='text'
        ))

    fig.update_layout(
        barmode='stack',
        title='세션별 TMSSR 비율 (100% 스택)',
        xaxis_title='날짜 #회차',
        yaxis_title='비율',
        yaxis=dict(tickformat='.0%'),
        margin=dict(l=40, r=20, t=70, b=120),
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    # 한글 폰트 적용
    fig.update_layout(font=dict(family='Noto Sans KR, sans-serif', size=12))
    return fig


def compute_tmssr_potential_counts(df: pd.DataFrame):
    """각 세션별(TMSSR × Potential) 개수를 계산한 피벗 테이블과 세션 레이블 목록을 반환.

    반환값: (pivot_df, labels)
    - pivot_df: 인덱스는 그대로 유지(날짜, 회차), 컬럼은 (TMSSR, Potential) 형태의 피벗 테이블
    - labels: 세션 라벨 리스트 (날짜 #회차)
    """
    df2 = df.copy()
    if 'TMSSR' not in df2.columns:
        df2['TMSSR'] = 'Unknown'
    df2['TMSSR'] = df2['TMSSR'].fillna('Unknown')
    # '-' 표시는 분석에서 제외
    df2 = df2[df2['TMSSR'] != '-']
    # Potential은 High/Low만 사용
    df2['Potential'] = df2['Potential'].fillna('-')
    df2 = df2[df2['Potential'].isin(['High', 'Low'])]

    df2['회차'] = df2['회차'].astype(int)
    df2['날짜'] = pd.to_datetime(df2['날짜']).dt.date

    grp = df2.groupby(['날짜', '회차', 'TMSSR', 'Potential']).size().reset_index(name='count')
    pivot = grp.pivot_table(index=['날짜', '회차'], columns=['TMSSR', 'Potential'], values='count', fill_value=0)

    # 세션 라벨 생성 (index 기반)
    labels = [f"{d} #{r}" for (d, r) in pivot.index.tolist()]

    # 반환: pivot (index 유지)와 labels
    return pivot, labels


def plot_tmssr_potential_trends(pivot_df: pd.DataFrame, labels: list):
    """각 TMSSR 범주별로 High/Low의 변화(세션 순서)를 막대 그래프로 표시.

    pivot_df: index가 (날짜, 회차)인 피벗 테이블
    labels: 각 인덱스에 대응하는 x축 레이블 리스트
    """
    # TMSSR 카테고리 목록 추출 (멀티컬럼 형태에서 추출)
    col_tuples = [c for c in pivot_df.columns if isinstance(c, tuple) and len(c) == 2]
    tmssr_cats = sorted({t[0] for t in col_tuples})

    # 색상 팔레트 (High, Low 쌍)
    high_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    low_palette =  ['#17becf', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2']

    fig = go.Figure()
    for i, cat in enumerate(tmssr_cats):
        color_h = high_palette[i % len(high_palette)]
        color_l = low_palette[i % len(low_palette)]

        # High bar
        col_high = (cat, 'High')
        if col_high in pivot_df.columns:
            y_high = pivot_df[col_high].astype(float).fillna(0).tolist()
        else:
            y_high = [0] * len(labels)
        fig.add_trace(go.Bar(
            x=labels,
            y=y_high,
            name=f'{cat} - High',
            marker=dict(color=color_h),
            offsetgroup=f'{cat}_high',
            legendgroup=cat,
            hovertemplate=f'{cat} - High<br>%{{x}}<br>count: %{{y}}<extra></extra>'
        ))

        # Low bar
        col_low = (cat, 'Low')
        if col_low in pivot_df.columns:
            y_low = pivot_df[col_low].astype(float).fillna(0).tolist()
        else:
            y_low = [0] * len(labels)
        fig.add_trace(go.Bar(
            x=labels,
            y=y_low,
            name=f'{cat} - Low',
            marker=dict(color=color_l),
            offsetgroup=f'{cat}_low',
            legendgroup=cat,
            hovertemplate=f'{cat} - Low<br>%{{x}}<br>count: %{{y}}<extra></extra>'
        ))

    fig.update_layout(
        title='세션별 TMSSR 범주별 High / Low (막대그래프)',
        xaxis_title='날짜 #회차',
        yaxis_title='발화 수',
        xaxis=dict(tickangle=-45),
        margin=dict(l=40, r=20, t=70, b=120),
        template='plotly_white',
        barmode='group',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    fig.update_layout(font=dict(family='Noto Sans KR, sans-serif', size=12))
    return fig


def main():
    st.title('Rehearsal: 날짜·회차별 High/Low/Total 발화 수 추이')

    # 학생 선택: 각 학생에 대해 미리 정해진 CSV 파일을 불러옵니다
    student = st.radio('학생 선택', options=['K', 'J'])
    csv_map = {
        'K': 'data/analysis-251125/rehearsal_김세진.csv',
        'J': 'data/analysis-251125/rehearsal_정민지.csv',
    }

    csv_path = csv_map.get(student)
    if not csv_path or not os.path.exists(csv_path):
        st.error(f'선택된 학생의 파일이 존재하지 않습니다: {csv_path}')
        return

    df = pd.read_csv(csv_path, dtype=str)

    # Google Noto Sans KR 로드 (브라우저가 폰트를 가져와서 Plotly에 적용)
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap" rel="stylesheet">
        <style>
        html, body { font-family: 'Noto Sans KR', sans-serif; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 요약 및 플롯 생성
    try:
        summary = summarize_csv(df)
    except Exception as e:
        st.error(f'CSV 처리 중 오류: {e}')
        return

    if summary.empty:
        st.warning('집계 결과가 없습니다. CSV 내용을 확인하세요.')
        return

    fig = plot_summary(summary)
    st.plotly_chart(fig, use_container_width=True)

    # TMSSR 비율 플롯 (세션별)
    try:
        tmssr_pivot = compute_tmssr_summary(df)
        if tmssr_pivot.shape[0] > 0:
            fig_tmssr = plot_tmssr_proportions(tmssr_pivot)
            st.plotly_chart(fig_tmssr, use_container_width=True)
        else:
            st.info('TMSSR 데이터를 찾을 수 없습니다.')
    except Exception as e:
        st.warning(f'TMSSR 시각화 생성 중 오류: {e}')

    # TMSSR 범주별 High/Low 변화 (라인 플롯)
    try:
        pivot_ph, labels_ph = compute_tmssr_potential_counts(df)
        if pivot_ph.shape[0] > 0:
            fig_ph = plot_tmssr_potential_trends(pivot_ph, labels_ph)
            st.plotly_chart(fig_ph, use_container_width=True)
        else:
            st.info('TMSSR × Potential 데이터가 없습니다.')
    except Exception as e:
        st.warning(f'TMSSR×Potential 시각화 생성 중 오류: {e}')

    # 플롯 표시 완료
    st.info('플롯이 생성되었습니다.')


if __name__ == '__main__':
    main()
