import streamlit as st
st.set_page_config(page_title="PEA Meter Dashboard", layout="wide")
st.write("✅ เริ่มรันโค้ดแล้ว!!")
import pandas as pd
import plotly.graph_objs as go
import datetime
import math

st.write("✅ importสำเร็จ!")
# ---------- ฟังก์ชันแยกเลขจาก string ----------
def extract_numeric_column(series):
    return (
        series.astype(str)
        .str.extract(r"([\d]+\.?\d*)")[0]
        .astype(float)
    )

# ---------- ตั้งค่าเบื้องต้นของหน้า ----------

st.title("ระบบแสดงกราฟข้อมูลมิเตอร์")
# ✅ แสดงข้อความทันทีให้หน้าเว็บไม่ขาวเปล่า
st.markdown("👀 รอรับข้อมูลจากผู้ใช้งาน...")

# ---------- Input จากผู้ใช้งาน ----------
meter_id = st.text_input("หมายเลขมิเตอร์", value="")
selected_date = st.date_input("เลือกวันที่")

# 🔸 แสดงข้อความเตือนถ้ายังไม่ได้กรอกข้อมูล
if not meter_id or not selected_date:
    st.warning("กรุณากรอกหมายเลขมิเตอร์และเลือกวันที่ก่อน")

# ---------- Mapping ค่าหน่วยของแต่ละกราฟ ----------
unit_map = {
    "Voltage": "V",
    "Power": "kW",
    "Current": "A",
    "Frequency": "Hz",
    "Energy": "kWh"
}

available_times = []
file_ready = False

df = pd.DataFrame()
if meter_id and selected_date:
    try:
        # ✅ Debug ก่อนโหลด JSON พร้อมโชว์ URL จริง
        json_url = f"https://raw.githubusercontent.com/JayJoteaw/PEA-meter-data/main/{meter_id}.json"
        st.write(f"🔄 กำลังโหลด: {json_url}")

        df = pd.read_json(json_url)
        st.write("✅ โหลดข้อมูลสำเร็จ (ตัวอย่าง 5 แถว):")
        st.write(df.head())

        df["Datetime"] = pd.to_datetime(df["DateTime"].astype(str), errors="coerce", dayfirst=True)
        df = df.dropna(subset=["Datetime"])

        allowed_columns = ["Voltage", "Power", "Current", "Frequency", "Energy"]
        graph_options = [col for col in df.columns if col in allowed_columns]
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
            start_str = start_dt.strftime("%H:%M")
            end_str = end_dt.strftime("%H:%M")

            df_filtered = df[
                (df["Datetime"].dt.date == selected_date) &
                (df["TimeOnly"] >= start_str) &
                (df["TimeOnly"] <= end_str)
            ]

            df_filtered = df_filtered.sort_values("Datetime")

            if df_filtered.empty:
                st.warning("ไม่พบข้อมูลในช่วงเวลาที่เลือก")
            else:
                y_col = graph_type
                if y_col not in df_filtered.columns:
                    st.error(f"ไม่พบคอลัมน์ '{y_col}' ในไฟล์")
                else:
                    try:
                        df_filtered[y_col] = extract_numeric_column(df_filtered[y_col])
                    except:
                        st.error("ไม่สามารถแปลงค่าข้อมูลในคอลัมน์เป็นตัวเลขได้")
                        st.stop()

                    if df_filtered[y_col].notna().sum() > 0:
                        y_min = df_filtered[y_col].min()
                        y_max = df_filtered[y_col].max()
                        y_range = y_max - y_min

                        if y_range <= 100:
                            y_min_adj = y_min - 1
                            y_max_adj = y_max + 1
                            y_dtick = 10
                        else:
                            y_min_adj = y_min - 10
                            y_max_adj = y_max + 10
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

                        peak_points = df_filtered[df_filtered[y_col] == y_peak]
                        fig.add_trace(go.Scatter(
                            x=peak_points["Datetime"],
                            y=peak_points[y_col],
                            mode="markers",
                            name="Peak",
                            marker=dict(color="red", size=10, symbol="circle-open-dot")
                        ))

                        min_points = df_filtered[df_filtered[y_col] == y_minval]
                        fig.add_trace(go.Scatter(
                            x=min_points["Datetime"],
                            y=min_points[y_col],
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
                            title=f"{y_col} สำหรับมิเตอร์ {meter_id}",
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
                    else:
                        st.error("ไม่สามารถแสดงกราฟได้ เนื่องจากไม่มีข้อมูลตัวเลขในช่วงเวลาที่เลือก")
                        st.stop()
