import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import datetime

# ---------- ฟังก์ชันแยกเลขจาก string ----------
def extract_numeric_column(series):
    return (
        series.astype(str)
        .str.extract(r"([\d]+\.?\d*)")[0]
        .astype(float)
    )

# ---------- ฟังก์ชันตรวจหา header ----------
def detect_header_row(uploaded_file):
    df_raw = pd.read_excel(uploaded_file, header=None)
    for i, row in df_raw.iterrows():
        if any("DateTime" in str(cell) for cell in row):
            return i
    return None

# ---------- ตั้งค่าหน้าเว็บ ----------
st.set_page_config(page_title="PEA Meter Dashboard", layout="wide")
st.title("ระบบแสดงกราฟข้อมูลมิเตอร์")
st.markdown("👀 กรุณาอัปโหลดไฟล์ .xlsx และเลือกวันเวลาที่ต้องการแสดงผล")

# ---------- ส่วนรับไฟล์จากผู้ใช้งาน ----------
uploaded_file = st.file_uploader("อัปโหลดไฟล์ Excel", type=["xlsx"])
selected_date = st.date_input("เลือกวันที่ (ปี-เดือน-วัน)")

if uploaded_file and selected_date:
    try:
        header_row = detect_header_row(uploaded_file)
        if header_row is None:
            st.error("ไม่พบแถวที่มีหัวตาราง 'DateTime'")
        else:
            df = pd.read_excel(uploaded_file, skiprows=header_row)
            df["Datetime"] = pd.to_datetime(df["DateTime"].astype(str), errors="coerce", dayfirst=True)
            df = df.dropna(subset=["Datetime"])

            # เฉพาะคอลัมน์ที่ต้องการให้เลือก
            allowed_columns = ["Voltage", "Power", "Current", "Frequency", "Energy"]
            graph_options = [col for col in df.columns if col in allowed_columns]
            graph_type = st.radio("เลือกกราฟที่ต้องการดู", graph_options)

            df_selected = df[df["Datetime"].dt.date == selected_date]
            if df_selected.empty:
                st.warning("ไม่มีข้อมูลในวันที่เลือก")
            else:
                available_times = df_selected["Datetime"].dt.strftime("%H:%M").drop_duplicates().sort_values().tolist()
                col1, col2 = st.columns(2)
                with col1:
                    start_time_str = st.selectbox("เวลาเริ่ม", available_times, key="start")
                with col2:
                    end_time_str = st.selectbox("เวลาสิ้นสุด", available_times, index=len(available_times)-1, key="end")

                if st.button("แสดงกราฟ"):
                    start_dt = pd.to_datetime(f"{selected_date} {start_time_str}")
                    end_dt = pd.to_datetime(f"{selected_date} {end_time_str}")

                    df["TimeOnly"] = df["Datetime"].dt.strftime("%H:%M")
                    df_filtered = df[
                        (df["Datetime"].dt.date == selected_date) &
                        (df["TimeOnly"] >= start_time_str) &
                        (df["TimeOnly"] <= end_time_str)
                    ].sort_values("Datetime")

                    if df_filtered.empty:
                        st.warning("ไม่พบข้อมูลในช่วงเวลาที่เลือก")
                    else:
                        df_filtered[graph_type] = extract_numeric_column(df_filtered[graph_type])
                        y_col = graph_type
                        y_min = df_filtered[y_col].min()
                        y_max = df_filtered[y_col].max()
                        y_range = y_max - y_min
                        y_dtick = 10 if y_range <= 100 else max(1, round(y_range / 20))
                        y_min_adj = y_min - 1 if y_range <= 100 else y_min - 10
                        y_max_adj = y_max + 1 if y_range <= 100 else y_max + 10

                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df_filtered["Datetime"],
                            y=df_filtered[y_col],
                            mode="lines+markers",
                            name=y_col,
                            marker=dict(color="#1f77b4")
                        ))

                        fig.update_xaxes(dtick=3600000, tickformat="%H:%M", tickangle=-45)
                        fig.update_layout(
                            title=f"{y_col} ในวันที่ {selected_date}",
                            xaxis_title="เวลา",
                            yaxis_title=y_col,
                            yaxis=dict(
                                range=[y_min_adj, y_max_adj],
                                dtick=y_dtick,
                                tickformat=".2f"
                            )
                        )

                        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
