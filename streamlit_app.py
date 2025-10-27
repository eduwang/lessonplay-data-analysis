import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime

st.set_page_config(page_title="Lesson Play 데이터 정리", layout="wide")
st.title("📊 Lesson Play 데이터 정리")

BASE_DIR = "data"
folders = ["Rehearsal", "TeachingMethod"]


# ---------------------------
# ① CSV 내부 또는 파일명에서 날짜/시간 파싱 함수
# ---------------------------
def parse_korean_datetime(raw_datetime_str: str):
    """CSV 내부 B2 셀 등에서 '2025. 9. 11. 오후 12-05-27' 형식을 처리"""
    if not isinstance(raw_datetime_str, str):
        return "", ""
    s = raw_datetime_str.strip()
    if not s:
        return "", ""

    s = re.sub(r"\s+", " ", s)
    pattern = r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2})-(\d{1,2})(?:-\d{1,2})?"
    m = re.search(pattern, s)
    if not m:
        return "", ""

    year, month, day, ampm, hour, minute = m.groups()
    year, month, day, hour, minute = map(int, [year, month, day, hour, minute])
    if ampm == "오전" and hour == 12:
        hour = 0
    elif ampm == "오후" and hour != 12:
        hour += 12

    date_str = f"{year:04d}-{month:02d}-{day:02d}"
    time_str = f"{hour:02d}{minute:02d}"
    return date_str, time_str


def parse_datetime_from_filename(filename: str):
    """파일명에서 '2025. 9. 11. 오후 12-05-27' 형식을 인식"""
    s = os.path.basename(filename)
    pattern = r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2})-(\d{1,2})"
    m = re.search(pattern, s)
    if not m:
        return "", ""
    year, month, day, ampm, hour, minute = m.groups()
    year, month, day, hour, minute = map(int, [year, month, day, hour, minute])
    if ampm == "오전" and hour == 12:
        hour = 0
    elif ampm == "오후" and hour != 12:
        hour += 12
    return f"{year:04d}-{month:02d}-{day:02d}", f"{hour:02d}{minute:02d}"


# ---------------------------
# ② 데이터 요약 수집
# ---------------------------
summary = []

for folder in folders:
    root_path = os.path.join(BASE_DIR, folder)
    if not os.path.exists(root_path):
        continue

    for root, dirs, files in os.walk(root_path):
        for file in files:
            if not file.endswith(".csv"):
                continue

            file_path = os.path.join(root, file)

            try:
                df = pd.read_csv(file_path, header=None)
            except Exception as e:
                st.warning(f"{file} 불러오는 중 오류 발생: {e}")
                continue

            # 수업 구분
            lesson_type = "Rehearsal" if "Rehearsal" in folder else "TeachingMethod"

            # 날짜/시간 (1️⃣ CSV 내부 → 2️⃣ 파일명 순으로 시도)
            raw_datetime = str(df.iloc[1, 1]) if (len(df.columns) > 1 and len(df) > 1) else ""
            date_str, time_str = parse_korean_datetime(raw_datetime)
            if not date_str:
                date_str, time_str = parse_datetime_from_filename(file)

            # 시나리오
            scenario_cell = str(df.iloc[1, 3]) if len(df.columns) > 3 and len(df) > 1 else ""
            if scenario_cell.startswith("120의 약수"):
                scenario = "약수"
            elif scenario_cell.startswith("선생님,"):
                scenario = "명제"
            else:
                scenario = ""

            # 사용자
            user = str(df.iloc[1, 0]) if len(df) > 1 else ""

            # 피드백 유무
            has_feedback = 1 if (df.shape[1] > 4 and "AI 피드백" in str(df.iloc[0, 4])) else 0

            # 입력 수 / 발문 수 / 설명 수
            input_count = question_count = explanation_count = 0
            if scenario == "명제":
                teacher_msgs = df[df.iloc[:, 2] == "교사"] if df.shape[1] > 2 else pd.DataFrame()
            elif scenario == "약수":
                if len(df) > 8 and df.shape[1] > 2:
                    df_sub = df.iloc[8:]
                    teacher_msgs = df_sub[df_sub.iloc[:, 2] == "교사"]
                else:
                    teacher_msgs = pd.DataFrame()
            else:
                teacher_msgs = pd.DataFrame()

            if not teacher_msgs.empty and df.shape[1] > 3:
                input_count = len(teacher_msgs)
                msgs = teacher_msgs.iloc[:, 3].astype(str)
                question_count = msgs.str.endswith("?").sum()
                explanation_count = input_count - question_count

            # 회차 ID
            session_id = f"{user}_{date_str}"

            summary.append({
                "수업": lesson_type,
                "날짜": date_str,
                "시간": time_str,
                "시나리오": scenario,
                "사용자": user,
                "입력 수": input_count,
                "발문 수": question_count,
                "설명 수": explanation_count,
                "피드백 유무": has_feedback,
                "파일 경로": file_path,
                "session_id": session_id
            })


