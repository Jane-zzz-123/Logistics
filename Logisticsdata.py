import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# ---------------------- 页面基础配置 ----------------------
st.set_page_config(
    page_title="红单物流交期分析看板",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------- 数据读取与预处理 ----------------------
@st.cache_data
def load_data():
    """读取红单数据并预处理"""
    # 读取指定sheet
    url = "https://github.com/Jane-zzz-123/Logistics/raw/main/Logisticsdata.xlsx"
    df_red = pd.read_excel(url, sheet_name="上架完成-红单")

    # 指定需要分析的列
    target_cols = [
        "FBA号", "店铺", "仓库", "货代", "异常备注",
        "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
        "发货-签收", "发货-完成上架", "到货年月",
        "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)",
        "预计物流时效-实际物流时效差值", "提前/延期"
    ]

    # 确保只保留目标列（处理列名可能的空格/大小写问题）
    df_red = df_red[[col for col in target_cols if col in df_red.columns]]

    # 数据类型处理
    df_red["到货年月"] = pd.to_datetime(df_red["到货年月"], errors='coerce').dt.strftime("%Y-%m")
    df_red = df_red.dropna(subset=["到货年月"])  # 去除到货年月为空的数据

    # 数值列处理
    numeric_cols = [
        "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)",
        "预计物流时效-实际物流时效差值"
    ]
    for col in numeric_cols:
        if col in df_red.columns:
            df_red[col] = pd.to_numeric(df_red[col], errors='coerce').fillna(0)

    return df_red


# 加载数据
df_red = load_data()


# ---------------------- 工具函数 ----------------------
def get_prev_month(current_month):
    """获取上个月的年月字符串（格式：YYYY-MM）"""
    try:
        current = datetime.strptime(current_month, "%Y-%m")
        prev_month = current.replace(day=1) - pd.Timedelta(days=1)
        return prev_month.strftime("%Y-%m")
    except:
        return ""


def calculate_percent_change(current, prev):
    """计算环比变化百分比"""
    try:
        if prev == 0:
            return 0 if current == 0 else 100
        return ((current - prev) / prev) * 100
    except:
        return 0


def highlight_large_cells(val, avg, col_name):
    """高亮大于平均值的单元格"""
    try:
        # 跳过非数值和平均值行
        if pd.isna(val) or val == "-" or str(val) == "平均值":
            return ""
        val_num = float(val)
        if val_num > avg:
            return "background-color: #ffcccc"  # 浅红色
    except:
        pass
    return ""


def highlight_change(val):
    """高亮环比变化（红升绿降）"""
    try:
        # 处理空值和非数值
        if pd.isna(val) or val == "-" or str(val).strip() == "":
            return ""

        # 提取数值
        val_str = str(val).replace('%', '').strip()
        val_num = float(val_str)

        # 设置颜色
        if val_num > 0:
            return "color: red"
        elif val_num < 0:
            return "color: green"
    except:
        pass
    return ""


# ---------------------- 主页面构建 ----------------------
st.title("📦 红单分析看板区域")
st.divider()

# ===================== 一、当月的情况 =====================
st.subheader("🔍 当月红单分析")

# 时间筛选器（到货年月，最新的在最上方）
month_options = sorted(df_red["到货年月"].unique(), reverse=True) if len(df_red["到货年月"].unique()) > 0 else []
selected_month = st.selectbox(
    "选择到货年月",
    options=month_options,
    index=0 if month_options else None,
    key="month_selector_current"
) if month_options else st.write("⚠️ 暂无可用的到货年月数据")

# 筛选当月数据
if month_options and selected_month:
    df_current = df_red[df_red["到货年月"] == selected_month].copy()
    # 获取上月数据
    prev_month = get_prev_month(selected_month)
    df_prev = df_red[
        df_red["到货年月"] == prev_month].copy() if prev_month and prev_month in month_options else pd.DataFrame()

    # ---------------------- ① 核心指标卡片 ----------------------
    st.markdown("### 核心指标")

    # ---------------------- ① 核心指标卡片 ----------------------
    st.markdown("### 核心指标")

    # 计算核心指标
    # 1. FBA单数
    current_fba = len(df_current)
    prev_fba = len(df_prev) if not df_prev.empty else 0
    fba_change = current_fba - prev_fba
    fba_change_text = f"{'↑' if fba_change > 0 else '↓' if fba_change < 0 else '—'} {abs(fba_change)} (上月: {prev_fba})"
    fba_change_color = "red" if fba_change > 0 else "green" if fba_change < 0 else "gray"

    # 2. 提前/准时数
    current_on_time = len(
        df_current[df_current["提前/延期"] == "提前/准时"]) if "提前/延期" in df_current.columns else 0
    prev_on_time = len(
        df_prev[df_prev["提前/延期"] == "提前/准时"]) if not df_prev.empty and "提前/延期" in df_prev.columns else 0
    on_time_change = current_on_time - prev_on_time
    on_time_change_text = f"{'↑' if on_time_change > 0 else '↓' if on_time_change < 0 else '—'} {abs(on_time_change)} (上月: {prev_on_time})"
    on_time_change_color = "red" if on_time_change > 0 else "green" if on_time_change < 0 else "gray"

    # 3. 延期数
    current_delay = len(df_current[df_current["提前/延期"] == "延期"]) if "提前/延期" in df_current.columns else 0
    prev_delay = len(
        df_prev[df_prev["提前/延期"] == "延期"]) if not df_prev.empty and "提前/延期" in df_prev.columns else 0
    delay_change = current_delay - prev_delay
    delay_change_text = f"{'↑' if delay_change > 0 else '↓' if delay_change < 0 else '—'} {abs(delay_change)} (上月: {prev_delay})"
    delay_change_color = "red" if delay_change > 0 else "green" if delay_change < 0 else "gray"

    # 4. 绝对值差值平均值（将百分比改为差值）
    abs_col = "预计物流时效-实际物流时效差值(绝对值)"
    current_abs_avg = df_current[abs_col].mean() if abs_col in df_current.columns and len(df_current) > 0 else 0
    prev_abs_avg = df_prev[abs_col].mean() if not df_prev.empty and abs_col in df_prev.columns and len(
        df_prev) > 0 else 0
    abs_change = current_abs_avg - prev_abs_avg  # 差值计算（替换百分比）
    abs_change_text = f"{'↑' if abs_change > 0 else '↓' if abs_change < 0 else '—'} {abs(abs_change):.2f} (上月: {prev_abs_avg:.2f})"
    abs_change_color = "red" if abs_change > 0 else "green" if abs_change < 0 else "gray"

    # 5. 实际差值平均值
    diff_col = "预计物流时效-实际物流时效差值"
    current_diff_avg = df_current[diff_col].mean() if diff_col in df_current.columns and len(df_current) > 0 else 0
    prev_diff_avg = df_prev[diff_col].mean() if not df_prev.empty and diff_col in df_prev.columns and len(
        df_prev) > 0 else 0
    diff_change = current_diff_avg - prev_diff_avg
    diff_change_text = f"{'↑' if diff_change > 0 else '↓' if diff_change < 0 else '—'} {abs(diff_change):.2f} (上月: {prev_diff_avg:.2f})"
    diff_change_color = "red" if diff_change > 0 else "green" if diff_change < 0 else "gray"

    # 显示卡片（一行五列）- 改用HTML自定义样式
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;'>
            <h5 style='margin: 0; color: #333;'>FBA单</h5>
            <p style='font-size: 24px; margin: 8px 0; font-weight: bold;'>{current_fba}</p>
            <p style='font-size: 14px; color: {fba_change_color}; margin: 0;'>{fba_change_text}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style='background-color: #f0f8f0; padding: 15px; border-radius: 8px; text-align: center;'>
            <h5 style='margin: 0; color: green;'>提前/准时数</h5>
            <p style='font-size: 24px; margin: 8px 0; font-weight: bold;'>{current_on_time}</p>
            <p style='font-size: 14px; color: {on_time_change_color}; margin: 0;'>{on_time_change_text}</p>  <!-- 新增 -->
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style='background-color: #fff0f0; padding: 15px; border-radius: 8px; text-align: center;'>
            <h5 style='margin: 0; color: red;'>延期数</h5>
            <p style='font-size: 24px; margin: 8px 0; font-weight: bold;'>{current_delay}</p>
            <p style='font-size: 14px; color: {delay_change_color}; margin: 0;'>{delay_change_text}</p>  <!-- 新增 -->
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;'>
            <h5 style='margin: 0; color: #333;'>绝对值差值均值</h5>
            <p style='font-size: 24px; margin: 8px 0; font-weight: bold;'>{current_abs_avg:.2f}</p>
            <p style='font-size: 14px; color: {abs_change_color}; margin: 0;'>{abs_change_text}</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;'>
            <h5 style='margin: 0; color: #333;'>实际差值均值</h5>
            <p style='font-size: 24px; margin: 8px 0; font-weight: bold;'>{current_diff_avg:.2f}</p>
            <p style='font-size: 14px; color: {diff_change_color}; margin: 0;'>{diff_change_text}</p>
        </div>
        """, unsafe_allow_html=True)

    # 生成总结文字
    summary_text = f"""
    {selected_month.replace('-', '年')}月物流时效情况：本月的FBA单有：{current_fba}单，与上个月对比{'增加' if fba_change > 0 else '减少' if fba_change < 0 else '持平'} {abs(fba_change)}单，
    其中提前/准时单有：{current_on_time}单，与上个月对比{'增加' if on_time_change > 0 else '减少' if on_time_change < 0 else '持平'} {abs(on_time_change)}单，
    延期单有：{current_delay}单，与上个月对比{'增加' if delay_change > 0 else '减少' if delay_change < 0 else '持平'} {abs(delay_change)}单，
    预计物流时效-实际物流时效差异（绝对值）为：{current_abs_avg:.2f}，与上个月对比{'增加' if abs_change > 0 else '减少' if abs_change < 0 else '持平'} {abs(abs_change):.2f}，
    预计物流时效-实际物流时效差异为：{current_diff_avg:.2f}，与上个月对比{'增加' if diff_change > 0 else '减少' if diff_change < 0 else '持平'} {abs(diff_change):.2f}。
    """

    # 差异判断
    if current_diff_avg > 0:
        summary_text += "虽然有延迟，但延迟情况不严重，整体提前！"
    else:
        summary_text += "虽然有提前，但延迟更严重，整体还是延迟的！"

    st.markdown(f"> {summary_text}")
    st.divider()

    # ---------------------- ② 当月准时率与时效偏差 ----------------------
    # ---------------------- ② 当月准时率与时效偏差 ----------------------
    # ---------------------- ② 当月准时率与时效偏差 ----------------------
    # ---------------------- ② 当月准时率与时效偏差 ----------------------
    # ---------------------- ② 当月准时率与时效偏差 ----------------------
    st.markdown("### 准时率与时效偏差分布")
    col1, col2 = st.columns(2)

    # 左：饼图（提前/准时 vs 延期）
    with col1:
        if "提前/延期" in df_current.columns and len(df_current) > 0:
            pie_data = df_current["提前/延期"].value_counts()

            # 确保颜色映射严格生效（显式指定颜色列表）
            # 提取类别并按顺序映射颜色
            categories = pie_data.index.tolist()
            colors = []
            for cat in categories:
                if cat == "提前/准时":
                    colors.append("green")
                elif cat == "延期":
                    colors.append("red")
                else:
                    colors.append("gray")  # 处理意外类别

            fig_pie = px.pie(
                values=pie_data.values,
                names=pie_data.index,
                title=f"{selected_month} 红单准时率分布",
                color=pie_data.index,  # 显式指定颜色依据
                color_discrete_sequence=colors  # 使用顺序颜色列表确保对应关系
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.write("⚠️ 暂无准时率数据")

    # 右：文本直方图（提前/准时 和 延期）
    with col2:
        if diff_col in df_current.columns and len(df_current) > 0:
            # 提取并处理数据
            diff_data = df_current[diff_col].dropna()
            diff_data = diff_data.round().astype(int)  # 转换为整数天数

            # 分离提前/准时（>=0）和延期（<0）数据
            early_data = diff_data[diff_data >= 0]  # 包含0天（准时）
            delay_data = diff_data[diff_data < 0]  # 延期数据

            # 统计各天数出现次数
            early_counts = early_data.value_counts().sort_index(ascending=False)  # 从大到小排序
            delay_counts = delay_data.value_counts().sort_index()  # 从小到大排序（-7, -6...）

            # 计算最大计数（用于归一化显示长度）
            max_count = max(
                early_counts.max() if not early_counts.empty else 0,
                delay_counts.max() if not delay_counts.empty else 0
            )
            max_display_length = 20  # 最大显示字符数

            # 生成文本直方图（使用HTML设置颜色，与饼图保持一致）
            st.markdown("#### 提前/准时区间分布")
            if not early_counts.empty:
                for day, count in early_counts.items():
                    # 计算显示长度（按比例缩放）
                    display_length = int((count / max_count) * max_display_length) if max_count > 0 else 0
                    bar = "█" * display_length
                    day_label = f"+{day}天" if day > 0 else "0天"  # 0天特殊处理
                    # 绿色显示（与饼图提前/准时颜色一致）
                    st.markdown(
                        f"<div style='font-family: monospace;'><span style='display: inline-block; width: 60px;'>{day_label}</span>"
                        f"<span style='color: green;'>{bar}</span> <span> ({count})</span></div>",
                        unsafe_allow_html=True
                    )
            else:
                st.text("暂无提前/准时数据")

            st.markdown("#### 延迟区间分布")
            if not delay_counts.empty:
                for day, count in delay_counts.items():
                    display_length = int((count / max_count) * max_display_length) if max_count > 0 else 0
                    bar = "█" * display_length
                    # 红色显示（与饼图延期颜色一致）
                    st.markdown(
                        f"<div style='font-family: monospace;'><span style='display: inline-block; width: 60px;'>{day}天</span>"
                        f"<span style='color: red;'>{bar}</span> <span> ({count})</span></div>",
                        unsafe_allow_html=True
                    )
            else:
                st.text("暂无延迟数据")
        else:
            st.write("⚠️ 暂无时效偏差数据")

    st.divider()

    # ---------------------- ③ 当月红单明细表格 ----------------------
    # ---------------------- ③ 当月红单明细表格 ----------------------
    # ---------------------- ③ 当月红单明细表格 ----------------------
    # ---------------------- ③ 当月红单明细表格 ----------------------
    # ---------------------- ③ 当月红单明细表格 ----------------------
    st.markdown("### 红单明细（含平均值）")

    # 准备明细数据
    detail_cols = [
        "到货年月", "提前/延期", "FBA号", "店铺", "仓库", "货代",
        # 新增的物流阶段列（加在货代右边）
        "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
        "签收-发货时间", "上架完成-发货时间",
        abs_col, diff_col
    ]
    # 过滤存在的列
    detail_cols = [col for col in detail_cols if col in df_current.columns]
    df_detail = df_current[detail_cols].copy() if len(detail_cols) > 0 else pd.DataFrame()

    if len(df_detail) > 0:
        # 按时效差值升序排序
        if diff_col in df_detail.columns:
            df_detail = df_detail.sort_values(diff_col, ascending=True)

        # 定义需要显示为整数的列
        int_cols = [
            "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
            "签收-发货时间", "上架完成-发货时间"
        ]
        # 过滤存在的整数列
        int_cols = [col for col in int_cols if col in df_detail.columns]

        # 将整数列转换为无小数点格式（空值填充为0）
        for col in int_cols:
            df_detail[col] = pd.to_numeric(df_detail[col], errors='coerce').fillna(0).astype(int)

        # 计算平均值行
        avg_row = {}
        for col in detail_cols:
            if col in ["到货年月"]:
                avg_row[col] = "平均值"
            elif col in ["提前/延期", "FBA号", "店铺", "仓库", "货代"]:
                avg_row[col] = "-"
            elif col in int_cols:
                # 整数列的平均值保留两位小数
                avg_val = df_detail[col].mean()
                avg_row[col] = round(avg_val, 2)
            else:
                # 其他数值列保留两位小数
                avg_val = df_detail[col].mean() if len(df_detail) > 0 else 0
                avg_row[col] = round(avg_val, 2)


        # 格式化函数
        def format_value(val, col):
            """格式化单元格值"""
            try:
                if val == "平均值" or val == "-":
                    return val
                if col in int_cols:
                    if isinstance(val, (int, float)):
                        if val == int(val):
                            return f"{int(val)}"
                        else:
                            return f"{val:.2f}"
                elif col in [abs_col, diff_col]:
                    return f"{val:.2f}"
                return str(val)
            except:
                return str(val)


        # === 核心修复：统一列宽 + 同步滚动 + 固定行 ===
        # 1. 生成列宽样式（按列数均分宽度）
        col_width = 100 / len(detail_cols)
        col_style = f"""
        <style>
        /* 强制所有表格列宽统一 */
        .fixed-table th, .fixed-table td {{
            width: {col_width}%;
            min-width: {col_width}%;
            max-width: {col_width}%;
            box-sizing: border-box;
        }}
        </style>
        """

        # 2. 生成完整的表格HTML（单表格+sticky固定，替代绝对定位）
        html_content = f"""
        {col_style}
        <style>
        /* 容器样式 */
        .table-container {{
            height: 400px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            margin: 10px 0;
        }}

        /* 核心：单表格 + sticky固定行 */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed; /* 强制列宽均分 */
        }}

        /* 表头固定 */
        .data-table thead th {{
            position: sticky;
            top: 0;
            background-color: #f8f9fa;
            font-weight: bold;
            z-index: 2;
        }}

        /* 平均值行固定（紧跟表头） */
        .avg-row td {{
            position: sticky;
            top: 38px; /* 表头高度，精准匹配 */
            background-color: #fff3cd;
            font-weight: 500;
            z-index: 1;
        }}

        /* 通用单元格样式 */
        .data-table th, .data-table td {{
            padding: 8px;
            text-align: left;
            border: 1px solid #e0e0e0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* 高亮样式 */
        .highlight {{
            background-color: #ffcccc !important;
        }}
        </style>

        <div class="table-container">
            <table class="data-table">
                <!-- 表头 -->
                <thead>
                    <tr>
                        {''.join([f'<th>{col}</th>' for col in detail_cols])}
                    </tr>
                </thead>
                <tbody>
                    <!-- 平均值行 -->
                    <tr class="avg-row">
                        {''.join([f'<td>{format_value(avg_row[col], col)}</td>' for col in detail_cols])}
                    </tr>
                    <!-- 数据行 -->
                    {''.join([
            '<tr>' + ''.join([
                f'<td class={"highlight" if (
                        col in (int_cols + [abs_col, diff_col])
                        and avg_row[col] not in ["-", "平均值"]
                        and pd.notna(row[col])
                        and float(row[col]) > float(avg_row[col])
                ) else ""}>{format_value(row[col], col)}</td>'
                for col in detail_cols
            ]) + '</tr>'
            for _, row in df_detail.iterrows()
        ])}
                </tbody>
            </table>
        </div>
        """

        # 渲染修复后的表格
        st.markdown(html_content, unsafe_allow_html=True)

    else:
        st.write("⚠️ 暂无明细数据")

    st.divider()

    # ---------------------- ④ 当月货代准时情况 ----------------------
    st.markdown("### 货代准时情况分析")
    col1, col2 = st.columns(2)

    # 左：货代柱形图
    with col1:
        if "货代" in df_current.columns and "提前/延期" in df_current.columns and len(df_current) > 0:
            # 按货代统计提前/准时和延期数量
            freight_data = df_current.groupby(["货代", "提前/延期"]).size().unstack(fill_value=0)
            if "提前/准时" not in freight_data.columns:
                freight_data["提前/准时"] = 0
            if "延期" not in freight_data.columns:
                freight_data["延期"] = 0

            fig_freight = px.bar(
                freight_data,
                barmode="group",
                title=f"{selected_month} 货代准时情况",
                color_discrete_map={"提前/准时": "green", "延期": "red"}
            )
            fig_freight.update_layout(height=400)
            st.plotly_chart(fig_freight, use_container_width=True)
        else:
            st.write("⚠️ 暂无货代准时情况数据")

    # 右：货代准时率和平均差值表格
    with col2:
        if "货代" in df_current.columns and len(df_current) > 0:
            freight_metrics = df_current.groupby("货代").agg({
                "提前/延期": lambda x: (x == "提前/准时").sum() / len(x) * 100 if len(x) > 0 else 0,
                diff_col: "mean"
            }).round(2)
            freight_metrics.columns = ["准时率(%)", "平均时效差值"]
            st.dataframe(freight_metrics, use_container_width=True)
        else:
            st.write("⚠️ 暂无货代指标数据")

    st.divider()

    # ---------------------- ⑤ 当月仓库准时情况 ----------------------
    st.markdown("### 仓库准时情况分析")
    col1, col2 = st.columns(2)

    # 左：仓库柱形图
    with col1:
        if "仓库" in df_current.columns and "提前/延期" in df_current.columns and len(df_current) > 0:
            warehouse_data = df_current.groupby(["仓库", "提前/延期"]).size().unstack(fill_value=0)
            if "提前/准时" not in warehouse_data.columns:
                warehouse_data["提前/准时"] = 0
            if "延期" not in warehouse_data.columns:
                warehouse_data["延期"] = 0

            fig_warehouse = px.bar(
                warehouse_data,
                barmode="group",
                title=f"{selected_month} 仓库准时情况",
                color_discrete_map={"提前/准时": "green", "延期": "red"}
            )
            fig_warehouse.update_layout(height=400)
            st.plotly_chart(fig_warehouse, use_container_width=True)
        else:
            st.write("⚠️ 暂无仓库准时情况数据")

    # 右：仓库准时率和平均差值表格
    with col2:
        if "仓库" in df_current.columns and len(df_current) > 0:
            warehouse_metrics = df_current.groupby("仓库").agg({
                "提前/延期": lambda x: (x == "提前/准时").sum() / len(x) * 100 if len(x) > 0 else 0,
                diff_col: "mean"
            }).round(2)
            warehouse_metrics.columns = ["准时率(%)", "平均时效差值"]
            st.dataframe(warehouse_metrics, use_container_width=True)
        else:
            st.write("⚠️ 暂无仓库指标数据")

    st.divider()

    # ===================== 二、不同月份的红单情况 =====================
    st.subheader("📈 不同月份红单趋势分析")

    # ---------------------- ① 不同月份时效情况 ----------------------
    st.markdown("### 月度时效趋势")
    col1, col2 = st.columns(2)

    # 左：月度汇总表格
    with col1:
        if len(df_red["到货年月"].unique()) > 0:
            # 按月份统计核心指标
            month_summary = df_red.groupby("到货年月").agg({
                "FBA号": "count",
                "提前/延期": [
                    lambda x: (x == "提前/准时").sum(),
                    lambda x: (x == "延期").sum()
                ],
                abs_col: "mean",
                diff_col: "mean"
            }).round(2)

            # 重命名列
            month_summary.columns = [
                "FBA单数", "提前/准时数", "延期数",
                "绝对值差值均值", "实际差值均值"
            ]

            # 计算准时率
            month_summary["准时率(%)"] = (month_summary["提前/准时数"] / month_summary["FBA单数"] * 100).round(2)

            # 计算环比变化
            month_summary = month_summary.sort_index()
            for col in ["FBA单数", "提前/准时数", "延期数", "绝对值差值均值", "实际差值均值", "准时率(%)"]:
                month_summary[f"{col}_环比"] = month_summary[col].pct_change() * 100
                month_summary[f"{col}_环比"] = month_summary[f"{col}_环比"].round(1).astype(str) + "%"
                # 处理NaN值
                month_summary[f"{col}_环比"] = month_summary[f"{col}_环比"].replace("nan%", "-")

            # 添加平均值行
            avg_row = {
                "FBA单数": month_summary["FBA单数"].mean(),
                "提前/准时数": month_summary["提前/准时数"].mean(),
                "延期数": month_summary["延期数"].mean(),
                "绝对值差值均值": month_summary["绝对值差值均值"].mean(),
                "实际差值均值": month_summary["实际差值均值"].mean(),
                "准时率(%)": month_summary["准时率(%)"].mean()
            }
            # 环比列平均值为空
            for col in month_summary.columns:
                if "环比" in col and col not in avg_row:
                    avg_row[col] = "-"

            # 插入平均值行
            month_summary_with_avg = pd.concat([
                pd.DataFrame([avg_row], index=["平均值"]),
                month_summary
            ])

            # 高亮大于平均值的单元格
            styled_month = month_summary_with_avg.style
            for col in ["FBA单数", "提前/准时数", "延期数", "绝对值差值均值", "实际差值均值", "准时率(%)"]:
                avg_val = avg_row[col]
                styled_month = styled_month.applymap(
                    lambda x, col=col, avg=avg_val: highlight_large_cells(x, avg, col),
                    subset=pd.IndexSlice[:, col]
                )

            # 高亮环比变化
            for col in month_summary.columns:
                if "环比" in col:
                    styled_month = styled_month.applymap(
                        highlight_change,
                        subset=pd.IndexSlice[:, col]
                    )

            # 转换为HTML显示（避免styler错误）
            st.dataframe(month_summary_with_avg, use_container_width=True, height=400)
            # 单独显示样式（备选方案）
            st.markdown("""
            <style>
            .dataframe td {
                text-align: center;
            }
            .dataframe th {
                text-align: center;
            }
            </style>
            """, unsafe_allow_html=True)
        else:
            st.write("⚠️ 暂无月度汇总数据")

    # 右：月度时效差值折线图
    with col2:
        if len(df_red["到货年月"].unique()) > 0:
            line_data = df_red.groupby("到货年月").agg({
                abs_col: "mean",
                diff_col: "mean"
            }).round(2).reset_index()

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=line_data["到货年月"],
                y=line_data[abs_col],
                name="绝对值差值均值",
                line=dict(color="red")
            ))
            fig_line.add_trace(go.Scatter(
                x=line_data["到货年月"],
                y=line_data[diff_col],
                name="实际差值均值",
                line=dict(color="blue")
            ))
            fig_line.update_layout(
                title="月度物流时效差值趋势",
                height=400,
                xaxis_title="到货年月",
                yaxis_title="时效差值"
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.write("⚠️ 暂无月度趋势数据")

    st.divider()

    # ---------------------- ② 不同月份货代/仓库准时情况 ----------------------
    st.markdown("### 月度货代&仓库准时情况")
    col1, col2 = st.columns(2)

    # 左：不同月份货代准时情况
    with col1:
        if "货代" in df_red.columns and len(df_red) > 0:
            freight_month = df_red.groupby(["到货年月", "货代"]).agg({
                "提前/延期": lambda x: (x == "提前/准时").sum() / len(x) * 100 if len(x) > 0 else 0,
                diff_col: "mean"
            }).round(2)
            freight_month.columns = ["准时率(%)", "平均时效差值"]
            st.markdown("#### 货代月度准时率")
            st.dataframe(freight_month, use_container_width=True, height=400)
        else:
            st.write("⚠️ 暂无货代月度数据")

    # 右：不同月份仓库准时情况
    with col2:
        if "仓库" in df_red.columns and len(df_red) > 0:
            warehouse_month = df_red.groupby(["到货年月", "仓库"]).agg({
                "提前/延期": lambda x: (x == "提前/准时").sum() / len(x) * 100 if len(x) > 0 else 0,
                diff_col: "mean"
            }).round(2)
            warehouse_month.columns = ["准时率(%)", "平均时效差值"]
            st.markdown("#### 仓库月度准时率")
            st.dataframe(warehouse_month, use_container_width=True, height=400)
        else:
            st.write("⚠️ 暂无仓库月度数据")

    st.divider()

    # ===================== 三、数据源 =====================
    st.subheader("📋 数据源筛选")

    # ---------------------- 筛选器（单选+默认“全部”） ----------------------
    col1, col2, col3, col4 = st.columns(4)

    # 1. 到货年月筛选器（单选+默认“全部”）
    with col1:
        month_options_filter = ["全部"] + sorted(df_red["到货年月"].unique(), reverse=True)
        selected_month_filter = st.selectbox(
            "到货年月",
            options=month_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_month_single"
        )

    # 2. 仓库筛选器（单选+默认“全部”）
    with col2:
        warehouse_options_filter = ["全部"] + list(df_red["仓库"].unique()) if "仓库" in df_red.columns else ["全部"]
        selected_warehouse_filter = st.selectbox(
            "仓库",
            options=warehouse_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_warehouse_single"
        )

    # 3. 货代筛选器（单选+默认“全部”）
    with col3:
        freight_options_filter = ["全部"] + list(df_red["货代"].unique()) if "货代" in df_red.columns else ["全部"]
        selected_freight_filter = st.selectbox(
            "货代",
            options=freight_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_freight_single"
        )

    # 4. 提前/延期筛选器（单选+默认“全部”）
    with col4:
        status_options_filter = ["全部"] + list(df_red["提前/延期"].unique()) if "提前/延期" in df_red.columns else [
            "全部"]
        selected_status_filter = st.selectbox(
            "提前/延期",
            options=status_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_status_single"
        )

    # ---------------------- 应用筛选逻辑 ----------------------
    # 初始化筛选条件（默认全部数据）
    filter_conditions = pd.Series([True] * len(df_red))

    # 应用到货年月筛选
    if selected_month_filter != "全部":
        filter_conditions = filter_conditions & (df_red["到货年月"] == selected_month_filter)

    # 应用仓库筛选
    if "仓库" in df_red.columns and selected_warehouse_filter != "全部":
        filter_conditions = filter_conditions & (df_red["仓库"] == selected_warehouse_filter)

    # 应用货代筛选
    if "货代" in df_red.columns and selected_freight_filter != "全部":
        filter_conditions = filter_conditions & (df_red["货代"] == selected_freight_filter)

    # 应用提前/延期筛选
    if "提前/延期" in df_red.columns and selected_status_filter != "全部":
        filter_conditions = filter_conditions & (df_red["提前/延期"] == selected_status_filter)

    # 执行筛选
    df_filtered = df_red[filter_conditions].copy()

    # ---------------------- 显示筛选后数据 ----------------------
    st.markdown("### 原始数据（筛选后）")
    if len(df_filtered) > 0:
        # 定义要显示的列
        display_cols = [
            "到货年月", "FBA号", "店铺", "仓库", "货代", "异常备注",
            "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
            "发货-签收", "发货-完成上架", "签收-发货时间", "上架完成-发货时间",
            "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值",
            "提前/延期"
        ]
        # 过滤存在的列
        display_cols = [col for col in display_cols if col in df_filtered.columns]

        st.dataframe(
            df_filtered[display_cols],
            use_container_width=True,
            height=400
        )
        # 数据量提示
        st.caption(f"当前筛选结果共 {len(df_filtered)} 条数据 | 总数据量：{len(df_red)} 条")
    else:
        st.write("⚠️ 暂无符合筛选条件的数据")
else:
    st.write("⚠️ 请先确保数据源中有有效的到货年月数据")