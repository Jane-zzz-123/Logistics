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
    # ---------------------- 货代准时情况分析 ----------------------
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
    # ---------------------- 仓库准时情况分析 ----------------------
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

    # ====================== 不同月份红单趋势分析 ======================
    st.markdown("### 不同月份红单趋势分析")

    # 增加异常处理：检查df_red是否有效
    if isinstance(df_red, pd.DataFrame) and "到货年月" in df_red.columns and "提前/延期" in df_red.columns and len(
            df_red) > 0:
        col1, col2 = st.columns(2)

        # ====================== 左侧：月份趋势分析表格 ======================
        with col1:
            # 1. 月份范围筛选控件（下拉选择）
            st.markdown("#### 分析条件设置")
            # 获取所有唯一的到货年月并排序
            all_months_trend = sorted(df_red["到货年月"].unique())
            if len(all_months_trend) >= 2:
                default_start = all_months_trend[-3] if len(all_months_trend) >= 3 else all_months_trend[0]
                default_end = all_months_trend[-1]
            else:
                default_start = default_end = all_months_trend[0] if all_months_trend else None

            # 月份范围选择器（增加空值判断）
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
                start_month = end_month = ""
                st.write("⚠️ 无可用月份数据")

            # 筛选维度（全部/仅提前/仅延期）
            delay_filter = st.radio(
                "订单状态筛选",
                options=["全部订单", "仅提前/准时", "仅延期"],
                horizontal=True,
                key="trend_delay_filter"
            )

            # 显示模式（汇总/明细）
            view_mode = st.radio(
                "表格显示模式",
                options=["月份汇总（无状态）", "月份+准时状态（明细）"],
                horizontal=True,
                key="trend_view_mode"
            )

            # 2. 数据过滤（增加空值判断）
            if start_month and end_month:
                # 转换为可比较的格式（如202510）
                def month_to_num(month_str):
                    try:
                        return int(month_str.replace("-", ""))
                    except:
                        return 0


                # 筛选月份范围内的数据
                df_trend_filtered = df_red[
                    (df_red["到货年月"].apply(month_to_num) >= month_to_num(start_month)) &
                    (df_red["到货年月"].apply(month_to_num) <= month_to_num(end_month))
                    ].copy()

                # 筛选订单状态
                if delay_filter == "仅提前/准时":
                    df_trend_filtered = df_trend_filtered[df_trend_filtered["提前/延期"] == "提前/准时"].copy()
                elif delay_filter == "仅延期":
                    df_trend_filtered = df_trend_filtered[df_trend_filtered["提前/延期"] == "延期"].copy()

                # 3. 定义差值列
                abs_diff_col = "预计物流时效-实际物流时效差值(绝对值)"
                diff_col = "预计物流时效-实际物流时效差值"

                # 4. 数据聚合
                if view_mode == "月份汇总（无状态）" and len(df_trend_filtered) > 0:
                    # 4.1 月份汇总（无状态维度）
                    trend_data = df_trend_filtered.groupby("到货年月").agg(
                        订单个数=("FBA号", "count"),
                        准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                        **{
                            f"{abs_diff_col}_均值": (abs_diff_col,
                                                     "mean") if abs_diff_col in df_trend_filtered.columns else 0,
                            f"{diff_col}_均值": (diff_col, "mean") if diff_col in df_trend_filtered.columns else 0
                        }
                    ).reset_index()

                    # 按月份排序
                    trend_data["年月数值"] = trend_data["到货年月"].apply(month_to_num)
                    trend_data = trend_data.sort_values("年月数值").drop("年月数值", axis=1)

                elif len(df_trend_filtered) > 0:
                    # 4.2 月份+准时状态明细
                    trend_data = df_trend_filtered.groupby(["到货年月", "提前/延期"]).agg(
                        订单个数=("FBA号", "count"),
                        准时率=("提前/延期", lambda x: (x == "提前/准时").sum() / len(x) if len(x) > 0 else 0),
                        **{
                            f"{abs_diff_col}_均值": (abs_diff_col,
                                                     "mean") if abs_diff_col in df_trend_filtered.columns else 0,
                            f"{diff_col}_均值": (diff_col, "mean") if diff_col in df_trend_filtered.columns else 0
                        }
                    ).reset_index()

                    # 按月份+状态排序
                    trend_data["年月数值"] = trend_data["到货年月"].apply(month_to_num)
                    trend_data = trend_data.sort_values(["年月数值", "提前/延期"]).drop("年月数值", axis=1)
                else:
                    trend_data = pd.DataFrame()
                    st.write("⚠️ 筛选后无数据")

                # 5. 计算筛选后整体平均值（核心功能）
                if len(trend_data) > 0:
                    avg_row = {}
                    # 定义需要计算平均值的列
                    avg_cols = ["订单个数", "准时率", f"{abs_diff_col}_均值", f"{diff_col}_均值"]

                    for col in trend_data.columns:
                        if col == "到货年月":
                            avg_row[col] = "筛选后平均值"
                        elif col == "提前/延期":
                            avg_row[col] = "-"
                        elif col in avg_cols:
                            # 计算筛选后所有数据的平均值
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
                        else:
                            avg_row[col] = "-"

                    # 将平均值行插入到表格顶部
                    df_with_avg = pd.concat([pd.DataFrame([avg_row]), trend_data], ignore_index=True)


                    # 6. 计算环比差值（与上月对比）
                    def calculate_monthly_diff(df, base_col, group_cols=["到货年月"]):
                        """计算环比差值"""
                        # 复制数据避免修改原数据（跳过平均值行）
                        df_data = df.iloc[1:].copy() if len(df) > 1 else df.copy()
                        if len(df_data) == 0:
                            return df

                        # 按分组列排序
                        df_data["年月数值"] = df_data["到货年月"].apply(month_to_num)
                        df_data = df_data.sort_values(["年月数值"] + group_cols[1:])

                        # 计算环比差值
                        if view_mode == "月份汇总（无状态）":
                            df_data[f"{base_col}_环比差值"] = df_data[base_col].diff()
                        else:
                            # 按状态分组计算环比
                            df_data[f"{base_col}_环比差值"] = df_data.groupby("提前/延期")[base_col].diff()

                        # 填充第一个月的差值（无上月）
                        df_data[f"{base_col}_环比差值"] = df_data[f"{base_col}_环比差值"].fillna(0)

                        # 合并平均值行和数据行
                        if len(df) > 1:
                            df_result = pd.concat([df.iloc[0:1], df_data], ignore_index=True)
                        else:
                            df_result = df_data
                        return df_result.drop("年月数值", axis=1)


                    # 对核心列计算环比
                    for col in avg_cols:
                        if col in df_with_avg.columns:
                            df_with_avg = calculate_monthly_diff(df_with_avg, col)


                    # 7. 格式化显示（主值+环比差值小字体+箭头 + 平均值行）
                    def format_value_with_diff(main_val, diff_val, col_type, is_avg=False):
                        """
                        格式化值：主值 + 环比差值（小字体+箭头+颜色）
                        col_type: num(个数)/rate(准时率)/diff(差值)
                        is_avg: 是否是平均值行
                        """
                        # 平均值行特殊处理
                        if is_avg:
                            if col_type == "num":
                                return f"<strong>{main_val:.2f}</strong>"
                            elif col_type == "rate":
                                return f"<strong>{main_val:.2%}</strong>"
                            elif col_type == "diff":
                                return f"<strong>{main_val:.2f}</strong>"
                            else:
                                return f"<strong>{main_val}</strong>"

                        # 普通行主值格式化
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

                        # 环比差值格式化（小字体+箭头）
                        if diff_val == 0:
                            diff_str = ""
                        else:
                            # 箭头和颜色：上升(red)/下降(green)
                            if diff_val > 0:
                                arrow = "↑"
                                color = "red"
                            else:
                                arrow = "↓"
                                color = "green"

                            # 差值数值格式化
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


                    # 8. 生成带环比+平均值的表格数据
                    trend_display = df_with_avg.copy()

                    # 标记是否是平均值行
                    trend_display["is_avg"] = trend_display["到货年月"] == "筛选后平均值"

                    # 格式化订单个数
                    if "订单个数" in trend_display.columns and "订单个数_环比差值" in trend_display.columns:
                        trend_display["订单个数"] = trend_display.apply(
                            lambda x: format_value_with_diff(x["订单个数"], x["订单个数_环比差值"], "num", x["is_avg"]),
                            axis=1
                        )
                        trend_display = trend_display.drop(["订单个数_环比差值", "is_avg"], axis=1)

                    # 格式化准时率
                    if "准时率" in trend_display.columns and "准时率_环比差值" in trend_display.columns:
                        trend_display["准时率"] = trend_display.apply(
                            lambda x: format_value_with_diff(x["准时率"], x["准时率_环比差值"], "rate",
                                                             x["到货年月"] == "筛选后平均值"),
                            axis=1
                        )
                        trend_display = trend_display.drop("准时率_环比差值", axis=1)

                    # 格式化绝对值差值均值
                    abs_diff_mean_col = f"{abs_diff_col}_均值"
                    if abs_diff_mean_col in trend_display.columns and f"{abs_diff_mean_col}_环比差值" in trend_display.columns:
                        trend_display[abs_diff_mean_col] = trend_display.apply(
                            lambda x: format_value_with_diff(x[abs_diff_mean_col], x[f"{abs_diff_mean_col}_环比差值"],
                                                             "diff", x["到货年月"] == "筛选后平均值"),
                            axis=1
                        )
                        trend_display = trend_display.drop(f"{abs_diff_mean_col}_环比差值", axis=1)

                    # 格式化时效差值均值
                    diff_mean_col = f"{diff_col}_均值"
                    if diff_mean_col in trend_display.columns and f"{diff_mean_col}_环比差值" in trend_display.columns:
                        trend_display[diff_mean_col] = trend_display.apply(
                            lambda x: format_value_with_diff(x[diff_mean_col], x[f"{diff_mean_col}_环比差值"], "diff",
                                                             x["到货年月"] == "筛选后平均值"),
                            axis=1
                        )
                        trend_display = trend_display.drop(f"{diff_mean_col}_环比差值", axis=1)

                    # 9. 生成带固定平均值行的HTML表格
                    st.markdown(f"#### 月份趋势分析（{start_month} ~ {end_month}）")

                    # 构建表格HTML
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

                    # 生成表头
                    headers = [col for col in trend_display.columns if col != "is_avg"]
                    header_html = "".join([f"<th>{col}</th>" for col in headers])

                    # 生成行数据
                    rows_html = ""
                    for idx, row in trend_display.iterrows():
                        if idx == 0:  # 平均值行
                            row_html = "<tr class='avg-row'>"
                            for col in headers:
                                row_html += f"<td>{row[col]}</td>"
                            row_html += "</tr>"
                        else:  # 普通数据行
                            row_html = "<tr>"
                            for col in headers:
                                row_html += f"<td>{row[col]}</td>"
                            row_html += "</tr>"
                        rows_html += row_html

                    # 完整HTML
                    table_html = f"""
                    {html_style}
                    <div class='trend-table-container'>
                        <table class='trend-table'>
                            <thead><tr>{header_html}</tr></thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                    </div>
                    """

                    # 渲染表格
                    st.markdown(table_html, unsafe_allow_html=True)


                    # 10. 下载功能
                    def generate_trend_download_link(df, filename, link_text):
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='月份趋势')
                        output.seek(0)
                        b64 = base64.b64encode(output.read()).decode()
                        return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{link_text}</a>'


                    # 下载包含平均值的原始数据
                    download_filename = f"月份红单趋势_{start_month}_{end_month}_{view_mode.replace('（', '').replace('）', '').replace(' ', '')}.xlsx"
                    st.markdown(
                        generate_trend_download_link(df_with_avg, download_filename, "📥 下载趋势数据（含平均值）"),
                        unsafe_allow_html=True
                    )
                else:
                    st.write("⚠️ 筛选后无数据")

            else:
                st.write("⚠️ 请选择有效的月份范围")

        # ====================== 右侧：联动折线图 ======================
        # ====================== 右侧：联动折线图（修复版） ======================
        with col2:
            st.markdown("#### 红单趋势折线图")

            # 强化数据校验：检查所有必要条件
            if 'trend_data' in locals() and isinstance(trend_data, pd.DataFrame) and len(
                    trend_data) > 0 and start_month and end_month:
                # 1. 准备图表数据（排除空值，强制转换数值类型）
                chart_data = trend_data.copy().dropna()


                # 2. 月份转换并排序（增加异常处理）
                def safe_month_to_num(month_str):
                    """安全的月份转换函数"""
                    try:
                        return int(month_str.replace("-", ""))
                    except:
                        return 0


                chart_data["年月数值"] = chart_data["到货年月"].apply(safe_month_to_num)
                chart_data = chart_data.sort_values("年月数值")

                # 3. 汇总模式折线图（修复核心）
                if view_mode == "月份汇总（无状态）":
                    # 筛选有效数值列，排除非数值数据
                    valid_y_cols = []
                    if "订单个数" in chart_data.columns:
                        # 强制转换为数值类型
                        chart_data["订单个数"] = pd.to_numeric(chart_data["订单个数"], errors='coerce').fillna(0)
                        if chart_data["订单个数"].sum() > 0:  # 确保有有效数据
                            valid_y_cols.append("订单个数")

                    if "准时率" in chart_data.columns:
                        chart_data["准时率"] = pd.to_numeric(chart_data["准时率"], errors='coerce').fillna(0)
                        if chart_data["准时率"].sum() > 0:
                            valid_y_cols.append("准时率")

                    abs_diff_mean_col = f"{abs_diff_col}_均值"
                    if abs_diff_mean_col in chart_data.columns:
                        chart_data[abs_diff_mean_col] = pd.to_numeric(chart_data[abs_diff_mean_col],
                                                                      errors='coerce').fillna(0)
                        if chart_data[abs_diff_mean_col].sum() > 0:
                            valid_y_cols.append(abs_diff_mean_col)

                    # 只有存在有效列时才生成图表
                    if valid_y_cols:
                        try:
                            fig_trend = px.line(
                                chart_data,
                                x="到货年月",
                                y=valid_y_cols,
                                title=f"{start_month} ~ {end_month} 红单核心指标趋势",
                                labels={"value": "数值", "variable": "指标"},
                                marker=True,
                                # 增加数据校验：确保x轴有值
                                category_orders={"到货年月": sorted(chart_data["到货年月"].unique())}
                            )

                            # 添加平均值参考线（增加异常处理）
                            if 'avg_row' in locals():
                                for col in valid_y_cols:
                                    try:
                                        avg_val = float(avg_row.get(col, 0))
                                        if avg_val != 0:
                                            annotation_text = f"平均值: {avg_val:.2f}" if col != "准时率" else f"平均值: {avg_val:.2%}"
                                            fig_trend.add_hline(
                                                y=avg_val,
                                                line_dash="dash",
                                                line_color="orange",
                                                annotation_text=annotation_text,
                                                annotation_position="right"
                                            )
                                    except:
                                        pass

                            # 图表样式优化
                            fig_trend.update_layout(
                                height=400,
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                hovermode="x unified"
                            )

                            # 显示图表
                            st.plotly_chart(fig_trend, use_container_width=True)
                        except Exception as e:
                            st.error(f"图表生成失败：{str(e)}")
                    else:
                        st.write("⚠️ 无有效数值数据生成折线图")

                # 4. 明细模式折线图（修复核心）
                else:
                    # 确保提前/延期列有值
                    if "提前/延期" in chart_data.columns and "订单个数" in chart_data.columns:
                        # 强制转换数值类型
                        chart_data["订单个数"] = pd.to_numeric(chart_data["订单个数"], errors='coerce').fillna(0)

                        # 筛选有有效订单数的数据
                        chart_data = chart_data[chart_data["订单个数"] > 0]

                        if len(chart_data) > 0:
                            try:
                                fig_trend = px.line(
                                    chart_data,
                                    x="到货年月",
                                    y="订单个数",
                                    color="提前/延期",
                                    title=f"{start_month} ~ {end_month} 各状态订单数趋势",
                                    color_discrete_map={"提前/准时": "green", "延期": "red"},
                                    marker=True,
                                    # 确保颜色映射有效
                                    category_orders={
                                        "到货年月": sorted(chart_data["到货年月"].unique()),
                                        "提前/延期": ["提前/准时", "延期"]
                                    }
                                )

                                # 按状态添加平均值参考线（增加异常处理）
                                if 'avg_row' in locals():
                                    for status in ["提前/准时", "延期"]:
                                        try:
                                            status_data = chart_data[chart_data["提前/延期"] == status]
                                            if len(status_data) > 0:
                                                status_avg = float(status_data["订单个数"].mean())
                                                if status_avg > 0:
                                                    fig_trend.add_hline(
                                                        y=status_avg,
                                                        line_dash="dash",
                                                        line_color="green" if status == "提前/准时" else "red",
                                                        annotation_text=f"{status}平均值: {status_avg:.0f}",
                                                        annotation_position="right"
                                                    )
                                        except:
                                            pass

                                # 图表样式优化
                                fig_trend.update_layout(
                                    height=400,
                                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                    hovermode="x unified"
                                )

                                # 显示图表
                                st.plotly_chart(fig_trend, use_container_width=True)
                            except Exception as e:
                                st.error(f"图表生成失败：{str(e)}")
                        else:
                            st.write("⚠️ 无有效订单数据生成折线图")
                    else:
                        st.write("⚠️ 缺少「提前/延期」或「订单个数」列")
            else:
                st.write("⚠️ 请先选择有效的筛选条件并确保有数据")

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