# ---------------------------
# ③ 데이터프레임 출력
# ---------------------------
if summary:
    df_all = pd.DataFrame(summary)

    # ✅ 정렬 (회차 계산 전)
    df_all = df_all.sort_values(
        by=["수업", "날짜", "사용자", "시간"],
        ascending=[True, True, True, True]
    )

    # ✅ (수업, 날짜, 사용자)별로 시간 순서에 따라 회차 부여
    df_all["회차"] = (
        df_all.groupby(["수업", "날짜", "사용자"])
              .cumcount() + 1
    )

    # 인덱스 다시 1부터 부여
    df_all = df_all.reset_index(drop=True)
    df_all.index = df_all.index + 1

    # ✅ highlow.csv 불러오기 및 매칭
    highlow_path = os.path.join(BASE_DIR, "highlow.csv")
    if os.path.exists(highlow_path):
        highlow_df = pd.read_csv(highlow_path)

        def normalize_filename(name: str):
            """파일명 정규화: 확장자 제거 + 공백 정리 + 오전/오후 표준화"""
            s = os.path.splitext(str(name).strip())[0]
            s = s.replace("  ", " ")
            s = re.sub(r"\s+", " ", s)
            s = s.replace("AM", "오전").replace("PM", "오후")
            return s

        # Key 생성
        highlow_df["Key"] = highlow_df["Filename"]
        df_all["Key"] = df_all["파일 경로"].apply(lambda x: normalize_filename(os.path.basename(x)))

        # 디버깅용 출력 (체크용)
        # st.write(highlow_df[["Filename", "Key"]].head())
        # st.write(df_all[["파일 경로", "Key"]].head())

        # 병합
        df_all = df_all.merge(
            highlow_df[["Key", "High", "Low"]],
            on="Key",
            how="left"
        )

        df_all = df_all.drop(columns=["Key"])

        # High, Low 값이 없는 경우 NaN 대신 0으로
        df_all["High"] = df_all["High"].fillna(0).astype(int)
        df_all["Low"] = df_all["Low"].fillna(0).astype(int)

    else:
        st.warning("⚠️ data/highlow.csv 파일이 존재하지 않습니다. High/Low 열은 표시되지 않습니다.")

    # ✅ 멀티 필터
    lesson_options = ["전체"] + sorted(df_all["수업"].unique().tolist())
    scenario_options = ["전체"] + sorted(df_all["시나리오"].unique().tolist())
    user_options = ["전체"] + sorted(df_all["사용자"].unique().tolist())

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_lesson = st.selectbox("수업 선택", lesson_options)
    with col2:
        selected_scenario = st.selectbox("시나리오 선택", scenario_options)
    with col3:
        selected_user = st.selectbox("사용자 선택", user_options)

    # ✅ 필터 적용
    filtered_df = df_all.copy()
    if selected_lesson != "전체":
        filtered_df = filtered_df[filtered_df["수업"] == selected_lesson]
    if selected_scenario != "전체":
        filtered_df = filtered_df[filtered_df["시나리오"] == selected_scenario]
    if selected_user != "전체":
        filtered_df = filtered_df[filtered_df["사용자"] == selected_user]

    # ✅ 입력 수가 0인 데이터 제외 체크박스
    exclude_zero = st.checkbox("입력 수가 0인 데이터 제외", value=True)
    if exclude_zero:
        filtered_df = filtered_df[filtered_df["입력 수"] > 0]

    # ✅ 데이터 수 표시
    total_rows = len(filtered_df)
    st.markdown(f"**총 데이터 수: {total_rows}건**")

    # ✅ 컬럼 순서 정리 (High/Low 추가됨)
    filtered_df = filtered_df[
        ["수업", "날짜", "시간", "시나리오", "사용자", "회차",
         "입력 수", "발문 수", "설명 수", "High", "Low", "피드백 유무", "파일 경로"]
    ]

    # ✅ 테이블 출력
    st.dataframe(filtered_df, use_container_width=True)

    # ✅ CSV 다운로드
    csv = filtered_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 통합 CSV 다운로드", csv, "summary.csv", "text/csv")

else:
    st.info("📂 data 폴더에 분석할 CSV 파일이 없습니다.")
