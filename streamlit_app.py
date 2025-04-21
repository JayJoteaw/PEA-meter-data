import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import datetime
import math

# ---------- ฟังก์ชันแยกเลขจาก string ----------
def extract_numeric_column(series):
    return (
        series.astype(str)
        .str.extract(r"([\d]+\.?\d*)")[0]
        .astype(float)
    )

# ---------- ฟังก์ชันตรวจหา header จาก DateTime หรือ วัน-เวลา ----------
def detect_header_row(uploaded_file, selected_sheet):
    df_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=None)
    for i, row in df_raw.iterrows():
        if any(str(cell).strip().lower() in ["datetime", "วัน-เวลา"] for cell in row):
            return i
    return None

# ---------- ตั้งค่าเบื้องต้นของหน้า ----------
st.set_page_config(page_title="PEA Meter Dashboard", layout="wide")
st.title("ระบบแสดงกราฟข้อมูลมิเตอร์")

# ---------- อัปโหลดไฟล์จากผู้ใช้งาน ----------
uploaded_file = st.file_uploader("\U0001F4C4 อัปโหลดไฟล์ Excel", type=["xlsx"])
if uploaded_file:
    excel_file = pd.ExcelFile(uploaded_file)
    sheet_names = excel_file.sheet_names
    selected_sheet = st.selectbox("เลือกชีตที่ต้องการ", sheet_names)
    st.markdown("ได้รับข้อมูลเรียบร้อยแล้ว 👌🏻")
else:
    selected_sheet = None
    st.markdown("👀 รอรับข้อมูลจากผู้ใช้งาน...")

selected_date = st.date_input("เลือกวันที่ (ปี-เดือน-วัน)")

# ---------- Mapping ค่าหน่วยของแต่ละกราฟ ----------
unit_map = {
    "Voltage": "V",
    "Power": "kW",
    "Current": "A",
    "Frequency": "Hz",
    "Energy": "kWh",
    "Load": "kVA"
}

available_times = []
file_ready = False

if uploaded_file and selected_date and selected_sheet:
    try:
        header_row = detect_header_row(uploaded_file, selected_sheet)
        if header_row is None:
            st.error("ไม่พบหัวตารางที่มี 'DateTime' หรือ 'วัน-เวลา'")
        else:
            df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, skiprows=header_row)

            # ✅ ตรวจหาชื่อคอลัมน์วันเวลา
            datetime_column = None
            for col in df.columns:
                if str(col).strip().lower() in ["datetime", "วัน-เวลา"]:
                    datetime_column = col
                    break

            if not datetime_column:
                st.error("ไม่พบคอลัมน์วันที่ (DateTime หรือ วัน-เวลา)")
                st.stop()

            df["Datetime"] = pd.to_datetime(df[datetime_column].astype(str), errors="coerce", dayfirst=True)
            df = df.dropna(subset=["Datetime"])

            # ✅ แสดงชื่อมิเตอร์และสถานะ ถ้ามีคอลัมน์อยู่ใน DataFrame
            col1, col2 = st.columns(2)

            with col1:
                if any(col.strip().lower() == "pea มิเตอร์" for col in df.columns):
                    meter_col = [col for col in df.columns if col.strip().lower() == "pea มิเตอร์"][0]
                    meter_value = df[meter_col].dropna().astype(str).unique()
                    if len(meter_value) > 0:
                        st.info(f"🔌 กำลังอ่านมิเตอร์: **{', '.join(meter_value)}**")

            with col2:
                if any(col.strip().lower() == "สถานะ" for col in df.columns):
                    status_col = [col for col in df.columns if col.strip().lower() == "สถานะ"][0]
                    status_value = df[status_col].dropna().astype(str).unique()
                    if len(status_value) > 0:
                        st.warning(f"📟 สถานะ: **{', '.join(status_value)}**")

            if not df.empty:
                min_dt = df["Datetime"].min()
                max_dt = df["Datetime"].max()
                st.success(f"🗓️ ข้อมูลมีตั้งแต่วันที่ {min_dt.strftime('%Y-%m-%d %H:%M')} ถึง {max_dt.strftime('%Y-%m-%d %H:%M')}")

            # ✅ ลบคอลัมน์ที่ไม่ต้องการให้เลือกเป็นกราฟ
            excluded_columns = ["pea มิเตอร์", "วัน-เวลา", "สถานะ"]
            graph_options = [
                col for col in df.columns
                if "date" not in col.lower()
                and not col.lower().startswith("unnamed")
                and col.lower() != "no."
                and col.lower() not in excluded_columns
                and df[col].notna().sum() > 0
            ]

            graph_type = st.radio("เลือกกราฟที่ต้องการดู", graph_options)

            df_selected = df[df["Datetime"].dt.date == selected_date]
            if df_selected.empty:
                st.warning("ไม่มีข้อมูลในวันที่คุณเลือก")
            else:
                available_times = df_selected["Datetime"].dt.strftime("%H:%M").drop_duplicates().sort_values().tolist()
                file_ready = True

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")

