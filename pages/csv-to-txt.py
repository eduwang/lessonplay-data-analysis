import streamlit as st
import pandas as pd
import os
import zipfile
import io

st.set_page_config(page_title="CSV → TXT 변환 도구", layout="wide")
st.title("📝 CSV → TXT 변환 도구")

BASE_DIR = "data"
folders = ["Rehearsal", "TeachingMethod"]
output_dir = "converted_txt"
os.makedirs(output_dir, exist_ok=True)

def convert_all_csv_to_txt():
    """data 폴더 내 모든 CSV → TXT 변환"""
    converted_files = []
    error_files = []

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
                    error_files.append((file, str(e)))
                    continue

                # 화자열(index 2), 메시지열(index 3)
                if df.shape[1] < 4:
                    error_files.append((file, "열 구조 부족"))
                    continue

                speaker_col = df.iloc[:, 2].astype(str)
                message_col = df.iloc[:, 3].astype(str)

                # 텍스트 조합
                lines = []
                for s, m in zip(speaker_col, message_col):
                    if s.strip() or m.strip():
                        lines.append(f"[{s}] {m}")

                # TXT 파일 저장 (파일명 동일)
                txt_filename = os.path.splitext(file)[0] + ".txt"
                txt_path = os.path.join(output_dir, txt_filename)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

                converted_files.append(txt_path)

    return converted_files, error_files


# -----------------------------
# 🚀 실행 버튼
# -----------------------------
if st.button("🚀 CSV → TXT 변환 시작"):
    with st.spinner("CSV 파일을 TXT로 변환 중입니다..."):
        converted_files, error_files = convert_all_csv_to_txt()

    # 결과 출력
    st.success(f"✅ 변환 완료! 총 {len(converted_files)}개 파일이 생성되었습니다.")
    st.write("**출력 폴더:**", output_dir)

    if converted_files:
        # 변환된 파일 목록 표시
        st.dataframe(pd.DataFrame({"생성된 TXT 파일": [os.path.basename(f) for f in converted_files]}))

        # -----------------------------
        # 📦 ZIP 파일로 압축 및 다운로드
        # -----------------------------
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for fpath in converted_files:
                zipf.write(fpath, arcname=os.path.basename(fpath))
        zip_buffer.seek(0)

        st.download_button(
            label="📥 변환된 TXT 파일 ZIP 다운로드",
            data=zip_buffer,
            file_name="converted_txt_files.zip",
            mime="application/zip"
        )

    # 변환 실패 파일 표시
    if error_files:
        st.subheader("⚠️ 변환 실패 파일")
        st.dataframe(pd.DataFrame(error_files, columns=["파일명", "오류"]))
else:
    st.info("📂 'CSV → TXT 변환 시작' 버튼을 눌러 변환을 실행하세요.")
