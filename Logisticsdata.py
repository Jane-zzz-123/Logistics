import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
from io import BytesIO
import base64
warnings.filterwarnings('ignore')

# ---------------------- 页面基础配置 ----------------------
st.set_page_config(
    page_title="物流交期分析看板（红单+空派）",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------- 红单数据加载与预处理  ----------------------
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
# ---------------------- 空派数据加载与预处理 ----------------------
@st.cache_data
def load_air_data():
    """读取空派数据并预处理（与红单逻辑完全一致）"""
    url = "https://github.com/Jane-zzz-123/Logistics/raw/main/Logisticsdata.xlsx"
    df_air = pd.read_excel(url, sheet_name="上架完成-空派")  # 仅修改sheet名称

    target_cols = [
        "FBA号", "店铺", "仓库", "货代", "异常备注",
        "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
        "发货-签收", "发货-完成上架", "到货年月",
        "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)",
        "预计物流时效-实际物流时效差值", "提前/延期"
    ]

    df_air = df_air[[col for col in target_cols if col in df_air.columns]]
    df_air["到货年月"] = pd.to_datetime(df_air["到货年月"], errors='coerce').dt.strftime("%Y-%m")
    df_air = df_air.dropna(subset=["到货年月"])

    numeric_cols = [
        "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)",
        "预计物流时效-实际物流时效差值"
    ]
    for col in numeric_cols:
        if col in df_air.columns:
            df_air[col] = pd.to_numeric(df_air[col], errors='coerce').fillna(0)

    return df_air

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


# ---------------------- 红单看板核心逻辑 ----------------------
def render_red_dashboard(df_red):
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


        # === 1. 解决列名不完整：换行/自适应宽度 ===
        # 处理长列名（换行显示）
        def format_colname(col):
            """列名换行处理，避免截断"""
            if len(col) > 8:
                # 按特殊字符拆分长列名
                if "-" in col:
                    return col.replace("-", "<br>-")
                elif "（" in col:
                    return col.replace("（", "<br>（")
                else:
                    # 手动换行
                    return col[:8] + "<br>" + col[8:]
            return col


        # === 2. 生成带固定行的表格（列名完整） ===
        html_content = f"""
        <style>
        /* 容器样式 */
        .table-container {{
            height: 400px;
            overflow-y: auto;
            overflow-x: auto;  /* 横向滚动，避免列名截断 */
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            margin: 10px 0;
        }}

        /* 核心：单表格 + sticky固定行 */
        .data-table {{
            width: 100%;
            min-width: max-content;  /* 确保列名完整显示 */
            border-collapse: collapse;
        }}

        /* 表头固定 + 列名完整显示 */
        .data-table thead th {{
            position: sticky;
            top: 0;
            background-color: #f8f9fa;
            font-weight: bold;
            z-index: 2;
            padding: 8px 4px;  /* 减小内边距，增加显示空间 */
            white-space: normal;  /* 允许列名换行 */
            line-height: 1.2;     /* 行高适配换行 */
            text-align: center;   /* 列名居中，更易读 */
        }}

        /* 平均值行固定（紧跟表头） */
        .avg-row td {{
            position: sticky;
            top: 60px; /* 适配换行后的表头高度 */
            background-color: #fff3cd;
            font-weight: 500;
            z-index: 1;
            text-align: center;
        }}

        /* 通用单元格样式 */
        .data-table th, .data-table td {{
            padding: 8px;
            border: 1px solid #e0e0e0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* 数据行左对齐 */
        .data-table tbody tr td {{
            text-align: left;
        }}

        /* 高亮样式 */
        .highlight {{
            background-color: #ffcccc !important;
        }}
        </style>

        <div class="table-container">
            <table class="data-table">
                <!-- 表头（列名换行处理） -->
                <thead>
                    <tr>
                        {''.join([f'<th>{format_colname(col)}</th>' for col in detail_cols])}
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

        # 渲染表格
        st.markdown(html_content, unsafe_allow_html=True)

        # === 3. 添加表格下载功能 ===
        import pandas as pd
        from io import BytesIO
        import base64

        # 构建带平均值的完整数据（用于下载）
        df_download = pd.concat([pd.DataFrame([avg_row]), df_detail], ignore_index=True)


        # 定义下载函数
        def get_table_download_link(df, filename, text):
            """生成表格下载链接"""
            # 保存为Excel（保留格式）
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='红单明细')
            output.seek(0)
            b64 = base64.b64encode(output.read()).decode()

            # 生成下载链接
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
            return href


        # 显示下载按钮
        st.markdown(
            get_table_download_link(
                df_download,
                f"红单明细_{selected_month}.xlsx",
                "📥 下载红单明细表格（Excel格式）"
            ),
            unsafe_allow_html=True
        )

    else:
        st.write("⚠️ 暂无明细数据")

    st.divider()

    # ---------------------- ④ 当月货代准时情况 ----------------------
    st.markdown("### 货代准时情况分析")

    if "货代" in df_current.columns and "提前/延期" in df_current.columns and len(df_current) > 0:
        col1, col2 = st.columns(2)

        # 左：货代准时情况柱状图（保留原有逻辑）
        with col1:
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

        # 右：货代多维度分析表格（实现筛选+个数+差值计算）
        with col2:
            # 1. 筛选控件：选择分析维度（全部/仅提前/仅延期）
            st.markdown("#### 分析维度筛选")
            delay_filter = st.radio(
                "选择订单范围",
                options=["全部订单", "仅提前/准时", "仅延期"],
                horizontal=True,
                key="freight_table_filter"
            )

            # 2. 根据筛选条件过滤数据
            if delay_filter == "仅提前/准时":
                df_filtered = df_current[df_current["提前/延期"] == "提前/准时"].copy()
            elif delay_filter == "仅延期":
                df_filtered = df_current[df_current["提前/延期"] == "延期"].copy()
            else:
                df_filtered = df_current.copy()

            # 3. 定义需要计算的差值列
            abs_diff_col = "预计物流时效-实际物流时效差值(绝对值)"
            diff_col = "预计物流时效-实际物流时效差值"

            # 4. 核心：双层聚合（支持「货代」+「提前/延期」维度）
            # 4.1 基础聚合（货代+准时状态）
            freight_detail = df_filtered.groupby(["货代", "提前/延期"]).agg(
                订单个数=("FBA号", "count"),  # 新增个数列
                准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                **{
                    f"{abs_diff_col}_均值": (abs_diff_col, "mean") if abs_diff_col in df_filtered.columns else 0,
                    f"{diff_col}_均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                }
            ).reset_index()

            # 4.2 货代汇总聚合（无准时状态维度，用于对比）
            freight_summary = df_filtered.groupby("货代").agg(
                总订单个数=("FBA号", "count"),
                整体准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                **{
                    f"{abs_diff_col}_整体均值": (abs_diff_col, "mean") if abs_diff_col in df_filtered.columns else 0,
                    f"{diff_col}_整体均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                }
            ).reset_index()

            # 5. 数值格式化
            # 5.1 明细表格格式化
            freight_detail["准时率"] = freight_detail["准时率"].apply(lambda x: f"{x:.2%}")
            if abs_diff_col in freight_detail.columns:
                freight_detail[f"{abs_diff_col}_均值"] = freight_detail[f"{abs_diff_col}_均值"].round(2)
            if diff_col in freight_detail.columns:
                freight_detail[f"{diff_col}_均值"] = freight_detail[f"{diff_col}_均值"].round(2)

            # 5.2 汇总表格格式化
            freight_summary["整体准时率"] = freight_summary["整体准时率"].apply(lambda x: f"{x:.2%}")
            if abs_diff_col in freight_summary.columns:
                freight_summary[f"{abs_diff_col}_整体均值"] = freight_summary[f"{abs_diff_col}_整体均值"].round(2)
            if diff_col in freight_summary.columns:
                freight_summary[f"{diff_col}_整体均值"] = freight_summary[f"{diff_col}_整体均值"].round(2)

            # 6. 切换显示模式（汇总/明细）
            view_mode = st.radio(
                "表格显示模式",
                options=["货代汇总（无状态）", "货代+准时状态（明细）"],
                horizontal=True,
                key="freight_view_mode"
            )

            # 7. 显示对应表格
            st.markdown(f"#### {view_mode}")
            if view_mode == "货代汇总（无状态）":
                # 汇总表格（不加提前/准时/延期维度）
                st.dataframe(
                    freight_summary,
                    column_config={
                        "货代": st.column_config.TextColumn("货代名称"),
                        "总订单个数": st.column_config.NumberColumn("总订单个数", format="%d"),
                        "整体准时率": st.column_config.TextColumn("整体准时率"),
                        f"{abs_diff_col}_整体均值": st.column_config.NumberColumn("绝对值差值整体均值", format="%.2f"),
                        f"{diff_col}_整体均值": st.column_config.NumberColumn("时效差值整体均值", format="%.2f")
                    },
                    use_container_width=True,
                    height=350
                )
            else:
                # 明细表格（加提前/准时/延期维度）
                st.dataframe(
                    freight_detail,
                    column_config={
                        "货代": st.column_config.TextColumn("货代名称"),
                        "提前/延期": st.column_config.TextColumn("准时状态"),
                        "订单个数": st.column_config.NumberColumn("订单个数", format="%d"),
                        "准时率": st.column_config.TextColumn("准时率"),
                        f"{abs_diff_col}_均值": st.column_config.NumberColumn("绝对值差值均值", format="%.2f"),
                        f"{diff_col}_均值": st.column_config.NumberColumn("时效差值均值", format="%.2f")
                    },
                    use_container_width=True,
                    height=350
                )

            # 8. 下载功能
            import pandas as pd
            from io import BytesIO
            import base64


            def generate_download_link(df, filename, link_text):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='货代分析')
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{link_text}</a>'


            # 下载当前显示的表格数据
            download_df = freight_summary if view_mode == "货代汇总（无状态）" else freight_detail
            download_filename = f"货代分析_{selected_month}_{view_mode.replace('（', '').replace('）', '').replace(' ', '')}.xlsx"
            st.markdown(
                generate_download_link(download_df, download_filename, "📥 下载当前表格数据"),
                unsafe_allow_html=True
            )
    else:
        st.write("⚠️ 暂无货代准时情况数据")

    st.divider()

    # ---------------------- ⑤ 当月仓库准时情况 ----------------------
    st.markdown("### 仓库准时情况分析")

    if "仓库" in df_current.columns and "提前/延期" in df_current.columns and len(df_current) > 0:
        col1, col2 = st.columns(2)

        # 左：仓库准时情况柱状图（复用货代图表逻辑，替换为仓库维度）
        with col1:
            # 按仓库统计提前/准时和延期数量
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

        # 右：仓库多维度分析表格（完全复用货代表格逻辑，替换为仓库维度）
        with col2:
            # 1. 筛选控件：选择分析维度（全部/仅提前/仅延期）
            st.markdown("#### 分析维度筛选")
            delay_filter = st.radio(
                "选择订单范围",
                options=["全部订单", "仅提前/准时", "仅延期"],
                horizontal=True,
                key="warehouse_table_filter"
            )

            # 2. 根据筛选条件过滤数据
            if delay_filter == "仅提前/准时":
                df_filtered = df_current[df_current["提前/延期"] == "提前/准时"].copy()
            elif delay_filter == "仅延期":
                df_filtered = df_current[df_current["提前/延期"] == "延期"].copy()
            else:
                df_filtered = df_current.copy()

            # 3. 定义需要计算的差值列
            abs_diff_col = "预计物流时效-实际物流时效差值(绝对值)"
            diff_col = "预计物流时效-实际物流时效差值"

            # 4. 核心：双层聚合（支持「仓库」+「提前/延期」维度）
            # 4.1 基础聚合（仓库+准时状态）
            warehouse_detail = df_filtered.groupby(["仓库", "提前/延期"]).agg(
                订单个数=("FBA号", "count"),  # 新增个数列
                准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                **{
                    f"{abs_diff_col}_均值": (abs_diff_col, "mean") if abs_diff_col in df_filtered.columns else 0,
                    f"{diff_col}_均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                }
            ).reset_index()

            # 4.2 仓库汇总聚合（无准时状态维度，用于对比）
            warehouse_summary = df_filtered.groupby("仓库").agg(
                总订单个数=("FBA号", "count"),
                整体准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                **{
                    f"{abs_diff_col}_整体均值": (abs_diff_col, "mean") if abs_diff_col in df_filtered.columns else 0,
                    f"{diff_col}_整体均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                }
            ).reset_index()

            # 5. 数值格式化
            # 5.1 明细表格格式化
            warehouse_detail["准时率"] = warehouse_detail["准时率"].apply(lambda x: f"{x:.2%}")
            if abs_diff_col in warehouse_detail.columns:
                warehouse_detail[f"{abs_diff_col}_均值"] = warehouse_detail[f"{abs_diff_col}_均值"].round(2)
            if diff_col in warehouse_detail.columns:
                warehouse_detail[f"{diff_col}_均值"] = warehouse_detail[f"{diff_col}_均值"].round(2)

            # 5.2 汇总表格格式化
            warehouse_summary["整体准时率"] = warehouse_summary["整体准时率"].apply(lambda x: f"{x:.2%}")
            if abs_diff_col in warehouse_summary.columns:
                warehouse_summary[f"{abs_diff_col}_整体均值"] = warehouse_summary[f"{abs_diff_col}_整体均值"].round(2)
            if diff_col in warehouse_summary.columns:
                warehouse_summary[f"{diff_col}_整体均值"] = warehouse_summary[f"{diff_col}_整体均值"].round(2)

            # 6. 切换显示模式（汇总/明细）
            view_mode = st.radio(
                "表格显示模式",
                options=["仓库汇总（无状态）", "仓库+准时状态（明细）"],
                horizontal=True,
                key="warehouse_view_mode"
            )

            # 7. 显示对应表格
            st.markdown(f"#### {view_mode}")
            if view_mode == "仓库汇总（无状态）":
                # 汇总表格（不加提前/准时/延期维度）
                st.dataframe(
                    warehouse_summary,
                    column_config={
                        "仓库": st.column_config.TextColumn("仓库名称"),
                        "总订单个数": st.column_config.NumberColumn("总订单个数", format="%d"),
                        "整体准时率": st.column_config.TextColumn("整体准时率"),
                        f"{abs_diff_col}_整体均值": st.column_config.NumberColumn("绝对值差值整体均值", format="%.2f"),
                        f"{diff_col}_整体均值": st.column_config.NumberColumn("时效差值整体均值", format="%.2f")
                    },
                    use_container_width=True,
                    height=350
                )
            else:
                # 明细表格（加提前/准时/延期维度）
                st.dataframe(
                    warehouse_detail,
                    column_config={
                        "仓库": st.column_config.TextColumn("仓库名称"),
                        "提前/延期": st.column_config.TextColumn("准时状态"),
                        "订单个数": st.column_config.NumberColumn("订单个数", format="%d"),
                        "准时率": st.column_config.TextColumn("准时率"),
                        f"{abs_diff_col}_均值": st.column_config.NumberColumn("绝对值差值均值", format="%.2f"),
                        f"{diff_col}_均值": st.column_config.NumberColumn("时效差值均值", format="%.2f")
                    },
                    use_container_width=True,
                    height=350
                )

            # 8. 下载功能
            import pandas as pd
            from io import BytesIO
            import base64


            def generate_download_link(df, filename, link_text):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='仓库分析')
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{link_text}</a>'


            # 下载当前显示的表格数据
            download_df = warehouse_summary if view_mode == "仓库汇总（无状态）" else warehouse_detail
            download_filename = f"仓库分析_{selected_month}_{view_mode.replace('（', '').replace('）', '').replace(' ', '')}.xlsx"
            st.markdown(
                generate_download_link(download_df, download_filename, "📥 下载当前表格数据"),
                unsafe_allow_html=True
            )
    else:
        st.write("⚠️ 暂无仓库准时情况数据")

    st.divider()

    # ====================== 不同月份红单趋势分析（货代+仓库维度细分） ======================
    st.markdown("### 不同月份红单趋势分析（货代/仓库维度）")

    # 全局列名定义（统一管理，避免硬编码错误）
    COL_DELIVERY_MONTH = "到货年月"
    COL_DELAY_STATUS = "提前/延期"
    COL_FBA_NO = "FBA号"
    COL_FREIGHT = "货代"
    COL_WAREHOUSE = "仓库"
    COL_DIFF = "预计物流时效-实际物流时效差值"
    COL_ABS_DIFF = "预计物流时效-实际物流时效差值(绝对值)"

    # 基础数据校验
    if isinstance(df_red, pd.DataFrame) and len(df_red) > 0:
        # 检查核心列是否存在
        required_core_cols = [COL_DELIVERY_MONTH, COL_DELAY_STATUS]
        missing_core_cols = [col for col in required_core_cols if col not in df_red.columns]
        if missing_core_cols:
            st.error(f"⚠️ 缺少核心列：{missing_core_cols}，无法进行趋势分析")
        else:
            # 新增：维度筛选（整体/货代/仓库）
            st.markdown("#### 分析维度选择")
            analysis_dimension = st.radio(
                "选择分析维度",
                options=["整体趋势", "货代维度", "仓库维度"],
                horizontal=True,
                key="trend_dimension"
            )

            # 校验维度列是否存在
            if analysis_dimension == "货代维度" and COL_FREIGHT not in df_red.columns:
                st.error(f"⚠️ 缺少列：{COL_FREIGHT}，无法切换到货代维度")
                analysis_dimension = "整体趋势"
            elif analysis_dimension == "仓库维度" and COL_WAREHOUSE not in df_red.columns:
                st.error(f"⚠️ 缺少列：{COL_WAREHOUSE}，无法切换到仓库维度")
                analysis_dimension = "整体趋势"

            col1, col2 = st.columns(2)

            # ====================== 左侧：月份趋势分析表格（重写聚合逻辑+单选筛选） ======================
            with col1:
                # 1. 基础筛选控件
                st.markdown("#### 分析条件设置")
                all_months_trend = sorted(df_red[COL_DELIVERY_MONTH].dropna().unique())

                # 月份范围选择
                if len(all_months_trend) >= 2:
                    default_start = all_months_trend[-3] if len(all_months_trend) >= 3 else all_months_trend[0]
                    default_end = all_months_trend[-1]
                else:
                    default_start = default_end = all_months_trend[0] if all_months_trend else None

                start_month = end_month = ""
                if all_months_trend:
                    start_month = st.selectbox(
                        "开始月份",
                        options=all_months_trend,
                        index=all_months_trend.index(default_start) if default_start else 0,
                        key="trend_start_month"
                    )
                    end_month = st.selectbox(
                        "结束月份",
                        options=all_months_trend,
                        index=all_months_trend.index(default_end) if default_end else 0,
                        key="trend_end_month"
                    )
                else:
                    st.write("⚠️ 无可用月份数据")

                # 订单状态筛选
                delay_filter = st.radio(
                    "订单状态筛选",
                    options=["全部订单", "仅提前/准时", "仅延期"],
                    horizontal=True,
                    key="trend_delay_filter"
                )

                # 显示模式
                view_mode = st.radio(
                    "表格显示模式",
                    options=["月份汇总（无状态）", "月份+准时状态（明细）"],
                    horizontal=True,
                    key="trend_view_mode"
                )

                # 核心修改：货代/仓库改为「全部+单选」筛选
                selected_dimension = None
                if analysis_dimension == "货代维度":
                    all_freight = sorted(df_red[COL_FREIGHT].dropna().unique())
                    # 插入「全部」选项到第一个位置
                    freight_options = ["全部"] + all_freight
                    selected_freight = st.selectbox(
                        "筛选货代",
                        options=freight_options,
                        index=0,  # 默认选中「全部」
                        key="trend_freight_filter"
                    )
                    selected_dimension = selected_freight if selected_freight != "全部" else None
                elif analysis_dimension == "仓库维度":
                    all_warehouse = sorted(df_red[COL_WAREHOUSE].dropna().unique())
                    # 插入「全部」选项到第一个位置
                    warehouse_options = ["全部"] + all_warehouse
                    selected_warehouse = st.selectbox(
                        "筛选仓库",
                        options=warehouse_options,
                        index=0,  # 默认选中「全部」
                        key="trend_warehouse_filter"
                    )
                    selected_dimension = selected_warehouse if selected_warehouse != "全部" else None

                # 2. 数据过滤（适配单选+全部筛选逻辑）
                if start_month and end_month:
                    # 月份转换函数
                    def month_to_num(month_str):
                        try:
                            return int(month_str.replace("-", ""))
                        except:
                            return 0


                    # 基础月份筛选
                    df_trend_filtered = df_red[
                        (df_red[COL_DELIVERY_MONTH].apply(month_to_num) >= month_to_num(start_month)) &
                        (df_red[COL_DELIVERY_MONTH].apply(month_to_num) <= month_to_num(end_month))
                        ].copy()

                    # 订单状态筛选
                    if delay_filter == "仅提前/准时":
                        df_trend_filtered = df_trend_filtered[df_trend_filtered[COL_DELAY_STATUS] == "提前/准时"].copy()
                    elif delay_filter == "仅延期":
                        df_trend_filtered = df_trend_filtered[df_trend_filtered[COL_DELAY_STATUS] == "延期"].copy()

                    # 适配单选筛选逻辑：仅当选择了具体货代/仓库时才过滤
                    if analysis_dimension == "货代维度" and selected_dimension is not None:
                        df_trend_filtered = df_trend_filtered[
                            df_trend_filtered[COL_FREIGHT] == selected_dimension].copy()
                    elif analysis_dimension == "仓库维度" and selected_dimension is not None:
                        df_trend_filtered = df_trend_filtered[
                            df_trend_filtered[COL_WAREHOUSE] == selected_dimension].copy()

                    # 3. 重写数据聚合逻辑（核心修复：分步聚合+手动命名）
                    trend_data = pd.DataFrame()
                    if len(df_trend_filtered) > 0:
                        # 定义分组列
                        group_cols = [COL_DELIVERY_MONTH]
                        if analysis_dimension == "货代维度":
                            group_cols.insert(1, COL_FREIGHT)
                        elif analysis_dimension == "仓库维度":
                            group_cols.insert(1, COL_WAREHOUSE)

                        # 明细模式需添加状态列
                        if view_mode == "月份+准时状态（明细）":
                            group_cols.append(COL_DELAY_STATUS)

                        try:
                            # ========== 步骤1：计算订单个数 ==========
                            if COL_FBA_NO in df_trend_filtered.columns:
                                df_count = df_trend_filtered.groupby(group_cols)[COL_FBA_NO].count().reset_index()
                                df_count.rename(columns={COL_FBA_NO: "订单个数"}, inplace=True)
                            else:
                                # 备选：按行数计数
                                df_count = df_trend_filtered.groupby(group_cols).size().reset_index(name="订单个数")

                            # ========== 步骤2：计算准时率 ==========
                            # 先计算每组的准时订单数和总订单数
                            df_delay = df_trend_filtered.copy()
                            df_delay["是否准时"] = df_delay[COL_DELAY_STATUS] == "提前/准时"
                            df_rate = df_delay.groupby(group_cols).agg({
                                "是否准时": ["sum", "count"]
                            }).reset_index()
                            df_rate.columns = group_cols + ["准时订单数", "总订单数"]
                            # 计算准时率（避免除零）
                            df_rate["准时率"] = df_rate["准时订单数"] / df_rate["总订单数"].replace(0, 1)
                            # 只保留分组列和准时率
                            df_rate = df_rate[group_cols + ["准时率"]]

                            # ========== 步骤3：计算差值列均值（仅当列存在时） ==========
                            df_diff = pd.DataFrame()
                            if COL_ABS_DIFF in df_trend_filtered.columns or COL_DIFF in df_trend_filtered.columns:
                                agg_diff_dict = {}
                                if COL_ABS_DIFF in df_trend_filtered.columns:
                                    agg_diff_dict[COL_ABS_DIFF] = "mean"
                                if COL_DIFF in df_trend_filtered.columns:
                                    agg_diff_dict[COL_DIFF] = "mean"

                                if agg_diff_dict:
                                    df_diff = df_trend_filtered.groupby(group_cols).agg(agg_diff_dict).reset_index()
                                    # 重命名差值列
                                    if COL_ABS_DIFF in df_diff.columns:
                                        df_diff.rename(columns={COL_ABS_DIFF: f"{COL_ABS_DIFF}_均值"}, inplace=True)
                                    if COL_DIFF in df_diff.columns:
                                        df_diff.rename(columns={COL_DIFF: f"{COL_DIFF}_均值"}, inplace=True)

                            # ========== 步骤4：合并所有指标 ==========
                            # 先合并个数和准时率
                            trend_data = pd.merge(df_count, df_rate, on=group_cols, how="inner")
                            # 再合并差值列（如果有）
                            if not df_diff.empty:
                                trend_data = pd.merge(trend_data, df_diff, on=group_cols, how="left")

                            # ========== 步骤5：排序 ==========
                            trend_data["年月数值"] = trend_data[COL_DELIVERY_MONTH].apply(month_to_num)
                            sort_cols = ["年月数值"] + [col for col in group_cols if col != COL_DELIVERY_MONTH]
                            trend_data = trend_data.sort_values(sort_cols).drop("年月数值", axis=1)

                        except Exception as e:
                            st.error(f"数据聚合失败：{str(e)}")
                            st.write(f"分组列：{group_cols}")
                            st.write(f"过滤后数据列名：{df_trend_filtered.columns.tolist()}")
                            st.write(f"订单个数数据：{df_count.head() if 'df_count' in locals() else '无'}")
                    else:
                        st.write("⚠️ 筛选后无数据")

                    # 4. 计算筛选后整体平均值（适配维度）
                    avg_row = {}
                    df_with_avg = pd.DataFrame()
                    if len(trend_data) > 0:
                        # 定义需要计算均值的列
                        avg_cols = ["订单个数", "准时率"]
                        if f"{COL_ABS_DIFF}_均值" in trend_data.columns:
                            avg_cols.append(f"{COL_ABS_DIFF}_均值")
                        if f"{COL_DIFF}_均值" in trend_data.columns:
                            avg_cols.append(f"{COL_DIFF}_均值")

                        # 构建平均值行
                        avg_row = {col: "-" for col in trend_data.columns}
                        avg_row[COL_DELIVERY_MONTH] = "筛选后平均值"

                        # 计算各列均值
                        for col in avg_cols:
                            valid_vals = trend_data[col].dropna()
                            if len(valid_vals) > 0:
                                if col == "订单个数":
                                    avg_row[col] = round(valid_vals.mean(), 2)
                                elif col == "准时率":
                                    avg_row[col] = round(valid_vals.mean(), 4)
                                else:
                                    avg_row[col] = round(valid_vals.mean(), 2)
                            else:
                                avg_row[col] = 0

                        # 插入平均值行
                        df_with_avg = pd.concat([pd.DataFrame([avg_row]), trend_data], ignore_index=True)


                        # 5. 计算环比差值（适配维度 + 列存在性校验）
                        def calculate_monthly_diff(df, base_col, group_cols=[COL_DELIVERY_MONTH]):
                            df_data = df.iloc[1:].copy() if len(df) > 1 else df.copy()
                            if len(df_data) == 0 or base_col not in df_data.columns:
                                return df

                            # 按维度分组计算环比
                            df_data["年月数值"] = df_data[COL_DELIVERY_MONTH].apply(month_to_num)
                            sort_cols = ["年月数值"] + [c for c in group_cols if c not in [COL_DELIVERY_MONTH]]
                            df_data = df_data.sort_values(sort_cols)

                            # 环比分组列（排除年月）
                            diff_group_cols = [c for c in group_cols if c not in [COL_DELIVERY_MONTH]]
                            if diff_group_cols and all(col in df_data.columns for col in diff_group_cols):
                                df_data[f"{base_col}_环比差值"] = df_data.groupby(diff_group_cols)[base_col].diff()
                            else:
                                df_data[f"{base_col}_环比差值"] = df_data[base_col].diff()

                            df_data[f"{base_col}_环比差值"] = df_data[f"{base_col}_环比差值"].fillna(0)

                            if len(df) > 1:
                                df_result = pd.concat([df.iloc[0:1], df_data], ignore_index=True)
                            else:
                                df_result = df_data
                            return df_result.drop("年月数值", axis=1)


                        # 计算核心列环比（仅处理存在的列）
                        for col in avg_cols:
                            if col in df_with_avg.columns:
                                df_with_avg = calculate_monthly_diff(df_with_avg, col, group_cols)


                        # 6. 格式化显示（适配维度）
                        def format_value_with_diff(main_val, diff_val, col_type, is_avg=False):
                            if is_avg:
                                if col_type == "num":
                                    return f"<strong>{main_val:.2f}</strong>"
                                elif col_type == "rate":
                                    return f"<strong>{main_val:.2%}</strong>"
                                elif col_type == "diff":
                                    return f"<strong>{main_val:.2f}</strong>"
                                else:
                                    return f"<strong>{main_val}</strong>"

                            try:
                                if col_type == "num":
                                    main_str = f"{int(main_val)}"
                                elif col_type == "rate":
                                    main_str = f"{main_val:.2%}"
                                elif col_type == "diff":
                                    main_str = f"{main_val:.2f}"
                                else:
                                    main_str = str(main_val)
                            except:
                                main_str = "0"

                            if diff_val == 0:
                                diff_str = ""
                            else:
                                arrow = "↑" if diff_val > 0 else "↓"
                                color = "red" if diff_val > 0 else "green"
                                try:
                                    if col_type == "num":
                                        diff_val_str = f"{abs(int(diff_val))}"
                                    elif col_type == "rate":
                                        diff_val_str = f"{abs(diff_val):.2%}"
                                    elif col_type == "diff":
                                        diff_val_str = f"{abs(diff_val):.2f}"
                                    else:
                                        diff_val_str = f"{abs(diff_val)}"
                                except:
                                    diff_val_str = "0"

                                diff_str = f"""<span style="font-size: 0.7em; color: {color};">
                                                {arrow}{diff_val_str}
                                              </span>"""

                            return f"{main_str} {diff_str}" if diff_str else main_str


                        # 7. 生成显示数据
                        trend_display = df_with_avg.copy()
                        trend_display["is_avg"] = trend_display[COL_DELIVERY_MONTH] == "筛选后平均值"

                        # 格式化各列（仅处理存在的列）
                        if "订单个数" in trend_display.columns and "订单个数_环比差值" in trend_display.columns:
                            trend_display["订单个数"] = trend_display.apply(
                                lambda x: format_value_with_diff(x["订单个数"], x["订单个数_环比差值"], "num",
                                                                 x["is_avg"]),
                                axis=1
                            )
                            trend_display = trend_display.drop(["订单个数_环比差值", "is_avg"], axis=1)

                        if "准时率" in trend_display.columns and "准时率_环比差值" in trend_display.columns:
                            trend_display["准时率"] = trend_display.apply(
                                lambda x: format_value_with_diff(x["准时率"], x["准时率_环比差值"], "rate",
                                                                 x[COL_DELIVERY_MONTH] == "筛选后平均值"),
                                axis=1
                            )
                            trend_display = trend_display.drop("准时率_环比差值", axis=1)

                        abs_diff_mean_col = f"{COL_ABS_DIFF}_均值"
                        if abs_diff_mean_col in trend_display.columns and f"{abs_diff_mean_col}_环比差值" in trend_display.columns:
                            trend_display[abs_diff_mean_col] = trend_display.apply(
                                lambda x: format_value_with_diff(x[abs_diff_mean_col],
                                                                 x[f"{abs_diff_mean_col}_环比差值"],
                                                                 "diff", x[COL_DELIVERY_MONTH] == "筛选后平均值"),
                                axis=1
                            )
                            trend_display = trend_display.drop(f"{abs_diff_mean_col}_环比差值", axis=1)

                        diff_mean_col = f"{COL_DIFF}_均值"
                        if diff_mean_col in trend_display.columns and f"{diff_mean_col}_环比差值" in trend_display.columns:
                            trend_display[diff_mean_col] = trend_display.apply(
                                lambda x: format_value_with_diff(x[diff_mean_col], x[f"{diff_mean_col}_环比差值"],
                                                                 "diff",
                                                                 x[COL_DELIVERY_MONTH] == "筛选后平均值"),
                                axis=1
                            )
                            trend_display = trend_display.drop(f"{diff_mean_col}_环比差值", axis=1)

                        # 8. 生成HTML表格
                        st.markdown(f"#### 月份趋势分析（{analysis_dimension}）{start_month} ~ {end_month}")
                        # 补充筛选条件显示
                        if analysis_dimension == "货代维度" and selected_dimension:
                            st.markdown(f"**当前筛选：{selected_dimension}**")
                        elif analysis_dimension == "仓库维度" and selected_dimension:
                            st.markdown(f"**当前筛选：{selected_dimension}**")

                        html_style = """
                        <style>
                        .trend-table-container {
                            height: 400px;
                            overflow-y: auto;
                            border: 1px solid #e0e0e0;
                            border-radius: 4px;
                            margin: 10px 0;
                        }
                        .trend-table {
                            width: 100%;
                            border-collapse: collapse;
                        }
                        .trend-table th {
                            position: sticky;
                            top: 0;
                            background-color: #f8f9fa;
                            font-weight: bold;
                            z-index: 2;
                            padding: 8px;
                            border: 1px solid #e0e0e0;
                        }
                        .avg-row td {
                            position: sticky;
                            top: 38px;
                            background-color: #fff3cd;
                            font-weight: bold;
                            z-index: 1;
                            padding: 8px;
                            border: 1px solid #e0e0e0;
                        }
                        .trend-table td {
                            padding: 8px;
                            border: 1px solid #e0e0e0;
                        }
                        </style>
                        """

                        headers = [col for col in trend_display.columns if col != "is_avg"]
                        header_html = "".join([f"<th>{col}</th>" for col in headers])

                        rows_html = ""
                        for idx, row in trend_display.iterrows():
                            if idx == 0:
                                row_html = "<tr class='avg-row'>"
                                for col in headers:
                                    row_html += f"<td>{row[col]}</td>"
                                row_html += "</tr>"
                            else:
                                row_html = "<tr>"
                                for col in headers:
                                    row_html += f"<td>{row[col]}</td>"
                                row_html += "</tr>"
                            rows_html += row_html

                        table_html = f"""
                        {html_style}
                        <div class='trend-table-container'>
                            <table class='trend-table'>
                                <thead><tr>{header_html}</tr></thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                        </div>
                        """

                        st.markdown(table_html, unsafe_allow_html=True)


                        # 9. 下载功能
                        def generate_trend_download_link(df, filename, link_text):
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                df.to_excel(writer, index=False, sheet_name=f'{analysis_dimension}趋势')
                            output.seek(0)
                            b64 = base64.b64encode(output.read()).decode()
                            return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{link_text}</a>'


                        # 下载文件名补充筛选条件
                        download_suffix = f"_{selected_dimension}" if selected_dimension else ""
                        download_filename = f"{analysis_dimension}_月份红单趋势{download_suffix}_{start_month}_{end_month}.xlsx"
                        st.markdown(
                            generate_trend_download_link(df_with_avg, download_filename, "📥 下载趋势数据（含平均值）"),
                            unsafe_allow_html=True
                        )
                    else:
                        st.write("⚠️ 筛选后无数据")

                else:
                    st.write("⚠️ 请选择有效的月份范围")

            # ====================== 右侧：定制化折线图（适配货代/仓库维度） ======================
            with col2:
                st.markdown(f"#### 红单趋势折线图（{analysis_dimension}）")
                # 补充筛选条件显示
                if analysis_dimension == "货代维度" and selected_dimension:
                    st.markdown(f"**当前筛选：{selected_dimension}**")
                elif analysis_dimension == "仓库维度" and selected_dimension:
                    st.markdown(f"**当前筛选：{selected_dimension}**")

                # 强化数据校验
                if 'trend_data' in locals() and isinstance(trend_data, pd.DataFrame) and len(
                        trend_data) > 0 and start_month and end_month:
                    # 1. 定义需要的列
                    required_cols_base = [COL_DELIVERY_MONTH]
                    if analysis_dimension == "货代维度" and COL_FREIGHT in trend_data.columns:
                        required_cols_base.append(COL_FREIGHT)
                    elif analysis_dimension == "仓库维度" and COL_WAREHOUSE in trend_data.columns:
                        required_cols_base.append(COL_WAREHOUSE)

                    required_cols_extra = [
                        "准时率",
                        f"{COL_ABS_DIFF}_均值",
                        f"{COL_DIFF}_均值"
                    ]

                    # 过滤存在的列
                    required_cols = required_cols_base.copy()
                    for col in required_cols_extra:
                        if col in trend_data.columns:
                            required_cols.append(col)
                        else:
                            st.warning(f"⚠️ 数据中缺少列：{col}，无法绘制该指标")

                    # 基础列校验
                    if not set(required_cols_base).issubset(trend_data.columns):
                        st.error(f"⚠️ 缺少核心列：{required_cols_base}，无法绘制图表")
                    else:
                        chart_data = trend_data[required_cols].copy().dropna(subset=[COL_DELIVERY_MONTH])

                        # 列别名
                        abs_diff_col = f"{COL_ABS_DIFF}_均值"
                        diff_col = f"{COL_DIFF}_均值"


                        # 中文年月转换
                        def convert_to_chinese_month(month_str):
                            try:
                                year, month = month_str.split("-")
                                return f"{year}年{month}月"
                            except:
                                return month_str


                        chart_data["到货年月_中文"] = chart_data[COL_DELIVERY_MONTH].apply(convert_to_chinese_month)

                        # 数值转换
                        if "准时率" in chart_data.columns:
                            chart_data["准时率"] = pd.to_numeric(chart_data["准时率"], errors='coerce').fillna(0)
                        if abs_diff_col in chart_data.columns:
                            chart_data[abs_diff_col] = pd.to_numeric(chart_data[abs_diff_col], errors='coerce').fillna(
                                0).round(2)
                        if diff_col in chart_data.columns:
                            chart_data[diff_col] = pd.to_numeric(chart_data[diff_col], errors='coerce').fillna(0).round(
                                2)

                        # 排序
                        chart_data["年月数值"] = pd.to_datetime(chart_data[COL_DELIVERY_MONTH] + "-01",
                                                                errors='coerce').dt.to_period("M")
                        chart_data = chart_data.sort_values("年月数值")

                        # 绘图逻辑（适配维度）
                        if view_mode == "月份汇总（无状态）":
                            plot_cols = []
                            if abs_diff_col in chart_data.columns:
                                plot_cols.append(abs_diff_col)
                            if diff_col in chart_data.columns:
                                plot_cols.append(diff_col)
                            if "准时率" in chart_data.columns:
                                plot_cols.append("准时率")

                            if plot_cols:
                                try:
                                    # 构建折线图（按维度分组）
                                    fig_kwargs = {
                                        "data_frame": chart_data,
                                        "x": "到货年月_中文",
                                        "y": plot_cols,
                                        "title": f"{convert_to_chinese_month(start_month)} ~ {convert_to_chinese_month(end_month)} {analysis_dimension}核心指标趋势",
                                        "labels": {"value": "数值", "variable": "指标", "到货年月_中文": "到货年月"},
                                        "markers": True,
                                        "color_discrete_map": {
                                            abs_diff_col: "red",
                                            diff_col: "green",
                                            "准时率": "blue"
                                        },
                                        "category_orders": {"到货年月_中文": chart_data["到货年月_中文"].tolist()}
                                    }

                                    # 维度分组（货代/仓库）
                                    if analysis_dimension == "货代维度" and COL_FREIGHT in chart_data.columns:
                                        fig_kwargs["color"] = COL_FREIGHT
                                        fig_kwargs["line_dash"] = COL_FREIGHT
                                    elif analysis_dimension == "仓库维度" and COL_WAREHOUSE in chart_data.columns:
                                        fig_kwargs["color"] = COL_WAREHOUSE
                                        fig_kwargs["line_dash"] = COL_WAREHOUSE

                                    fig_trend = px.line(**fig_kwargs)

                                    # 折点标注
                                    for idx, row in chart_data.iterrows():
                                        x_val = row["到货年月_中文"]

                                        # 维度名称（用于标注区分）
                                        dim_name = ""
                                        if analysis_dimension == "货代维度" and COL_FREIGHT in row:
                                            dim_name = row[COL_FREIGHT]
                                        elif analysis_dimension == "仓库维度" and COL_WAREHOUSE in row:
                                            dim_name = row[COL_WAREHOUSE]

                                        # 绝对值差值标注
                                        if abs_diff_col in chart_data.columns:
                                            y_abs = row[abs_diff_col]
                                            fig_trend.add_annotation(
                                                x=x_val,
                                                y=y_abs,
                                                text=f"{dim_name}<br/>{y_abs:.2f}" if dim_name else f"{y_abs:.2f}",
                                                showarrow=True,
                                                arrowhead=1,
                                                ax=0,
                                                ay=-20,
                                                font={"size": 8, "color": "red"},
                                                bgcolor="rgba(255,255,255,0.8)"
                                            )

                                        # 时效差值标注
                                        if diff_col in chart_data.columns:
                                            y_diff = row[diff_col]
                                            fig_trend.add_annotation(
                                                x=x_val,
                                                y=y_diff,
                                                text=f"{dim_name}<br/>{y_diff:.2f}" if dim_name else f"{y_diff:.2f}",
                                                showarrow=True,
                                                arrowhead=1,
                                                ax=0,
                                                ay=-40,
                                                font={"size": 8, "color": "green"},
                                                bgcolor="rgba(255,255,255,0.8)"
                                            )

                                        # 准时率标注
                                        if "准时率" in chart_data.columns:
                                            y_rate = row["准时率"]
                                            fig_trend.add_annotation(
                                                x=x_val,
                                                y=y_rate,
                                                text=f"{dim_name}<br/>{y_rate * 100:.1f}%" if dim_name else f"{y_rate * 100:.1f}%",
                                                showarrow=True,
                                                arrowhead=1,
                                                ax=0,
                                                ay=-60,
                                                font={"size": 8, "color": "blue"},
                                                bgcolor="rgba(255,255,255,0.8)"
                                            )

                                    # 平均值参考线
                                    if 'avg_row' in locals() and len(avg_row) > 0:
                                        if abs_diff_col in chart_data.columns:
                                            avg_abs = float(avg_row.get(abs_diff_col, 0))
                                            if avg_abs != 0:
                                                fig_trend.add_hline(
                                                    y=avg_abs,
                                                    line_dash="dash",
                                                    line_color="red",
                                                    annotation_text=f"绝对值均值: {avg_abs:.2f}",
                                                    annotation_position="right"
                                                )

                                        if diff_col in chart_data.columns:
                                            avg_diff = float(avg_row.get(diff_col, 0))
                                            if avg_diff != 0:
                                                fig_trend.add_hline(
                                                    y=avg_diff,
                                                    line_dash="dash",
                                                    line_color="green",
                                                    annotation_text=f"时效差值均值: {avg_diff:.2f}",
                                                    annotation_position="right"
                                                )

                                        if "准时率" in chart_data.columns:
                                            avg_rate = float(avg_row.get("准时率", 0))
                                            if avg_rate != 0:
                                                fig_trend.add_hline(
                                                    y=avg_rate,
                                                    line_dash="dash",
                                                    line_color="blue",
                                                    annotation_text=f"准时率均值: {avg_rate * 100:.1f}%",
                                                    annotation_position="right"
                                                )

                                    # 图表样式优化
                                    fig_trend.update_layout(
                                        height=600,
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                        hovermode="x unified",
                                        yaxis=dict(rangemode="normal", fixedrange=False),
                                        xaxis=dict(
                                            tickangle=45,
                                            tickfont={"size": 10},
                                            title={"text": "到货年月", "font": {"size": 12}}
                                        )
                                    )

                                    st.plotly_chart(fig_trend, use_container_width=True)

                                except Exception as e:
                                    st.error(f"图表生成失败：{str(e)}")
                                    st.write("### 数据调试信息")
                                    st.write(f"trend_data列名：{trend_data.columns.tolist()}")
                                    st.write(f"实际使用列：{required_cols}")
                            else:
                                st.write("⚠️ 无可用的指标列生成折线图")
                        else:
                            st.write("⚠️ 请切换为「月份汇总（无状态）」模式查看折线图")
                else:
                    st.write("⚠️ 请先选择有效的筛选条件并确保有数据")
    else:
        st.write("⚠️ 无有效数据进行趋势分析")

    st.divider()

    # ===================== 三、数据源 =====================
    st.subheader("📋 红单数据源筛选")

    # ---------------------- 筛选器（单选+默认“全部”） ----------------------
    col1, col2, col3, col4 = st.columns(4)

    # 1. 到货年月筛选器（单选+默认“全部”）
    with col1:
        month_unique = df_red["到货年月"].dropna().unique()
        month_options_filter = ["全部"] + sorted(month_unique, reverse=True) if len(month_unique) > 0 else ["全部"]
        selected_month_filter = st.selectbox(
            "到货年月",
            options=month_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_month_single"
        )

    # 2. 仓库筛选器（单选+默认“全部”）
    with col2:
        warehouse_options_filter = ["全部"]
        if "仓库" in df_red.columns:
            warehouse_unique = df_red["仓库"].dropna().unique()
            if len(warehouse_unique) > 0:
                warehouse_options_filter += list(warehouse_unique)
        selected_warehouse_filter = st.selectbox(
            "仓库",
            options=warehouse_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_warehouse_single"
        )

    # 3. 货代筛选器（单选+默认“全部”）
    with col3:
        freight_options_filter = ["全部"]
        if "货代" in df_red.columns:
            freight_unique = df_red["货代"].dropna().unique()
            if len(freight_unique) > 0:
                freight_options_filter += list(freight_unique)
        selected_freight_filter = st.selectbox(
            "货代",
            options=freight_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_freight_single"
        )

    # 4. 提前/延期筛选器（单选+默认“全部”）
    with col4:
        status_options_filter = ["全部"]
        if "提前/延期" in df_red.columns:
            status_unique = df_red["提前/延期"].dropna().unique()
            if len(status_unique) > 0:
                status_options_filter += list(status_unique)
        selected_status_filter = st.selectbox(
            "提前/延期",
            options=status_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_status_single"
        )

    # ---------------------- 应用筛选逻辑 ----------------------
    filter_conditions = pd.Series([True] * len(df_red))
    if selected_month_filter != "全部" and len(df_red) > 0:
        filter_conditions = filter_conditions & (df_red["到货年月"] == selected_month_filter)
    if "仓库" in df_red.columns and selected_warehouse_filter != "全部" and len(df_red) > 0:
        filter_conditions = filter_conditions & (df_red["仓库"] == selected_warehouse_filter)
    if "货代" in df_red.columns and selected_freight_filter != "全部" and len(df_red) > 0:
        filter_conditions = filter_conditions & (df_red["货代"] == selected_freight_filter)
    if "提前/延期" in df_red.columns and selected_status_filter != "全部" and len(df_red) > 0:
        filter_conditions = filter_conditions & (df_red["提前/延期"] == selected_status_filter)
    df_filtered = df_red[filter_conditions].copy()

    # ---------------------- 计算平均值 ----------------------
    avg_target_cols = [
        "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
        "发货-签收", "发货-完成上架", "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值"
    ]
    display_cols = [
        "到货年月", "FBA号", "店铺", "仓库", "货代", "提前/延期",
        "异常备注", "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
        "发货-签收", "发货-完成上架", "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值"
    ]
    display_cols = [col for col in display_cols if col in df_filtered.columns]

    # 初始化平均值
    avg_row = {col: "-" for col in display_cols}
    if len(df_filtered) > 0:
        for col in avg_target_cols:
            if col in display_cols:
                numeric_vals = pd.to_numeric(df_filtered[col], errors='coerce').dropna()
                avg_row[col] = round(numeric_vals.mean(), 2) if len(numeric_vals) > 0 else 0.00

    # 处理数据行
    df_display = df_filtered[display_cols].copy() if len(df_filtered) > 0 else pd.DataFrame(columns=display_cols)
    for col in avg_target_cols:
        if col in df_display.columns:
            df_display[col] = pd.to_numeric(df_display[col], errors='coerce')

    # ---------------------- 生成表格（修复样式语法） ----------------------
    st.markdown("### 原始数据（含筛选后平均值）")

    # 列宽配置（简化为单行字符串，避免语法错误）
    col_width_config = {
        "到货年月": "80px", "FBA号": "120px", "店铺": "80px", "仓库": "80px",
        "货代": "80px", "提前/延期": "80px", "异常备注": "100px", "发货-提取": "80px",
        "提取-到港": "80px", "到港-签收": "80px", "签收-完成上架": "100px", "发货-签收": "80px",
        "发货-完成上架": "100px", "签收-发货时间": "100px", "上架完成-发货时间": "120px",
        "预计物流时效-实际物流时效差值(绝对值)": "150px", "预计物流时效-实际物流时效差值": "150px"
    }

    # 核心修复：CSS样式改为单行紧凑格式，避免换行导致的语法错误
    table_css = """
    <style>
    /* 全局表格样式重置 */
    .table-outer {
        width: 100%;
        border: 1px solid #dee2e6;
        margin: 10px 0;
        font-size: 14px;
    }
    /* 固定头部容器 */
    .table-fixed {
        position: sticky;
        top: 0;
        background: white;
        z-index: 99;
    }
    /* 表头样式 */
    .table-header th {
        width: var(--col-width);
        max-width: var(--col-width);
        min-width: var(--col-width);
        padding: 8px 12px;
        border: 1px solid #dee2e6;
        background: #e9ecef;
        font-weight: bold;
        text-align: left;
        white-space: normal;
        word-wrap: break-word;
        vertical-align: top;
    }
    /* 平均值行样式 */
    .table-avg td {
        width: var(--col-width);
        max-width: var(--col-width);
        min-width: var(--col-width);
        padding: 8px 12px;
        border: 1px solid #dee2e6;
        background: #fff3cd;
        font-weight: bold;
        text-align: left;
        white-space: normal;
        word-wrap: break-word;
        vertical-align: top;
    }
    /* 数据滚动容器 */
    .table-scroll {
        height: 400px;
        overflow-y: auto;
        overflow-x: hidden;
    }
    /* 数据行样式 */
    .table-data td {
        width: var(--col-width);
        max-width: var(--col-width);
        min-width: var(--col-width);
        padding: 8px 12px;
        border: 1px solid #dee2e6;
        text-align: left;
        white-space: normal;
        word-wrap: break-word;
        vertical-align: top;
    }
    /* 高亮单元格 */
    .highlight {
        background-color: #ffebee !important;
    }
    /* 表格布局统一 */
    .table-header, .table-avg, .table-data {
        width: 100%;
        table-layout: fixed;
        border-collapse: collapse;
        border-spacing: 0;
    }
    </style>
    """

    # 构建表头（使用CSS变量传递列宽，避免内联样式换行错误）
    header_html = "<table class='table-header'><tr>"
    for col in display_cols:
        width = col_width_config.get(col, "100px")
        header_html += f"<th style='--col-width: {width}'>{col}</th>"
    header_html += "</tr></table>"

    # 构建平均值行
    avg_html = "<table class='table-avg'><tr>"
    for col in display_cols:
        width = col_width_config.get(col, "100px")
        val = avg_row[col]
        if col in avg_target_cols and isinstance(val, (int, float)):
            val = f"{val:.2f}"
        avg_html += f"<td style='--col-width: {width}'>{val}</td>"
    avg_html += "</tr></table>"

    # 构建数据行
    data_html = "<table class='table-data'><tbody>"
    if len(df_display) > 0:
        for _, row in df_display.iterrows():
            data_html += "<tr>"
            for col in display_cols:
                width = col_width_config.get(col, "100px")
                val = row[col]
                highlight = "highlight" if (
                            col in avg_target_cols and pd.notna(val) and pd.notna(avg_row[col]) and isinstance(
                        avg_row[col], (int, float)) and float(val) > avg_row[col]) else ""
                display_val = f"{val:.2f}" if (col in avg_target_cols and isinstance(val, (int, float))) else (
                    "" if pd.isna(val) else str(val))
                data_html += f"<td style='--col-width: {width}' class='{highlight}'>{display_val}</td>"
            data_html += "</tr>"
    else:
        data_html += f"<tr><td colspan='{len(display_cols)}' style='text-align: center; padding: 20px;'>⚠️ 暂无符合筛选条件的数据</td></tr>"
    data_html += "</tbody></table>"

    # 拼接最终HTML（核心：使用CSS变量传递列宽，避免内联样式换行）
    final_html = f"""
    {table_css}
    <div class='table-outer'>
        <div class='table-fixed'>
            {header_html}
            {avg_html}
        </div>
        <div class='table-scroll'>
            {data_html}
        </div>
    </div>
    """

    st.markdown(final_html, unsafe_allow_html=True)

    # 数据量提示
    if len(df_filtered) > 0:
        st.caption(f"当前筛选结果共 {len(df_filtered)} 条数据 | 总数据量：{len(df_red)} 条")
    else:
        st.caption("⚠️ 暂无符合筛选条件的业务数据")
# ---------------------- 空派看板核心逻辑（1:1复刻红单，仅修改指定项） ----------------------
def render_air_dashboard(df_air):
    st.title("✈️ 空派分析看板区域")
    st.divider()

    # ===================== 一、当月的情况 =====================
    st.subheader("🔍 当月空派分析")

    month_options = sorted(df_air["到货年月"].unique(), reverse=True) if len(df_air["到货年月"].unique()) > 0 else []
    selected_month = st.selectbox(
        "选择到货年月",
        options=month_options,
        index=0 if month_options else None,
        key="air_month_selector_current"
    ) if month_options else st.write("⚠️ 暂无可用的到货年月数据")

    if month_options and selected_month:
        df_current = df_air[df_air["到货年月"] == selected_month].copy()
        prev_month = get_prev_month(selected_month)
        df_prev = df_air[df_air["到货年月"] == prev_month].copy() if prev_month and prev_month in month_options else pd.DataFrame()

        # ---------------------- ① 核心指标卡片 ----------------------
        st.markdown("### 核心指标")

        # 计算核心指标（逻辑完全一致）
        current_fba = len(df_current)
        prev_fba = len(df_prev) if not df_prev.empty else 0
        fba_change = current_fba - prev_fba
        fba_change_text = f"{'↑' if fba_change > 0 else '↓' if fba_change < 0 else '—'} {abs(fba_change)} (上月: {prev_fba})"
        fba_change_color = "red" if fba_change > 0 else "green" if fba_change < 0 else "gray"

        current_on_time = len(df_current[df_current["提前/延期"] == "提前/准时"]) if "提前/延期" in df_current.columns else 0
        prev_on_time = len(df_prev[df_prev["提前/延期"] == "提前/准时"]) if not df_prev.empty and "提前/延期" in df_prev.columns else 0
        on_time_change = current_on_time - prev_on_time
        on_time_change_text = f"{'↑' if on_time_change > 0 else '↓' if on_time_change < 0 else '—'} {abs(on_time_change)} (上月: {prev_on_time})"
        on_time_change_color = "red" if on_time_change > 0 else "green" if on_time_change < 0 else "gray"

        current_delay = len(df_current[df_current["提前/延期"] == "延期"]) if "提前/延期" in df_current.columns else 0
        prev_delay = len(df_prev[df_prev["提前/延期"] == "延期"]) if not df_prev.empty and "提前/延期" in df_prev.columns else 0
        delay_change = current_delay - prev_delay
        delay_change_text = f"{'↑' if delay_change > 0 else '↓' if delay_change < 0 else '—'} {abs(delay_change)} (上月: {prev_delay})"
        delay_change_color = "red" if delay_change > 0 else "green" if delay_change < 0 else "gray"

        abs_col = "预计物流时效-实际物流时效差值(绝对值)"
        current_abs_avg = df_current[abs_col].mean() if abs_col in df_current.columns and len(df_current) > 0 else 0
        prev_abs_avg = df_prev[abs_col].mean() if not df_prev.empty and abs_col in df_prev.columns and len(df_prev) > 0 else 0
        abs_change = current_abs_avg - prev_abs_avg
        abs_change_text = f"{'↑' if abs_change > 0 else '↓' if abs_change < 0 else '—'} {abs(abs_change):.2f} (上月: {prev_abs_avg:.2f})"
        abs_change_color = "red" if abs_change > 0 else "green" if abs_change < 0 else "gray"

        diff_col = "预计物流时效-实际物流时效差值"
        current_diff_avg = df_current[diff_col].mean() if diff_col in df_current.columns and len(df_current) > 0 else 0
        prev_diff_avg = df_prev[diff_col].mean() if not df_prev.empty and diff_col in df_prev.columns and len(df_prev) > 0 else 0
        diff_change = current_diff_avg - prev_diff_avg
        diff_change_text = f"{'↑' if diff_change > 0 else '↓' if diff_change < 0 else '—'} {abs(diff_change):.2f} (上月: {prev_diff_avg:.2f})"
        diff_change_color = "red" if diff_change > 0 else "green" if diff_change < 0 else "gray"

        # 显示卡片（仅修改标题文本）
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
                <p style='font-size: 14px; color: {on_time_change_color}; margin: 0;'>{on_time_change_text}</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div style='background-color: #fff0f0; padding: 15px; border-radius: 8px; text-align: center;'>
                <h5 style='margin: 0; color: red;'>延期数</h5>
                <p style='font-size: 24px; margin: 8px 0; font-weight: bold;'>{current_delay}</p>
                <p style='font-size: 14px; color: {delay_change_color}; margin: 0;'>{delay_change_text}</p>
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

        # 生成总结文字（仅修改“红单”为“空派”）
        summary_text = f"""
        {selected_month.replace('-', '年')}月物流时效情况：本月的FBA单有：{current_fba}单，与上个月对比{'增加' if fba_change > 0 else '减少' if fba_change < 0 else '持平'} {abs(fba_change)}单，
        其中提前/准时单有：{current_on_time}单，与上个月对比{'增加' if on_time_change > 0 else '减少' if on_time_change < 0 else '持平'} {abs(on_time_change)}单，
        延期单有：{current_delay}单，与上个月对比{'增加' if delay_change > 0 else '减少' if delay_change < 0 else '持平'} {abs(delay_change)}单，
        预计物流时效-实际物流时效差异（绝对值）为：{current_abs_avg:.2f}，与上个月对比{'增加' if abs_change > 0 else '减少' if abs_change < 0 else '持平'} {abs(abs_change):.2f}，
        预计物流时效-实际物流时效差异为：{current_diff_avg:.2f}，与上个月对比{'增加' if diff_change > 0 else '减少' if diff_change < 0 else '持平'} {abs(diff_change):.2f}。
        """

        if current_diff_avg > 0:
            summary_text += "虽然有延迟，但延迟情况不严重，整体提前！"
        else:
            summary_text += "虽然有提前，但延迟更严重，整体还是延迟的！"

        st.markdown(f"> {summary_text}")
        st.divider()
        # ---------------------- ② 当月准时率与时效偏差 ----------------------
        st.markdown("### 准时率与时效偏差分布")
        col1, col2 = st.columns(2)

        # 左：饼图（仅修改标题文本）
        with col1:
            if "提前/延期" in df_current.columns and len(df_current) > 0:
                pie_data = df_current["提前/延期"].value_counts()
                categories = pie_data.index.tolist()
                colors = []
                for cat in categories:
                    if cat == "提前/准时":
                        colors.append("green")
                    elif cat == "延期":
                        colors.append("red")
                    else:
                        colors.append("gray")

                fig_pie = px.pie(
                    values=pie_data.values,
                    names=pie_data.index,
                    title=f"{selected_month} 空派准时率分布",  # 红单→空派
                    color=pie_data.index,
                    color_discrete_sequence=colors
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("⚠️ 暂无准时率数据")

        # 右：文本直方图（逻辑完全一致）
        with col2:
            if diff_col in df_current.columns and len(df_current) > 0:
                diff_data = df_current[diff_col].dropna()
                diff_data = diff_data.round().astype(int)

                early_data = diff_data[diff_data >= 0]
                delay_data = diff_data[diff_data < 0]

                early_counts = early_data.value_counts().sort_index(ascending=False)
                delay_counts = delay_data.value_counts().sort_index()

                max_count = max(
                    early_counts.max() if not early_counts.empty else 0,
                    delay_counts.max() if not delay_counts.empty else 0
                )
                max_display_length = 20

                st.markdown("#### 提前/准时区间分布")
                if not early_counts.empty:
                    for day, count in early_counts.items():
                        display_length = int((count / max_count) * max_display_length) if max_count > 0 else 0
                        bar = "█" * display_length
                        day_label = f"+{day}天" if day > 0 else "0天"
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
        # ---------------------- ③ 当月空派明细表格（按要求修改） ----------------------
        st.markdown("### 空派明细（含平均值）")  # 红单→空派

        # 明细列修改：替换物流阶段列+新增异常备注、清关耗时
        detail_cols = [
            "到货年月", "提前/延期", "FBA号", "店铺", "仓库", "货代",
            "发货-起飞", "到港-提取", "提取-签收", "异常备注", "清关耗时",  # 替换列名+新增列
            "签收-完成上架",
            "签收-发货时间", "上架完成-发货时间",
            abs_col, diff_col
        ]
        detail_cols = [col for col in detail_cols if col in df_current.columns]
        df_detail = df_current[detail_cols].copy() if len(detail_cols) > 0 else pd.DataFrame()

        if len(df_detail) > 0:
            if diff_col in df_detail.columns:
                df_detail = df_detail.sort_values(diff_col, ascending=True)

            # 整数列修改（适配空派列名）
            int_cols = [
                "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架",
                "签收-发货时间", "上架完成-发货时间"
            ]
            int_cols = [col for col in int_cols if col in df_detail.columns]

            for col in int_cols:
                df_detail[col] = pd.to_numeric(df_detail[col], errors='coerce').fillna(0).astype(int)

            # 计算平均值行（清关耗时不计算平均值）
            avg_row = {}
            for col in detail_cols:
                if col in ["到货年月"]:
                    avg_row[col] = "平均值"
                elif col in ["提前/延期", "FBA号", "店铺", "仓库", "货代", "异常备注", "清关耗时"]:  # 清关耗时排除
                    avg_row[col] = "-"
                elif col in int_cols:
                    avg_val = df_detail[col].mean()
                    avg_row[col] = round(avg_val, 2)
                else:
                    avg_val = df_detail[col].mean() if len(df_detail) > 0 else 0
                    avg_row[col] = round(avg_val, 2)

            # 格式化函数（逻辑一致）
            def format_value(val, col):
                try:
                    if val == "平均值" or val == "-":
                        return val
                    if col in int_cols:
                        if isinstance(val, (int, float)):
                            if val == int(val):
                                return f"{int(val)}"
                            else:
                                return f"{val:.2f}"
                    elif col in [abs_col, diff_col, "清关耗时"]:  # 新增清关耗时
                        return f"{val:.2f}"
                    return str(val)
                except:
                    return str(val)

            # 列名换行处理（逻辑一致）
            def format_colname(col):
                if len(col) > 8:
                    if "-" in col:
                        return col.replace("-", "<br>-")
                    elif "（" in col:
                        return col.replace("（", "<br>（")
                    else:
                        return col[:8] + "<br>" + col[8:]
                return col

            # 新增：清关耗时≥1标浅红的样式
            def highlight_customs_days(val):
                try:
                    if pd.isna(val) or val == "-" or str(val) == "平均值":
                        return ""
                    val_num = float(val)
                    if val_num >= 1:
                        return "background-color: #ffcccc"
                except:
                    pass
                return ""

            # 生成HTML表格（新增清关耗时高亮）
            html_content = f"""
            <style>
            .table-container {{
                height: 400px;
                overflow-y: auto;
                overflow-x: auto;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin: 10px 0;
            }}
            .data-table {{
                width: 100%;
                min-width: max-content;
                border-collapse: collapse;
            }}
            .data-table thead th {{
                position: sticky;
                top: 0;
                background-color: #f8f9fa;
                font-weight: bold;
                z-index: 2;
                padding: 8px 4px;
                white-space: normal;
                line-height: 1.2;
                text-align: center;
            }}
            .avg-row td {{
                position: sticky;
                top: 60px;
                background-color: #fff3cd;
                font-weight: 500;
                z-index: 1;
                text-align: center;
            }}
            .data-table th, .data-table td {{
                padding: 8px;
                border: 1px solid #e0e0e0;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .data-table tbody tr td {{
                text-align: left;
            }}
            .highlight {{
                background-color: #ffcccc !important;
            }}
            .customs-highlight {{
                background-color: #ffcccc !important;
            }}
            </style>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            {''.join([f'<<th>{format_colname(col)}</</th>' for col in detail_cols])}
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="avg-row">
                            {''.join([f'<td>{format_value(avg_row[col], col)}</td>' for col in detail_cols])}
                        </tr>
                        {''.join([
                '<tr>' + ''.join([
                    f'<td class="{
                        "customs-highlight" if col == "清关耗时" and pd.notna(row[col]) and float(row[col]) >= 1
                        else "highlight" if (
                            col in (int_cols + [abs_col, diff_col])
                            and avg_row[col] not in ["-", "平均值"]
                            and pd.notna(row[col])
                            and float(row[col]) > float(avg_row[col])
                        ) else ""
                    }">{format_value(row[col], col)}</td>'
                    for col in detail_cols
                ]) + '</tr>'
                for _, row in df_detail.iterrows()
            ])}
                    </tbody>
                </table>
            </div>
            """
            st.markdown(html_content, unsafe_allow_html=True)

            # 下载功能（仅修改文件名）
            df_download = pd.concat([pd.DataFrame([avg_row]), df_detail], ignore_index=True)
            st.markdown(
                generate_download_link(
                    df_download,
                    f"空派明细_{selected_month}.xlsx",  # 红单→空派
                    "📥 下载空派明细表格（Excel格式）"  # 红单→空派
                ),
                unsafe_allow_html=True
            )
        else:
            st.write("⚠️ 暂无明细数据")

        st.divider()
        # ---------------------- ④ 当月货代准时情况（仅修改文本） ----------------------
        st.markdown("### 货代准时情况分析")

        if "货代" in df_current.columns and "提前/延期" in df_current.columns and len(df_current) > 0:
            col1, col2 = st.columns(2)

            # 左：柱状图（仅修改标题）
            with col1:
                freight_data = df_current.groupby(["货代", "提前/延期"]).size().unstack(fill_value=0)
                if "提前/准时" not in freight_data.columns:
                    freight_data["提前/准时"] = 0
                if "延期" not in freight_data.columns:
                    freight_data["延期"] = 0

                fig_freight = px.bar(
                    freight_data,
                    barmode="group",
                    title=f"{selected_month} 货代准时情况",  # 逻辑一致，文本不变（无需改）
                    color_discrete_map={"提前/准时": "green", "延期": "red"}
                )
                fig_freight.update_layout(height=400)
                st.plotly_chart(fig_freight, use_container_width=True)

            # 右：分析表格（逻辑完全一致，仅修改key）
            with col2:
                st.markdown("#### 分析维度筛选")
                delay_filter = st.radio(
                    "选择订单范围",
                    options=["全部订单", "仅提前/准时", "仅延期"],
                    horizontal=True,
                    key="air_freight_table_filter"  # 唯一key
                )

                if delay_filter == "仅提前/准时":
                    df_filtered = df_current[df_current["提前/延期"] == "提前/准时"].copy()
                elif delay_filter == "仅延期":
                    df_filtered = df_current[df_current["提前/延期"] == "延期"].copy()
                else:
                    df_filtered = df_current.copy()

                # 聚合数据（逻辑一致）
                freight_detail = df_filtered.groupby(["货代", "提前/延期"]).agg(
                    订单个数=("FBA号", "count"),
                    准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                    **{
                        f"{abs_col}_均值": (abs_col, "mean") if abs_col in df_filtered.columns else 0,
                        f"{diff_col}_均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                    }
                ).reset_index()

                freight_summary = df_filtered.groupby("货代").agg(
                    总订单个数=("FBA号", "count"),
                    整体准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                    **{
                        f"{abs_col}_整体均值": (abs_col, "mean") if abs_col in df_filtered.columns else 0,
                        f"{diff_col}_整体均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                    }
                ).reset_index()

                # 格式化（逻辑一致）
                freight_detail["准时率"] = freight_detail["准时率"].apply(lambda x: f"{x:.2%}")
                if abs_col in freight_detail.columns:
                    freight_detail[f"{abs_col}_均值"] = freight_detail[f"{abs_col}_均值"].round(2)
                if diff_col in freight_detail.columns:
                    freight_detail[f"{diff_col}_均值"] = freight_detail[f"{diff_col}_均值"].round(2)

                freight_summary["整体准时率"] = freight_summary["整体准时率"].apply(lambda x: f"{x:.2%}")
                if abs_col in freight_summary.columns:
                    freight_summary[f"{abs_col}_整体均值"] = freight_summary[f"{abs_col}_整体均值"].round(2)
                if diff_col in freight_summary.columns:
                    freight_summary[f"{diff_col}_整体均值"] = freight_summary[f"{diff_col}_整体均值"].round(2)

                # 显示模式（逻辑一致，仅修改key）
                view_mode = st.radio(
                    "表格显示模式",
                    options=["货代汇总（无状态）", "货代+准时状态（明细）"],
                    horizontal=True,
                    key="air_freight_view_mode"  # 唯一key
                )

                st.markdown(f"#### {view_mode}")
                if view_mode == "货代汇总（无状态）":
                    st.dataframe(
                        freight_summary,
                        column_config={
                            "货代": st.column_config.TextColumn("货代名称"),
                            "总订单个数": st.column_config.NumberColumn("总订单个数", format="%d"),
                            "整体准时率": st.column_config.TextColumn("整体准时率"),
                            f"{abs_col}_整体均值": st.column_config.NumberColumn("绝对值差值整体均值", format="%.2f"),
                            f"{diff_col}_整体均值": st.column_config.NumberColumn("时效差值整体均值", format="%.2f")
                        },
                        use_container_width=True,
                        height=350
                    )
                else:
                    st.dataframe(
                        freight_detail,
                        column_config={
                            "货代": st.column_config.TextColumn("货代名称"),
                            "提前/延期": st.column_config.TextColumn("准时状态"),
                            "订单个数": st.column_config.NumberColumn("订单个数", format="%d"),
                            "准时率": st.column_config.TextColumn("准时率"),
                            f"{abs_col}_均值": st.column_config.NumberColumn("绝对值差值均值", format="%.2f"),
                            f"{diff_col}_均值": st.column_config.NumberColumn("时效差值均值", format="%.2f")
                        },
                        use_container_width=True,
                        height=350
                    )

                # 下载（仅修改文件名）
                download_df = freight_summary if view_mode == "货代汇总（无状态）" else freight_detail
                download_filename = f"空派货代分析_{selected_month}_{view_mode.replace('（', '').replace('）', '').replace(' ', '')}.xlsx"  # 红单→空派
                st.markdown(
                    generate_download_link(download_df, download_filename, "📥 下载当前表格数据"),
                    unsafe_allow_html=True
                )
        else:
            st.write("⚠️ 暂无货代准时情况数据")

        st.divider()

        # ---------------------- ⑤ 当月仓库准时情况（仅修改文本和key） ----------------------
        st.markdown("### 仓库准时情况分析")

        if "仓库" in df_current.columns and "提前/延期" in df_current.columns and len(df_current) > 0:
            col1, col2 = st.columns(2)

            # 左：柱状图（仅修改标题）
            with col1:
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

            # 右：分析表格（逻辑一致，仅修改key）
            with col2:
                st.markdown("#### 分析维度筛选")
                delay_filter = st.radio(
                    "选择订单范围",
                    options=["全部订单", "仅提前/准时", "仅延期"],
                    horizontal=True,
                    key="air_warehouse_table_filter"  # 唯一key
                )

                if delay_filter == "仅提前/准时":
                    df_filtered = df_current[df_current["提前/延期"] == "提前/准时"].copy()
                elif delay_filter == "仅延期":
                    df_filtered = df_current[df_current["提前/延期"] == "延期"].copy()
                else:
                    df_filtered = df_current.copy()

                # 聚合数据（逻辑一致）
                warehouse_detail = df_filtered.groupby(["仓库", "提前/延期"]).agg(
                    订单个数=("FBA号", "count"),
                    准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                    **{
                        f"{abs_col}_均值": (abs_col, "mean") if abs_col in df_filtered.columns else 0,
                        f"{diff_col}_均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                    }
                ).reset_index()

                warehouse_summary = df_filtered.groupby("仓库").agg(
                    总订单个数=("FBA号", "count"),
                    整体准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                    **{
                        f"{abs_col}_整体均值": (abs_col, "mean") if abs_col in df_filtered.columns else 0,
                        f"{diff_col}_整体均值": (diff_col, "mean") if diff_col in df_filtered.columns else 0
                    }
                ).reset_index()

                # 格式化（逻辑一致）
                warehouse_detail["准时率"] = warehouse_detail["准时率"].apply(lambda x: f"{x:.2%}")
                if abs_col in warehouse_detail.columns:
                    warehouse_detail[f"{abs_col}_均值"] = warehouse_detail[f"{abs_col}_均值"].round(2)
                if diff_col in warehouse_detail.columns:
                    warehouse_detail[f"{diff_col}_均值"] = warehouse_detail[f"{diff_col}_均值"].round(2)

                warehouse_summary["整体准时率"] = warehouse_summary["整体准时率"].apply(lambda x: f"{x:.2%}")
                if abs_col in warehouse_summary.columns:
                    warehouse_summary[f"{abs_col}_整体均值"] = warehouse_summary[f"{abs_col}_整体均值"].round(2)
                if diff_col in warehouse_summary.columns:
                    warehouse_summary[f"{diff_col}_整体均值"] = warehouse_summary[f"{diff_col}_整体均值"].round(2)

                # 显示模式（逻辑一致，仅修改key）
                view_mode = st.radio(
                    "表格显示模式",
                    options=["仓库汇总（无状态）", "仓库+准时状态（明细）"],
                    horizontal=True,
                    key="air_warehouse_view_mode"  # 唯一key
                )

                st.markdown(f"#### {view_mode}")
                if view_mode == "仓库汇总（无状态）":
                    st.dataframe(
                        warehouse_summary,
                        column_config={
                            "仓库": st.column_config.TextColumn("仓库名称"),
                            "总订单个数": st.column_config.NumberColumn("总订单个数", format="%d"),
                            "整体准时率": st.column_config.TextColumn("整体准时率"),
                            f"{abs_col}_整体均值": st.column_config.NumberColumn("绝对值差值整体均值", format="%.2f"),
                            f"{diff_col}_整体均值": st.column_config.NumberColumn("时效差值整体均值", format="%.2f")
                        },
                        use_container_width=True,
                        height=350
                    )
                else:
                    st.dataframe(
                        warehouse_detail,
                        column_config={
                            "仓库": st.column_config.TextColumn("仓库名称"),
                            "提前/延期": st.column_config.TextColumn("准时状态"),
                            "订单个数": st.column_config.NumberColumn("订单个数", format="%d"),
                            "准时率": st.column_config.TextColumn("准时率"),
                            f"{abs_col}_均值": st.column_config.NumberColumn("绝对值差值均值", format="%.2f"),
                            f"{diff_col}_均值": st.column_config.NumberColumn("时效差值均值", format="%.2f")
                        },
                        use_container_width=True,
                        height=350
                    )

                # 下载（仅修改文件名）
                download_df = warehouse_summary if view_mode == "仓库汇总（无状态）" else warehouse_detail
                download_filename = f"空派仓库分析_{selected_month}_{view_mode.replace('（', '').replace('）', '').replace(' ', '')}.xlsx"  # 红单→空派
                st.markdown(
                    generate_download_link(download_df, download_filename, "📥 下载当前表格数据"),
                    unsafe_allow_html=True
                )
        else:
            st.write("⚠️ 暂无仓库准时情况数据")

        st.divider()

        # ====================== 不同月份空派趋势分析（仅修改文本和key） ======================
        st.markdown("### 不同月份空派趋势分析（货代/仓库维度）")  # 红单→空派

        COL_DELIVERY_MONTH = "到货年月"
        COL_DELAY_STATUS = "提前/延期"
        COL_FBA_NO = "FBA号"
        COL_FREIGHT = "货代"
        COL_WAREHOUSE = "仓库"
        COL_DIFF = diff_col
        COL_ABS_DIFF = abs_col

        if isinstance(df_air, pd.DataFrame) and len(df_air) > 0:
            required_core_cols = [COL_DELIVERY_MONTH, COL_DELAY_STATUS]
            missing_core_cols = [col for col in required_core_cols if col not in df_air.columns]
            if missing_core_cols:
                st.error(f"⚠️ 缺少核心列：{missing_core_cols}，无法进行趋势分析")
            else:
                st.markdown("#### 分析维度选择")
                analysis_dimension = st.radio(
                    "选择分析维度",
                    options=["整体趋势", "货代维度", "仓库维度"],
                    horizontal=True,
                    key="air_trend_dimension"  # 唯一key
                )

                if analysis_dimension == "货代维度" and COL_FREIGHT not in df_air.columns:
                    st.error(f"⚠️ 缺少列：{COL_FREIGHT}，无法切换到货代维度")
                    analysis_dimension = "整体趋势"
                elif analysis_dimension == "仓库维度" and COL_WAREHOUSE not in df_air.columns:
                    st.error(f"⚠️ 缺少列：{COL_WAREHOUSE}，无法切换到仓库维度")
                    analysis_dimension = "整体趋势"

                col1, col2 = st.columns(2)

                # 左侧：趋势表格（逻辑一致，仅修改key和文本）
                with col1:
                    st.markdown("#### 分析条件设置")
                    all_months_trend = sorted(df_air[COL_DELIVERY_MONTH].dropna().unique())

                    if len(all_months_trend) >= 2:
                        default_start = all_months_trend[-3] if len(all_months_trend) >= 3 else all_months_trend[0]
                        default_end = all_months_trend[-1]
                    else:
                        default_start = default_end = all_months_trend[0] if all_months_trend else None

                    start_month = end_month = ""
                    if all_months_trend:
                        start_month = st.selectbox(
                            "开始月份",
                            options=all_months_trend,
                            index=all_months_trend.index(default_start) if default_start else 0,
                            key="air_trend_start_month"  # 唯一key
                        )
                        end_month = st.selectbox(
                            "结束月份",
                            options=all_months_trend,
                            index=all_months_trend.index(default_end) if default_end else 0,
                            key="air_trend_end_month"  # 唯一key
                        )
                    else:
                        st.write("⚠️ 无可用月份数据")

                    delay_filter = st.radio(
                        "订单状态筛选",
                        options=["全部订单", "仅提前/准时", "仅延期"],
                        horizontal=True,
                        key="air_trend_delay_filter"  # 唯一key
                    )

                    view_mode = st.radio(
                        "表格显示模式",
                        options=["月份汇总（无状态）", "月份+准时状态（明细）"],
                        horizontal=True,
                        key="air_trend_view_mode"  # 唯一key
                    )

                    # 维度筛选（逻辑一致，仅修改key）
                    selected_dimension = None
                    if analysis_dimension == "货代维度":
                        all_freight = sorted(df_air[COL_FREIGHT].dropna().unique())
                        freight_options = ["全部"] + all_freight
                        selected_freight = st.selectbox(
                            "筛选货代",
                            options=freight_options,
                            index=0,
                            key="air_trend_freight_filter"  # 唯一key
                        )
                        selected_dimension = selected_freight if selected_freight != "全部" else None
                    elif analysis_dimension == "仓库维度":
                        all_warehouse = sorted(df_air[COL_WAREHOUSE].dropna().unique())
                        warehouse_options = ["全部"] + all_warehouse
                        selected_warehouse = st.selectbox(
                            "筛选仓库",
                            options=warehouse_options,
                            index=0,
                            key="air_trend_warehouse_filter"  # 唯一key
                        )
                        selected_dimension = selected_warehouse if selected_warehouse != "全部" else None

                    # 数据过滤+聚合（逻辑完全一致）
                    if start_month and end_month:
                        def month_to_num(month_str):
                            try:
                                return int(month_str.replace("-", ""))
                            except:
                                return 0

                        df_trend_filtered = df_air[
                            (df_air[COL_DELIVERY_MONTH].apply(month_to_num) >= month_to_num(start_month)) &
                            (df_air[COL_DELIVERY_MONTH].apply(month_to_num) <= month_to_num(end_month))
                            ].copy()

                        if delay_filter == "仅提前/准时":
                            df_trend_filtered = df_trend_filtered[df_trend_filtered[COL_DELAY_STATUS] == "提前/准时"].copy()
                        elif delay_filter == "仅延期":
                            df_trend_filtered = df_trend_filtered[df_trend_filtered[COL_DELAY_STATUS] == "延期"].copy()

                        if analysis_dimension == "货代维度" and selected_dimension is not None:
                            df_trend_filtered = df_trend_filtered[df_trend_filtered[COL_FREIGHT] == selected_dimension].copy()
                        elif analysis_dimension == "仓库维度" and selected_dimension is not None:
                            df_trend_filtered = df_trend_filtered[df_trend_filtered[COL_WAREHOUSE] == selected_dimension].copy()

                        # 聚合数据（逻辑一致）
                        trend_data = pd.DataFrame()
                        if len(df_trend_filtered) > 0:
                            group_cols = [COL_DELIVERY_MONTH]
                            if analysis_dimension == "货代维度":
                                group_cols.insert(1, COL_FREIGHT)
                            elif analysis_dimension == "仓库维度":
                                group_cols.insert(1, COL_WAREHOUSE)

                            if view_mode == "月份+准时状态（明细）":
                                group_cols.append(COL_DELAY_STATUS)

                            try:
                                # 订单个数
                                if COL_FBA_NO in df_trend_filtered.columns:
                                    df_count = df_trend_filtered.groupby(group_cols)[COL_FBA_NO].count().reset_index()
                                    df_count.rename(columns={COL_FBA_NO: "订单个数"}, inplace=True)
                                else:
                                    df_count = df_trend_filtered.groupby(group_cols).size().reset_index(name="订单个数")

                                # 准时率
                                df_delay = df_trend_filtered.copy()
                                df_delay["是否准时"] = df_delay[COL_DELAY_STATUS] == "提前/准时"
                                df_rate = df_delay.groupby(group_cols).agg({
                                    "是否准时": ["sum", "count"]
                                }).reset_index()
                                df_rate.columns = group_cols + ["准时订单数", "总订单数"]
                                df_rate["准时率"] = df_rate["准时订单数"] / df_rate["总订单数"].replace(0, 1)
                                df_rate = df_rate[group_cols + ["准时率"]]

                                # 差值列
                                df_diff = pd.DataFrame()
                                if COL_ABS_DIFF in df_trend_filtered.columns or COL_DIFF in df_trend_filtered.columns:
                                    agg_diff_dict = {}
                                    if COL_ABS_DIFF in df_trend_filtered.columns:
                                        agg_diff_dict[COL_ABS_DIFF] = "mean"
                                    if COL_DIFF in df_trend_filtered.columns:
                                        agg_diff_dict[COL_DIFF] = "mean"

                                    if agg_diff_dict:
                                        df_diff = df_trend_filtered.groupby(group_cols).agg(agg_diff_dict).reset_index()
                                        if COL_ABS_DIFF in df_diff.columns:
                                            df_diff.rename(columns={COL_ABS_DIFF: f"{COL_ABS_DIFF}_均值"}, inplace=True)
                                        if COL_DIFF in df_diff.columns:
                                            df_diff.rename(columns={COL_DIFF: f"{COL_DIFF}_均值"}, inplace=True)

                                # 合并
                                trend_data = pd.merge(df_count, df_rate, on=group_cols, how="inner")
                                if not df_diff.empty:
                                    trend_data = pd.merge(trend_data, df_diff, on=group_cols, how="left")

                                # 排序
                                trend_data["年月数值"] = trend_data[COL_DELIVERY_MONTH].apply(month_to_num)
                                sort_cols = ["年月数值"] + [col for col in group_cols if col != COL_DELIVERY_MONTH]
                                trend_data = trend_data.sort_values(sort_cols).drop("年月数值", axis=1)

                            except Exception as e:
                                st.error(f"数据聚合失败：{str(e)}")
                        else:
                            st.write("⚠️ 筛选后无数据")

                        # 平均值行+环比计算（逻辑一致）
                        avg_row = {}
                        df_with_avg = pd.DataFrame()
                        if len(trend_data) > 0:
                            avg_cols = ["订单个数", "准时率"]
                            if f"{COL_ABS_DIFF}_均值" in trend_data.columns:
                                avg_cols.append(f"{COL_ABS_DIFF}_均值")
                            if f"{COL_DIFF}_均值" in trend_data.columns:
                                avg_cols.append(f"{COL_DIFF}_均值")

                            avg_row = {col: "-" for col in trend_data.columns}
                            avg_row[COL_DELIVERY_MONTH] = "筛选后平均值"

                            for col in avg_cols:
                                valid_vals = trend_data[col].dropna()
                                if len(valid_vals) > 0:
                                    if col == "订单个数":
                                        avg_row[col] = round(valid_vals.mean(), 2)
                                    elif col == "准时率":
                                        avg_row[col] = round(valid_vals.mean(), 4)
                                    else:
                                        avg_row[col] = round(valid_vals.mean(), 2)
                                else:
                                    avg_row[col] = 0

                            df_with_avg = pd.concat([pd.DataFrame([avg_row]), trend_data], ignore_index=True)

                            # 环比计算（逻辑一致）
                            def calculate_monthly_diff(df, base_col, group_cols=[COL_DELIVERY_MONTH]):
                                df_data = df.iloc[1:].copy() if len(df) > 1 else df.copy()
                                if len(df_data) == 0 or base_col not in df_data.columns:
                                    return df

                                df_data["年月数值"] = df_data[COL_DELIVERY_MONTH].apply(month_to_num)
                                sort_cols = ["年月数值"] + [c for c in group_cols if c not in [COL_DELIVERY_MONTH]]
                                df_data = df_data.sort_values(sort_cols)

                                diff_group_cols = [c for c in group_cols if c not in [COL_DELIVERY_MONTH]]
                                if diff_group_cols and all(col in df_data.columns for col in diff_group_cols):
                                    df_data[f"{base_col}_环比差值"] = df_data.groupby(diff_group_cols)[base_col].diff()
                                else:
                                    df_data[f"{base_col}_环比差值"] = df_data[base_col].diff()

                                df_data[f"{base_col}_环比差值"] = df_data[f"{base_col}_环比差值"].fillna(0)

                                if len(df) > 1:
                                    df_result = pd.concat([df.iloc[0:1], df_data], ignore_index=True)
                                else:
                                    df_result = df_data
                                return df_result.drop("年月数值", axis=1)

                            for col in avg_cols:
                                if col in df_with_avg.columns:
                                    df_with_avg = calculate_monthly_diff(df_with_avg, col, group_cols)

                            # 格式化显示（逻辑一致）
                            def format_value_with_diff(main_val, diff_val, col_type, is_avg=False):
                                if is_avg:
                                    if col_type == "num":
                                        return f"<strong>{main_val:.2f}</strong>"
                                    elif col_type == "rate":
                                        return f"<strong>{main_val:.2%}</strong>"
                                    elif col_type == "diff":
                                        return f"<strong>{main_val:.2f}</strong>"
                                    else:
                                        return f"<strong>{main_val}</strong>"

                                try:
                                    if col_type == "num":
                                        main_str = f"{int(main_val)}"
                                    elif col_type == "rate":
                                        main_str = f"{main_val:.2%}"
                                    elif col_type == "diff":
                                        main_str = f"{main_val:.2f}"
                                    else:
                                        main_str = str(main_val)
                                except:
                                    main_str = "0"

                                if diff_val == 0:
                                    diff_str = ""
                                else:
                                    arrow = "↑" if diff_val > 0 else "↓"
                                    color = "red" if diff_val > 0 else "green"
                                    try:
                                        if col_type == "num":
                                            diff_val_str = f"{abs(int(diff_val))}"
                                        elif col_type == "rate":
                                            diff_val_str = f"{abs(diff_val):.2%}"
                                        elif col_type == "diff":
                                            diff_val_str = f"{abs(diff_val):.2f}"
                                        else:
                                            diff_val_str = f"{abs(diff_val)}"
                                    except:
                                        diff_val_str = "0"

                                    diff_str = f"""<span style="font-size: 0.7em; color: {color};">
                                                    {arrow}{diff_val_str}
                                                  </span>"""

                                return f"{main_str} {diff_str}" if diff_str else main_str

                            trend_display = df_with_avg.copy()
                            trend_display["is_avg"] = trend_display[COL_DELIVERY_MONTH] == "筛选后平均值"

                            # 格式化列（逻辑一致）
                            if "订单个数" in trend_display.columns and "订单个数_环比差值" in trend_display.columns:
                                trend_display["订单个数"] = trend_display.apply(
                                    lambda x: format_value_with_diff(x["订单个数"], x["订单个数_环比差值"], "num", x["is_avg"]),
                                    axis=1
                                )
                                trend_display = trend_display.drop(["订单个数_环比差值", "is_avg"], axis=1)

                            if "准时率" in trend_display.columns and "准时率_环比差值" in trend_display.columns:
                                trend_display["准时率"] = trend_display.apply(
                                    lambda x: format_value_with_diff(x["准时率"], x["准时率_环比差值"], "rate", x[COL_DELIVERY_MONTH] == "筛选后平均值"),
                                    axis=1
                                )
                                trend_display = trend_display.drop("准时率_环比差值", axis=1)

                            abs_diff_mean_col = f"{COL_ABS_DIFF}_均值"
                            if abs_diff_mean_col in trend_display.columns and f"{abs_diff_mean_col}_环比差值" in trend_display.columns:
                                trend_display[abs_diff_mean_col] = trend_display.apply(
                                    lambda x: format_value_with_diff(x[abs_diff_mean_col], x[f"{abs_diff_mean_col}_环比差值"], "diff", x[COL_DELIVERY_MONTH] == "筛选后平均值"),
                                    axis=1
                                )
                                trend_display = trend_display.drop(f"{abs_diff_mean_col}_环比差值", axis=1)

                            diff_mean_col = f"{COL_DIFF}_均值"
                            if diff_mean_col in trend_display.columns and f"{diff_mean_col}_环比差值" in trend_display.columns:
                                trend_display[diff_mean_col] = trend_display.apply(
                                    lambda x: format_value_with_diff(x[diff_mean_col], x[f"{diff_mean_col}_环比差值"], "diff", x[COL_DELIVERY_MONTH] == "筛选后平均值"),
                                    axis=1
                                )
                                trend_display = trend_display.drop(f"{diff_mean_col}_环比差值", axis=1)

                            # 生成HTML表格（仅修改标题文本）
                            st.markdown(f"#### 月份趋势分析（{analysis_dimension}）{start_month} ~ {end_month}")
                            if analysis_dimension == "货代维度" and selected_dimension:
                                st.markdown(f"**当前筛选：{selected_dimension}**")
                            elif analysis_dimension == "仓库维度" and selected_dimension:
                                st.markdown(f"**当前筛选：{selected_dimension}**")

                            # HTML样式（逻辑一致）
                            html_style = """
                            <style>
                            .trend-table-container {
                                height: 400px;
                                overflow-y: auto;
                                border: 1px solid #e0e0e0;
                                border-radius: 4px;
                                margin: 10px 0;
                            }
                            .trend-table {
                                width: 100%;
                                border-collapse: collapse;
                            }
                            .trend-table th {
                                position: sticky;
                                top: 0;
                                background-color: #f8f9fa;
                                font-weight: bold;
                                z-index: 2;
                                padding: 8px;
                                border: 1px solid #e0e0e0;
                            }
                            .avg-row td {
                                position: sticky;
                                top: 38px;
                                background-color: #fff3cd;
                                font-weight: bold;
                                z-index: 1;
                                padding: 8px;
                                border: 1px solid #e0e0e0;
                            }
                            .trend-table td {
                                padding: 8px;
                                border: 1px solid #e0e0e0;
                            }
                            </style>
                            """

                            headers = [col for col in trend_display.columns if col != "is_avg"]
                            header_html = "".join([f"<<th>{col}</</th>" for col in headers])

                            rows_html = ""
                            for idx, row in trend_display.iterrows():
                                if idx == 0:
                                    row_html = "<tr class='avg-row'>"
                                    for col in headers:
                                        row_html += f"<td>{row[col]}</td>"
                                    row_html += "</tr>"
                                else:
                                    row_html = "<tr>"
                                    for col in headers:
                                        row_html += f"<td>{row[col]}</td>"
                                    row_html += "</tr>"
                                rows_html += row_html

                            table_html = f"""
                            {html_style}
                            <div class='trend-table-container'>
                                <table class='trend-table'>
                                    <thead><tr>{header_html}</tr></thead>
                                    <tbody>{rows_html}</tbody>
                                </table>
                            </div>
                            """

                            st.markdown(table_html, unsafe_allow_html=True)

                            # 下载（仅修改文件名）
                            download_suffix = f"_{selected_dimension}" if selected_dimension else ""
                            download_filename = f"空派{analysis_dimension}_月份趋势{download_suffix}_{start_month}_{end_month}.xlsx"  # 红单→空派
                            st.markdown(
                                generate_download_link(df_with_avg, download_filename, "📥 下载趋势数据（含平均值）"),
                                unsafe_allow_html=True
                            )
                        else:
                            st.write("⚠️ 筛选后无数据")
                    else:
                        st.write("⚠️ 请选择有效的月份范围")

                # 右侧：折线图（逻辑一致，仅修改标题文本）
                with col2:
                    st.markdown(f"#### 空派趋势折线图（{analysis_dimension}）")  # 红单→空派
                    if analysis_dimension == "货代维度" and selected_dimension:
                        st.markdown(f"**当前筛选：{selected_dimension}**")
                    elif analysis_dimension == "仓库维度" and selected_dimension:
                        st.markdown(f"**当前筛选：{selected_dimension}**")

                    if 'trend_data' in locals() and isinstance(trend_data, pd.DataFrame) and len(trend_data) > 0 and start_month and end_month:
                        required_cols_base = [COL_DELIVERY_MONTH]
                        if analysis_dimension == "货代维度" and COL_FREIGHT in trend_data.columns:
                            required_cols_base.append(COL_FREIGHT)
                        elif analysis_dimension == "仓库维度" and COL_WAREHOUSE in trend_data.columns:
                            required_cols_base.append(COL_WAREHOUSE)

                        required_cols_extra = [
                            "准时率",
                            f"{COL_ABS_DIFF}_均值",
                            f"{COL_DIFF}_均值"
                        ]

                        required_cols = required_cols_base.copy()
                        for col in required_cols_extra:
                            if col in trend_data.columns:
                                required_cols.append(col)
                            else:
                                st.warning(f"⚠️ 数据中缺少列：{col}，无法绘制该指标")

                        if not set(required_cols_base).issubset(trend_data.columns):
                            st.error(f"⚠️ 缺少核心列：{required_cols_base}，无法绘制图表")
                        else:
                            chart_data = trend_data[required_cols].copy().dropna(subset=[COL_DELIVERY_MONTH])

                            abs_diff_col = f"{COL_ABS_DIFF}_均值"
                            diff_col = f"{COL_DIFF}_均值"

                            chart_data["到货年月_中文"] = chart_data[COL_DELIVERY_MONTH].apply(convert_to_chinese_month)

                            if "准时率" in chart_data.columns:
                                chart_data["准时率"] = pd.to_numeric(chart_data["准时率"], errors='coerce').fillna(0)
                            if abs_diff_col in chart_data.columns:
                                chart_data[abs_diff_col] = pd.to_numeric(chart_data[abs_diff_col], errors='coerce').fillna(0).round(2)
                            if diff_col in chart_data.columns:
                                chart_data[diff_col] = pd.to_numeric(chart_data[diff_col], errors='coerce').fillna(0).round(2)

                            chart_data["年月数值"] = pd.to_datetime(chart_data[COL_DELIVERY_MONTH] + "-01", errors='coerce').dt.to_period("M")
                            chart_data = chart_data.sort_values("年月数值")

                            if view_mode == "月份汇总（无状态）":
                                plot_cols = []
                                if abs_diff_col in chart_data.columns:
                                    plot_cols.append(abs_diff_col)
                                if diff_col in chart_data.columns:
                                    plot_cols.append(diff_col)
                                if "准时率" in chart_data.columns:
                                    plot_cols.append("准时率")

                                if plot_cols:
                                    try:
                                        fig_kwargs = {
                                            "data_frame": chart_data,
                                            "x": "到货年月_中文",
                                            "y": plot_cols,
                                            "title": f"{convert_to_chinese_month(start_month)} ~ {convert_to_chinese_month(end_month)} {analysis_dimension}核心指标趋势",
                                            "labels": {"value": "数值", "variable": "指标", "到货年月_中文": "到货年月"},
                                            "markers": True,
                                            "color_discrete_map": {
                                                abs_diff_col: "red",
                                                diff_col: "green",
                                                "准时率": "blue"
                                            },
                                            "category_orders": {"到货年月_中文": chart_data["到货年月_中文"].tolist()}
                                        }

                                        if analysis_dimension == "货代维度" and COL_FREIGHT in chart_data.columns:
                                            fig_kwargs["color"] = COL_FREIGHT
                                            fig_kwargs["line_dash"] = COL_FREIGHT
                                        elif analysis_dimension == "仓库维度" and COL_WAREHOUSE in chart_data.columns:
                                            fig_kwargs["color"] = COL_WAREHOUSE
                                            fig_kwargs["line_dash"] = COL_WAREHOUSE

                                        fig_trend = px.line(**fig_kwargs)

                                        # 标注（逻辑一致）
                                        for idx, row in chart_data.iterrows():
                                            x_val = row["到货年月_中文"]

                                            dim_name = ""
                                            if analysis_dimension == "货代维度" and COL_FREIGHT in row:
                                                dim_name = row[COL_FREIGHT]
                                            elif analysis_dimension == "仓库维度" and COL_WAREHOUSE in row:
                                                dim_name = row[COL_WAREHOUSE]

                                            if abs_diff_col in chart_data.columns:
                                                y_abs = row[abs_diff_col]
                                                fig_trend.add_annotation(
                                                    x=x_val,
                                                    y=y_abs,
                                                    text=f"{dim_name}<br/>{y_abs:.2f}" if dim_name else f"{y_abs:.2f}",
                                                    showarrow=True,
                                                    arrowhead=1,
                                                    ax=0,
                                                    ay=-20,
                                                    font={"size": 8, "color": "red"},
                                                    bgcolor="rgba(255,255,255,0.8)"
                                                )

                                            if diff_col in chart_data.columns:
                                                y_diff = row[diff_col]
                                                fig_trend.add_annotation(
                                                    x=x_val,
                                                    y=y_diff,
                                                    text=f"{dim_name}<br/>{y_diff:.2f}" if dim_name else f"{y_diff:.2f}",
                                                    showarrow=True,
                                                    arrowhead=1,
                                                    ax=0,
                                                    ay=-40,
                                                    font={"size": 8, "color": "green"},
                                                    bgcolor="rgba(255,255,255,0.8)"
                                                )

                                            if "准时率" in chart_data.columns:
                                                y_rate = row["准时率"]
                                                fig_trend.add_annotation(
                                                    x=x_val,
                                                    y=y_rate,
                                                    text=f"{dim_name}<br/>{y_rate * 100:.1f}%" if dim_name else f"{y_rate * 100:.1f}%",
                                                    showarrow=True,
                                                    arrowhead=1,
                                                    ax=0,
                                                    ay=-60,
                                                    font={"size": 8, "color": "blue"},
                                                    bgcolor="rgba(255,255,255,0.8)"
                                                )

                                        # 平均值参考线（逻辑一致）
                                        if 'avg_row' in locals() and len(avg_row) > 0:
                                            if abs_diff_col in chart_data.columns:
                                                avg_abs = float(avg_row.get(abs_diff_col, 0))
                                                if avg_abs != 0:
                                                    fig_trend.add_hline(
                                                        y=avg_abs,
                                                        line_dash="dash",
                                                        line_color="red",
                                                        annotation_text=f"绝对值均值: {avg_abs:.2f}",
                                                        annotation_position="right"
                                                    )

                                            if diff_col in chart_data.columns:
                                                avg_diff = float(avg_row.get(diff_col, 0))
                                                if avg_diff != 0:
                                                    fig_trend.add_hline(
                                                        y=avg_diff,
                                                        line_dash="dash",
                                                        line_color="green",
                                                        annotation_text=f"时效差值均值: {avg_diff:.2f}",
                                                        annotation_position="right"
                                                    )

                                            if "准时率" in chart_data.columns:
                                                avg_rate = float(avg_row.get("准时率", 0))
                                                if avg_rate != 0:
                                                    fig_trend.add_hline(
                                                        y=avg_rate,
                                                        line_dash="dash",
                                                        line_color="blue",
                                                        annotation_text=f"准时率均值: {avg_rate * 100:.1f}%",
                                                        annotation_position="right"
                                                    )

                                        fig_trend.update_layout(
                                            height=600,
                                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                            hovermode="x unified",
                                            yaxis=dict(rangemode="normal", fixedrange=False),
                                            xaxis=dict(
                                                tickangle=45,
                                                tickfont={"size": 10},
                                                title={"text": "到货年月", "font": {"size": 12}}
                                            )
                                        )

                                        st.plotly_chart(fig_trend, use_container_width=True)

                                    except Exception as e:
                                        st.error(f"图表生成失败：{str(e)}")
                                else:
                                    st.write("⚠️ 无可用的指标列生成折线图")
                            else:
                                st.write("⚠️ 请切换为「月份汇总（无状态）」模式查看折线图")
                    else:
                        st.write("⚠️ 请先选择有效的筛选条件并确保有数据")
        else:
            st.write("⚠️ 无有效的空派数据进行趋势分析")

        st.divider()
        # ===================== 三、空派原始数据筛选（复刻红单逻辑，仅修改列名） =====================
        st.markdown("### 📋 空派原始数据筛选查询")

        # 筛选条件（逻辑一致，仅修改key）
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            filter_month = st.multiselect(
                "筛选到货年月",
                options=sorted(df_air["到货年月"].unique()),
                default=None,
                key="air_filter_month"
            )
            filter_freight = st.multiselect(
                "筛选货代",
                options=sorted(df_air["货代"].unique()),
                default=None,
                key="air_filter_freight"
            )
        with col_filter2:
            filter_warehouse = st.multiselect(
                "筛选仓库",
                options=sorted(df_air["仓库"].unique()),
                default=None,
                key="air_filter_warehouse"
            )
            filter_status = st.multiselect(
                "筛选准时状态",
                options=["提前/准时", "延期"],
                default=None,
                key="air_filter_status"
            )
        with col_filter3:
            filter_shop = st.multiselect(
                "筛选店铺",
                options=sorted(df_air["店铺"].unique()),
                default=None,
                key="air_filter_shop"
            )
            # 新增清关耗时筛选
            st.markdown("#### 清关耗时筛选")
            customs_min = st.number_input(
                "清关耗时≥（天）",
                min_value=0,
                max_value=30,
                value=0,
                step=1,
                key="air_customs_min"
            )
            customs_max = st.number_input(
                "清关耗时≤（天）",
                min_value=0,
                max_value=30,
                value=30,
                step=1,
                key="air_customs_max"
            )

        # 应用筛选（逻辑一致，新增清关耗时过滤）
        df_filtered = df_air.copy()
        if filter_month:
            df_filtered = df_filtered[df_filtered["到货年月"].isin(filter_month)]
        if filter_freight:
            df_filtered = df_filtered[df_filtered["货代"].isin(filter_freight)]
        if filter_warehouse:
            df_filtered = df_filtered[df_filtered["仓库"].isin(filter_warehouse)]
        if filter_status:
            df_filtered = df_filtered[df_filtered["提前/延期"].isin(filter_status)]
        if filter_shop:
            df_filtered = df_filtered[df_filtered["店铺"].isin(filter_shop)]
        # 清关耗时筛选
        if "清关耗时" in df_filtered.columns:
            df_filtered["清关耗时_numeric"] = pd.to_numeric(df_filtered["清关耗时"], errors='coerce')
            df_filtered = df_filtered[
                (df_filtered["清关耗时_numeric"] >= customs_min) &
                (df_filtered["清关耗时_numeric"] <= customs_max)
            ]
            df_filtered = df_filtered.drop("清关耗时_numeric", axis=1)

        # 显示列配置（适配空派列名）
        avg_target_cols = [
            "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架",
            "签收-发货时间", "上架完成-发货时间",
            abs_col, diff_col
        ]
        display_cols = [
            "到货年月", "FBA号", "店铺", "仓库", "货代", "提前/延期",
            "异常备注", "清关耗时", "发货-起飞", "到港-提取", "提取-签收",
            "签收-完成上架", "发货-签收", "发货-完成上架",
            "签收-发货时间", "上架完成-发货时间",
            abs_col, diff_col
        ]
        display_cols = [col for col in display_cols if col in df_filtered.columns]

        # 初始化平均值
        avg_row = {col: "-" for col in display_cols}
        if len(df_filtered) > 0:
            for col in avg_target_cols:
                if col in display_cols and col != "清关耗时":  # 清关耗时不计算均值
                    numeric_vals = pd.to_numeric(df_filtered[col], errors='coerce').dropna()
                    avg_row[col] = round(numeric_vals.mean(), 2) if len(numeric_vals) > 0 else 0.00

        # 处理数据行
        df_display = df_filtered[display_cols].copy() if len(df_filtered) > 0 else pd.DataFrame(columns=display_cols)
        for col in avg_target_cols:
            if col in df_display.columns and col != "清关耗时":
                df_display[col] = pd.to_numeric(df_display[col], errors='coerce')

        # 生成表格（复刻红单样式，新增清关耗时高亮）
        st.markdown("### 空派原始数据（含筛选后平均值）")

        # 列宽配置（适配空派列名）
        col_width_config = {
            "到货年月": "80px", "FBA号": "120px", "店铺": "80px", "仓库": "80px",
            "货代": "80px", "提前/延期": "80px", "异常备注": "100px", "清关耗时": "80px",
            "发货-起飞": "80px", "到港-提取": "80px", "提取-签收": "80px",
            "签收-完成上架": "100px", "发货-签收": "80px", "发货-完成上架": "100px",
            "签收-发货时间": "100px", "上架完成-发货时间": "120px",
            abs_col: "150px", diff_col: "150px"
        }

        # CSS样式（新增清关耗时高亮类）
        table_css = """
        <style>
        .table-outer {
            width: 100%;
            border: 1px solid #dee2e6;
            margin: 10px 0;
            font-size: 14px;
        }
        .table-fixed {
            position: sticky;
            top: 0;
            background: white;
            z-index: 99;
        }
        .table-header th {
            width: var(--col-width);
            max-width: var(--col-width);
            min-width: var(--col-width);
            padding: 8px 12px;
            border: 1px solid #dee2e6;
            background: #e9ecef;
            font-weight: bold;
            text-align: left;
            white-space: normal;
            word-wrap: break-word;
            vertical-align: top;
        }
        .table-avg td {
            width: var(--col-width);
            max-width: var(--col-width);
            min-width: var(--col-width);
            padding: 8px 12px;
            border: 1px solid #dee2e6;
            background: #fff3cd;
            font-weight: bold;
            text-align: left;
            white-space: normal;
            word-wrap: break-word;
            vertical-align: top;
        }
        .table-scroll {
            height: 400px;
            overflow-y: auto;
            overflow-x: hidden;
        }
        .table-data td {
            width: var(--col-width);
            max-width: var(--col-width);
            min-width: var(--col-width);
            padding: 8px 12px;
            border: 1px solid #dee2e6;
            text-align: left;
            white-space: normal;
            word-wrap: break-word;
            vertical-align: top;
        }
        .highlight {
            background-color: #ffebee !important;
        }
        .customs-highlight {
            background-color: #ffcccc !important;
        }
        .table-header, .table-avg, .table-data {
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            border-spacing: 0;
        }
        </style>
        """

        # 构建表头
        header_html = "<table class='table-header'><tr>"
        for col in display_cols:
            width = col_width_config.get(col, "100px")
            header_html += f"<th style='--col-width: {width}'>{col}</th>"
        header_html += "</tr></table>"

        # 构建平均值行
        avg_html = "<table class='table-avg'><tr>"
        for col in display_cols:
            width = col_width_config.get(col, "100px")
            val = avg_row[col]
            if col in avg_target_cols and isinstance(val, (int, float)) and col != "清关耗时":
                val = f"{val:.2f}"
            avg_html += f"<td style='--col-width: {width}'>{val}</td>"
        avg_html += "</tr></table>"

        # 构建数据行（新增清关耗时高亮）
        data_html = "<table class='table-data'><tbody>"
        if len(df_display) > 0:
            for _, row in df_display.iterrows():
                data_html += "<tr>"
                for col in display_cols:
                    width = col_width_config.get(col, "100px")
                    val = row[col]
                    # 核心指标高亮（大于均值）
                    highlight = "highlight" if (
                        col in avg_target_cols and pd.notna(val) and pd.notna(avg_row[col]) and
                        isinstance(avg_row[col], (int, float)) and float(val) > avg_row[col]
                    ) else ""
                    # 清关耗时高亮（≥1天）
                    customs_highlight = "customs-highlight" if (
                        col == "清关耗时" and pd.notna(val) and
                        isinstance(val, (int, float)) and float(val) >= 1
                    ) else ""
                    # 合并高亮类
                    final_highlight = f"{highlight} {customs_highlight}".strip()
                    # 格式化显示值
                    display_val = ""
                    if pd.isna(val):
                        display_val = ""
                    elif col in avg_target_cols and isinstance(val, (int, float)) and col != "清关耗时":
                        display_val = f"{val:.2f}"
                    elif col == "清关耗时" and isinstance(val, (int, float)):
                        display_val = f"{val:.2f}"
                    else:
                        display_val = str(val)
                    # 拼接单元格
                    data_html += f"<td style='--col-width: {width}' class='{final_highlight}'>{display_val}</td>"
                data_html += "</tr>"
        else:
            data_html += f"<tr><td colspan='{len(display_cols)}' style='text-align: center; padding: 20px;'>⚠️ 暂无符合筛选条件的数据</td></tr>"
        data_html += "</tbody></table>"

        # 拼接HTML
        final_html = f"""
        {table_css}
        <div class='table-outer'>
            <div class='table-fixed'>
                {header_html}
                {avg_html}
            </div>
            <div class='table-scroll'>
                {data_html}
            </div>
        </div>
        """

        st.markdown(final_html, unsafe_allow_html=True)

        # 数据量提示
        if len(df_filtered) > 0:
            st.caption(f"当前筛选结果共 {len(df_filtered)} 条数据 | 总数据量：{len(df_air)} 条")
        else:
            st.caption("⚠️ 暂无符合筛选条件的空派业务数据")

        # 下载筛选后数据（仅修改文件名）
        if len(df_filtered) > 0:
            st.markdown(
                generate_download_link(
                    df_filtered,
                    "空派筛选数据.xlsx",
                    "📥 下载当前筛选结果（Excel格式）"
                ),
                unsafe_allow_html=True
            )