if file_ready and available_times:
    col1, col2 = st.columns(2)
    with col1:
        start_time_str = st.selectbox("เวลาเริ่ม", available_times, key="start_time")
    with col2:
        end_time_str = st.selectbox("เวลาสิ้นสุด", available_times, index=len(available_times)-1, key="end_time")

    if st.button("แสดงกราฟ"):
        start_dt = pd.to_datetime(f"{selected_date} {start_time_str}")
        end_dt = pd.to_datetime(f"{selected_date} {end_time_str}")

        if start_dt >= end_dt:
            st.error("เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุด")
        else:
            df["TimeOnly"] = df["Datetime"].dt.strftime("%H:%M")
            df_filtered = df[
                (df["Datetime"].dt.date == selected_date) &
                (df["TimeOnly"] >= start_time_str) &
                (df["TimeOnly"] <= end_time_str)
            ]

            df_filtered = df_filtered.sort_values("Datetime")

            if df_filtered.empty:
                st.warning("ไม่พบข้อมูลในช่วงเวลาที่เลือก")
            else:
                y_col = graph_type
                try:
                    df_filtered[y_col] = extract_numeric_column(df_filtered[y_col])
                except:
                    st.error("ไม่สามารถแปลงค่าข้อมูลในคอลัมน์เป็นตัวเลขได้")
                    st.stop()

                y_min = df_filtered[y_col].min()
                y_max = df_filtered[y_col].max()
                y_range = y_max - y_min

                # ✅ เพิ่มระยะเผื่อด้านบนกราฟ
                padding_top = y_range * 0.05
                y_min_adj = y_min
                y_max_adj = y_max + padding_top
                y_dtick = max(1, round(y_range / 20))

                y_mean = df_filtered[y_col].mean()
                y_peak = df_filtered[y_col].max()
                y_minval = df_filtered[y_col].min()
                unit_label = unit_map.get(y_col, "")

                st.markdown(f"<div style='background-color:#477c85;padding:10px;border-radius:10px;color:white'>เฉลี่ย: {y_mean:.2f} {unit_label}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='background-color:#855047;padding:10px;border-radius:10px;color:white'>สูงสุด: {y_peak:.2f} {unit_label}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='background-color:#858147;padding:10px;border-radius:10px;color:black'>ต่ำสุด: {y_minval:.2f} {unit_label}</div>", unsafe_allow_html=True)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_filtered["Datetime"],
                    y=df_filtered[y_col],
                    mode="lines+markers",
                    name=y_col,
                    marker=dict(color="#1f77b4")
                ))

                fig.add_trace(go.Scatter(
                    x=df_filtered[df_filtered[y_col] == y_peak]["Datetime"],
                    y=df_filtered[df_filtered[y_col] == y_peak][y_col],
                    mode="markers",
                    name="Peak",
                    marker=dict(color="red", size=10, symbol="circle-open-dot")
                ))

                fig.add_trace(go.Scatter(
                    x=df_filtered[df_filtered[y_col] == y_minval]["Datetime"],
                    y=df_filtered[df_filtered[y_col] == y_minval][y_col],
                    mode="markers",
                    name="Min",
                    marker=dict(color="yellow", size=10, symbol="circle-open-dot")
                ))

                fig.update_xaxes(
                    dtick=3600000,
                    tickformat="%H:%M",
                    tickangle=-45
                )

                fig.update_layout(
                    title=f"{y_col}",
                    xaxis_title="เวลา",
                    yaxis_title=f"{y_col} ({unit_label})",
                    yaxis=dict(
                        type="linear",
                        range=[y_min_adj, y_max_adj],
                        dtick=y_dtick,
                        tickformat=".2f"
                    )
                )

                st.success(f"พบข้อมูล {len(df_filtered)} แถว")
                st.plotly_chart(fig, use_container_width=True)
