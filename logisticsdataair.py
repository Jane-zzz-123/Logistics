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
    page_title="空派物流交期分析看板",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------- 数据读取与预处理 ----------------------
@st.cache_data
def load_data():
    """读取空派数据并预处理"""
    # 读取指定sheet
    url = "https://github.com/Jane-zzz-123/Logistics/raw/main/Logisticsdata.xlsx"
    df_air = pd.read_excel(url, sheet_name="上架完成-空运")

    # 指定需要分析的列
    target_cols = [
        "FBA号", "店铺", "仓库", "货代", "异常备注",
        "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架",
        "发货-签收", "发货-完成上架","清关耗时", "到货年月",
        "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)",
        "预计物流时效-实际物流时效差值", "提前/延期"
        "预计物流时效-实际物流时效差值（货代）","提前/延期（货代）","提前/延期（仓库）"
    ]

    # 确保只保留目标列（处理列名可能的空格/大小写问题）
    df_air = df_air[[col for col in target_cols if col in df_air.columns]]

    # 数据类型处理
    df_air["到货年月"] = pd.to_datetime(df_air["到货年月"], errors='coerce').dt.strftime("%Y-%m")
    df_air = df_air.dropna(subset=["到货年月"])  # 去除到货年月为空的数据

    # 数值列处理
    numeric_cols = [
        "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)",
        "预计物流时效-实际物流时效差值",
        "预计物流时效-实际物流时效差值（货代）"
    ]
    for col in numeric_cols:
        if col in df_air.columns:
            df_air[col] = pd.to_numeric(df_air[col], errors='coerce').fillna(0)

    return df_air


# 加载数据
df_air = load_data()


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
st.title("📦 空派分析看板区域")
st.divider()

# ===================== 一、当月的情况 =====================
st.subheader("🔍 当月空派分析")

# 时间筛选器（到货年月，最新的在最上方）
month_options = sorted(df_air["到货年月"].unique(), reverse=True) if len(df_air["到货年月"].unique()) > 0 else []
selected_month = st.selectbox(
    "选择到货年月",
    options=month_options,
    index=0 if month_options else None,
    key="month_selector_current"
) if month_options else st.write("⚠️ 暂无可用的到货年月数据")

# 筛选当月数据
if month_options and selected_month:
    df_current = df_air[df_air["到货年月"] == selected_month].copy()
    # 获取上月数据
    prev_month = get_prev_month(selected_month)
    df_prev = df_air[
        df_air["到货年月"] == prev_month].copy() if prev_month and prev_month in month_options else pd.DataFrame()

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
    # ========== 新增：6. 准时率（核心修改1） ==========
    # 当月准时率（提前/准时数 ÷ 总FBA数 × 100%）
    current_on_time_rate = (current_on_time / current_fba * 100) if current_fba > 0 else 0.0
    # 上月准时率
    prev_on_time_rate = (prev_on_time / prev_fba * 100) if prev_fba > 0 else 0.0
    # 准时率环比变化（百分点）
    on_time_rate_change = current_on_time_rate - prev_on_time_rate
    # 准时率变化文本（和其他指标样式统一）
    on_time_rate_change_text = f"{'↑' if on_time_rate_change > 0 else '↓' if on_time_rate_change < 0 else '—'} {abs(on_time_rate_change):.1f}% (上月: {prev_on_time_rate:.1f}%)"
    # 准时率变化颜色（红升绿降）
    on_time_rate_change_color = "red" if on_time_rate_change > 0 else "green" if on_time_rate_change < 0 else "gray"

    # 显示卡片（一行六列）- 改用HTML自定义样式（核心修改2：从5列改为6列）
    col1, col2, col3, col4, col5, col6 = st.columns(6)

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
    # ========== 新增：第6列 准时率卡片（核心修改3） ==========
    with col6:
        st.markdown(f"""
        <div style='background-color: #e8f4f8; padding: 15px; border-radius: 8px; text-align: center;'>
            <h5 style='margin: 0; color: #2196f3;'>准时率</h5>
            <p style='font-size: 24px; margin: 8px 0; font-weight: bold;'>{current_on_time_rate:.1f}%</p>
            <p style='font-size: 14px; color: {on_time_rate_change_color}; margin: 0;'>{on_time_rate_change_text}</p>
        </div>
        """, unsafe_allow_html=True)
    # 计算辅助指标（业务视角）
    total_orders = current_fba
    on_time_rate = (current_on_time / total_orders * 100) if total_orders > 0 else 0  # 准时率
    delay_rate = (current_delay / total_orders * 100) if total_orders > 0 else 0  # 延期率
    prev_on_time_rate = (prev_on_time / prev_fba * 100) if prev_fba > 0 else 0  # 上月准时率
    on_time_rate_change = on_time_rate - prev_on_time_rate  # 准时率变化

    # 核心结论（先给定性判断）
    if on_time_rate >= 90:
        core_conclusion = f"{selected_month}空派物流整体表现优秀，准时率达{on_time_rate:.1f}%，远高于行业基准"
    elif on_time_rate >= 80:
        core_conclusion = f"{selected_month}空派物流表现良好，准时率{on_time_rate:.1f}%，整体可控"
    elif on_time_rate >= 70:
        core_conclusion = f"{selected_month}空派物流表现一般，准时率{on_time_rate:.1f}%，需关注延期问题"
    else:
        core_conclusion = f"{selected_month}空派物流表现较差，准时率仅{on_time_rate:.1f}%，延期风险显著"

    # 关键数据支撑（精简+业务化）
    data_support = f"""
    本月共处理FBA订单{current_fba}单（环比{'+' if fba_change > 0 else ''}{fba_change}单）：
    ✅ 提前/准时单{current_on_time}单（准时率{on_time_rate:.1f}%，环比{'↑' if on_time_rate_change > 0 else '↓'}{abs(on_time_rate_change):.1f}个百分点）；
    ❌ 延期单{current_delay}单（延期率{delay_rate:.1f}%）；
    📊 实际物流时效与预计的偏差均值为{current_diff_avg:.2f}天（绝对值均值{current_abs_avg:.2f}天），环比{'扩大' if abs_change > 0 else '收窄'}{abs(abs_change):.2f}天。
    """

    # 风险/亮点提示（针对性分析）
    tips = ""
    # 1. 准时率大幅波动提示
    if abs(on_time_rate_change) >= 5:
        if on_time_rate_change > 0:
            tips += f"💡 亮点：本月准时率环比提升{on_time_rate_change:.1f}个百分点，物流效率显著改善；"
        else:
            tips += f"⚠️ 风险：本月准时率环比下降{abs(on_time_rate_change):.1f}个百分点，需排查延期原因；"
    # 2. 延期单占比过高提示
    if delay_rate >= 30:
        tips += f"⚠️ 风险：延期单占比超30%，建议优先核查高频延期的货代/仓库；"
    # 3. 时效偏差扩大提示
    if abs_change >= 2:
        tips += f"⚠️ 风险：时效偏差绝对值环比扩大{abs_change:.2f}天，预计时效的准确性需优化；"
    # 4. 无明显风险的正向提示
    if not tips:
        tips = "💡 本月物流时效无显著异常，各维度表现稳定。"

    # 整合最终总结
    summary_text = f"""
    ### {selected_month}空派物流核心分析
    {core_conclusion}

    {data_support}

    {tips}
    """

    # 渲染总结（用markdown美化）
    st.markdown(summary_text)

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
                title=f"{selected_month} 空派准时率分布",
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
    # ---------------------- ③ 当月空派明细表格 ----------------------
    st.markdown("### 空派明细（含平均值）")

    # 准备明细数据
    detail_cols = [
        "到货年月", "提前/延期", "FBA号", "店铺", "仓库", "货代",
        # 新增的物流阶段列（加在货代右边）
        "发货-起飞", "到港-提取", "提取-签收", "清关耗时","签收-完成上架",
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
            "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架","清关耗时",
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
                df.to_excel(writer, index=False, sheet_name='空派明细')
            output.seek(0)
            b64 = base64.b64encode(output.read()).decode()

            # 生成下载链接
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
            return href


        # 显示下载按钮
        st.markdown(
            get_table_download_link(
                df_download,
                f"空派明细_{selected_month}.xlsx",
                "📥 下载空派明细表格（Excel格式）"
            ),
            unsafe_allow_html=True
        )

    else:
        st.write("⚠️ 暂无明细数据")

    st.divider()

    # ---------------------- ④ 当月货代准时情况 ----------------------
    # ---------------------- 货代准时情况分析（独立版：发货-签收环节，无仓库关联） ----------------------
    st.markdown("### 货代准时情况分析（发货-签收环节）")

    # ========== 列名映射字典（根据你的实际列名修改！）==========
    COLUMN_MAPPING = {
        "货代列名": "货代",  # 改成你数据中实际的货代列名
        "货代提前延期列名": "提前/延期（货代）",  # 改成你实际的货代提前/延期列名
        "货代时效差值列名": "预计物流时效-实际物流时效差值（货代）"  # 改成你实际的货代时效差值列名
    }

    # 筛选有效数据（仅保留有货代信息的行）
    df_freight_valid = df_current[
        df_current[COLUMN_MAPPING["货代列名"]].notna() &
        (df_current[COLUMN_MAPPING["货代列名"]] != "")
        ].copy()

    if len(df_freight_valid) == 0:
        st.warning(f"{selected_month}月暂无货代相关数据")
    else:
        # ===== 列名校验：避免KeyError =====
        required_cols = [COLUMN_MAPPING["货代列名"], COLUMN_MAPPING["货代提前延期列名"],
                         COLUMN_MAPPING["货代时效差值列名"]]
        missing_cols = [col for col in required_cols if col not in df_freight_valid.columns]
        if missing_cols:
            st.error(f"缺少货代分析必要列：{missing_cols}，请检查列名是否正确！")
            st.stop()

        # ===== 1. 货代核心指标计算 =====
        freight_stats = df_freight_valid.groupby(COLUMN_MAPPING["货代列名"]).agg(
            总订单数=(COLUMN_MAPPING["货代列名"], "count"),
            提前准时订单数=(COLUMN_MAPPING["货代提前延期列名"], lambda x: len(x[x == "提前/准时"])),
            延期订单数=(COLUMN_MAPPING["货代提前延期列名"], lambda x: len(x[x == "延期"])),
            时效差值均值=(COLUMN_MAPPING["货代时效差值列名"], "mean"),
            最大延期天数=(COLUMN_MAPPING["货代时效差值列名"], lambda x: min(x.min(), 0)),  # 仅取延期负数
            最大提前天数=(COLUMN_MAPPING["货代时效差值列名"], lambda x: max(x.max(), 0))  # 仅取提前正数
        ).reset_index()

        # 重命名货代列，方便后续使用
        freight_stats.rename(columns={COLUMN_MAPPING["货代列名"]: "货代"}, inplace=True)

        # 计算衍生指标（核心）- 统一保留2位小数
        freight_stats["准时率(%)"] = round(freight_stats["提前准时订单数"] / freight_stats["总订单数"] * 100, 2)
        freight_stats["订单量占比(%)"] = round(freight_stats["总订单数"] / len(df_freight_valid) * 100, 2)
        freight_stats["延期率(%)"] = round(100 - freight_stats["准时率(%)"], 2)

        # ===== 2. 计算上月货代准时率（调整为“准时率差值”）=====
        prev_freight_valid = df_prev[
            df_prev[COLUMN_MAPPING["货代列名"]].notna() &
            (df_prev[COLUMN_MAPPING["货代列名"]] != "")
            ].copy() if not df_prev.empty else pd.DataFrame()

        if len(prev_freight_valid) > 0:
            prev_freight_stats = prev_freight_valid.groupby(COLUMN_MAPPING["货代列名"]).agg(
                上月提前准时订单数=(COLUMN_MAPPING["货代提前延期列名"], lambda x: len(x[x == "提前/准时"])),
                上月总订单数=(COLUMN_MAPPING["货代列名"], "count")
            ).reset_index()
            prev_freight_stats.rename(columns={COLUMN_MAPPING["货代列名"]: "货代"}, inplace=True)
            prev_freight_stats["上月准时率(%)"] = round(
                prev_freight_stats["上月提前准时订单数"] / prev_freight_stats["上月总订单数"] * 100, 2)
            # 合并本月&上月数据
            freight_stats = pd.merge(freight_stats, prev_freight_stats[["货代", "上月准时率(%)"]], on="货代",
                                     how="left")
            freight_stats["准时率差值(%)"] = round(
                freight_stats["准时率(%)"] - freight_stats["上月准时率(%)"].fillna(0), 2)
        else:
            freight_stats["上月准时率(%)"] = None  # 无数据时显示空
            freight_stats["准时率差值(%)"] = None

        # ===== 3. 可视化展示（双轴图 + 所有货代迷你卡片）=====
        col1, col2 = st.columns([2, 1])
        # 3.1 左：货代订单量占比 + 准时率 双轴图（核心趋势）
        with col1:
            import plotly.graph_objects as go

            fig = go.Figure()
            # 订单量占比-柱状图
            fig.add_trace(go.Bar(
                x=freight_stats["货代"],
                y=freight_stats["订单量占比(%)"],
                name="订单量占比(%)",
                yaxis="y1",
                marker_color="#4299e1",
                opacity=0.8,
                text=freight_stats["订单量占比(%)"].apply(lambda x: f"{x:.2f}%"),  # 显示2位小数
                textposition="auto"
            ))
            # 准时率-折线图
            fig.add_trace(go.Scatter(
                x=freight_stats["货代"],
                y=freight_stats["准时率(%)"],
                name="准时率(%)",
                yaxis="y2",
                marker_color="#e53e3e",
                mode="lines+markers+text",
                line=dict(width=3),
                marker=dict(size=8),
                text=freight_stats["准时率(%)"].apply(lambda x: f"{x:.2f}%"),  # 显示2位小数
                textposition="top center"
            ))
            # 图表样式配置
            fig.update_layout(
                title=f"{selected_month} 货代订单量占比 & 准时率对比",
                yaxis=dict(title="订单量占比(%)", side="left", range=[0, 100], color="#4299e1"),
                yaxis2=dict(title="准时率(%)", side="right", overlaying="y", range=[0, 100], color="#e53e3e"),
                xaxis=dict(title="货代名称", tickangle=0),
                legend=dict(x=0.02, y=0.98, bordercolor="#eee", borderwidth=1),
                height=400,
                plot_bgcolor="#ffffff"
            )
            st.plotly_chart(fig, use_container_width=True)

        # 3.2 右：所有货代核心表现迷你卡片（适配3-4个货代，颜色分级）
        with col2:
            st.markdown("#### 货代核心表现")
            for _, row in freight_stats.iterrows():
                # 准时率颜色分级：优质≥90% | 合格80-90% | 异常<80%
                if row["准时率(%)"] >= 90:
                    card_bg = "#f0f8f0"
                    rate_color = "#2e7d32"
                    tag = "优质"
                elif row["准时率(%)"] >= 80:
                    card_bg = "#fff8e1"
                    rate_color = "#ff9800"
                    tag = "合格"
                else:
                    card_bg = "#fff0f0"
                    rate_color = "#c62828"
                    tag = "异常"
                # 准时率差值样式
                diff_val = row["准时率差值(%)"]
                if pd.notna(diff_val):
                    if diff_val > 0:
                        diff_text = f"↑{diff_val:.2f}%"
                        diff_color = "#2e7d32"
                    elif diff_val < 0:
                        diff_text = f"↓{abs(diff_val):.2f}%"
                        diff_color = "#c62828"
                    else:
                        diff_text = "—"
                        diff_color = "#757575"
                    # 上月准时率显示（无数据时隐藏）
                    prev_rate_text = f"（上月{row['上月准时率(%)']:.2f}%）" if pd.notna(row["上月准时率(%)"]) else ""
                else:
                    diff_text = "—"
                    diff_color = "#757575"
                    prev_rate_text = ""
                # 生成货代迷你卡片
                st.markdown(f"""
                <div style='background-color: {card_bg}; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid {rate_color};'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <p style='margin: 0; font-weight: bold; font-size: 16px;'>{row['货代']}</p>
                        <span style='font-size: 12px; padding: 2px 6px; border-radius: 12px; background: {rate_color}; color: white;'>{tag}</span>
                    </div>
                    <p style='margin: 6px 0 0; font-size: 14px;'>
                        准时率：<span style='color: {rate_color}; font-weight: bold; font-size: 18px;'>{row['准时率(%)']:.2f}%</span>
                    </p>
                    <p style='margin: 4px 0 0; font-size: 12px; color: #666;'>订单：{row['总订单数']}单（{row['订单量占比(%)']:.2f}%）</p>
                    <p style='margin: 4px 0 0; font-size: 12px; color: #666;'>差值：<span style='color: {diff_color}; font-weight: bold;'>{diff_text}</span> {prev_rate_text}</p>
                    <p style='margin: 4px 0 0; font-size: 12px; color: #666;'>最大延期：{abs(row['最大延期天数'])}天</p>
                </div>
                """, unsafe_allow_html=True)

        # ===== 4. 货代详细时效指标表（带上月差值对比+兼容Streamlit样式）=====
        st.markdown("#### 货代详细时效指标表")

        # ---------------------- 计算上月货代订单类指标 ----------------------
        prev_order_stats = pd.DataFrame()
        if len(prev_freight_valid) > 0:
            prev_order_stats = prev_freight_valid.groupby(COLUMN_MAPPING["货代列名"]).agg(
                上月总订单数=(COLUMN_MAPPING["货代列名"], "count"),
                上月提前准时订单数=(COLUMN_MAPPING["货代提前延期列名"], lambda x: len(x[x == "提前/准时"])),
                上月延期订单数=(COLUMN_MAPPING["货代提前延期列名"], lambda x: len(x[x == "延期"]))
            ).reset_index()
            prev_order_stats.rename(columns={COLUMN_MAPPING["货代列名"]: "货代"}, inplace=True)
            freight_stats = pd.merge(freight_stats, prev_order_stats, on="货代", how="left")
        else:
            freight_stats["上月总订单数"] = None
            freight_stats["上月提前准时订单数"] = None
            freight_stats["上月延期订单数"] = None

        # ---------------------- 格式化订单数列（纯文本兼容版） ----------------------
        display_cols = [
            "货代", "总订单数", "订单量占比(%)", "提前准时订单数", "延期订单数", "延期率(%)",
            "准时率(%)", "上月准时率(%)", "准时率差值(%)",
            "时效差值均值", "最大提前天数", "最大延期天数"
        ]
        freight_display = freight_stats[display_cols].copy()


        # 自定义格式化函数（纯文本，用[]包裹上月信息，视觉区分）
        def format_order_col(current_val, prev_val):
            """
            纯文本格式化：本月数 [差值 上月数]
            - 上月信息用[]包裹，视觉上弱化
            - 差值带正负号，无上月数据时只显示本月数
            """
            if pd.notna(prev_val):
                diff = current_val - prev_val
                diff_sign = "+" if diff > 0 else "" if diff == 0 else "-"
                diff_abs = abs(diff)
                # 用[]包裹上月信息，通过空格/符号实现视觉层次
                return f"{current_val}  [{diff_sign}{diff_abs} 上月{prev_val}]"
            else:
                return f"{current_val}"


        # 应用格式化（直接操作freight_stats的原始数值）
        freight_display["总订单数"] = freight_stats.apply(
            lambda x: format_order_col(x["总订单数"], x["上月总订单数"]), axis=1
        )
        freight_display["提前准时订单数"] = freight_stats.apply(
            lambda x: format_order_col(x["提前准时订单数"], x["上月提前准时订单数"]), axis=1
        )
        freight_display["延期订单数"] = freight_stats.apply(
            lambda x: format_order_col(x["延期订单数"], x["上月延期订单数"]), axis=1
        )

        # 其他数值格式化
        freight_display["时效差值均值"] = round(freight_display["时效差值均值"], 2)
        freight_display["最大延期天数"] = freight_display["最大延期天数"].apply(
            lambda x: f"{abs(x)}天" if x < 0 else "0天")
        freight_display["最大提前天数"] = freight_display["最大提前天数"].apply(lambda x: f"{x}天" if x > 0 else "0天")

        # 百分比列格式化
        for col in ["订单量占比(%)", "延期率(%)", "准时率(%)", "上月准时率(%)", "准时率差值(%)"]:
            freight_display[col] = freight_display[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")


        # ---------------------- 表格高亮规则 ----------------------
        def highlight_freight(row):
            styles = [""] * len(row)
            # 准时率差值为负标红
            if row["准时率差值(%)"] and isinstance(row["准时率差值(%)"], str) and float(
                    row["准时率差值(%)"].replace("%", "")) < 0:
                styles[display_cols.index(
                    "准时率差值(%)")] = "background-color: #fff5f5; color: #c62828; font-weight: bold;"
            # 延期率>20%标红
            if row["延期率(%)"] and isinstance(row["延期率(%)"], str) and float(row["延期率(%)"].replace("%", "")) > 20:
                styles[
                    display_cols.index("延期率(%)")] = "background-color: #fff5f5; color: #c62828; font-weight: bold;"
            # 准时率<80%标红
            if row["准时率(%)"] and isinstance(row["准时率(%)"], str) and float(row["准时率(%)"].replace("%", "")) < 80:
                styles[
                    display_cols.index("准时率(%)")] = "background-color: #fff5f5; color: #c62828; font-weight: bold;"
            return styles


        # ---------------------- 展示表格（移除unsafe_allow_html，兼容Streamlit） ----------------------
        styled_table = freight_display.style.apply(highlight_freight, axis=1)
        st.dataframe(
            styled_table,
            use_container_width=True,
            hide_index=True  # 移除unsafe_allow_html参数，避免TypeError
        )

        # ===== 5. 数据下载功能 =====
        # 下载数据保留原始数值（非格式化）
        download_data = freight_stats.copy()
        csv_data = download_data.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 下载货代分析完整数据",
            data=csv_data,
            file_name=f"{selected_month}_货代准时率分析数据.csv",
            mime="text/csv",
            key="freight_data_download"
        )
    # ===== 6. 货代当月表现总结文字（修复重复问题） =====
    st.markdown("### 货代当月表现总结")

    # 每次运行都重新创建空列表（避免追加重复内容）
    summary_paragraphs = []
    for _, row in freight_stats.iterrows():
        # 基础信息提取
        freight_name = row["货代"]
        order_count = row["总订单数"]
        order_ratio = row["订单量占比(%)"]
        on_time_rate = row["准时率(%)"]
        max_delay = abs(row["最大延期天数"])
        prev_rate = row["上月准时率(%)"]
        diff_val = row["准时率差值(%)"]

        # 评级判断+颜色
        if on_time_rate >= 90:
            level_tag = "【优质】"
            level_color = "#2e7d32"
            level_desc = "准时率表现优秀"
        elif on_time_rate >= 80:
            level_tag = "【合格】"
            level_color = "#ff9800"
            level_desc = "准时率表现达标"
        else:
            level_tag = "【异常】"
            level_color = "#c62828"
            level_desc = "准时率表现不达标，需重点关注"

        # 差值描述（修复无上月数据）
        if pd.notna(prev_rate):
            if diff_val > 0:
                diff_desc = f"较上月提升{diff_val:.2f}个百分点"
            elif diff_val < 0:
                diff_desc = f"较上月下降{abs(diff_val):.2f}个百分点"
            else:
                diff_desc = "与上月持平"
        else:
            diff_desc = "无上月数据对比"

        # 延期描述
        delay_desc = "全程无延期订单" if max_delay == 0 else f"最大延期天数为{max_delay}天"

        # 生成单条总结（精简HTML，避免冗余标签）
        summary = f"""
        - <b>{freight_name} <span style='color:{level_color};'>{level_tag}</span></b>：
          本月承接{order_count}单（占总订单量{order_ratio:.2f}%），{level_desc}，准时率为{on_time_rate:.2f}%，{diff_desc}，{delay_desc}。
        """
        summary_paragraphs.append(summary)

    # 清空重复内容后，只渲染一次
    st.markdown("\n".join(summary_paragraphs), unsafe_allow_html=True)


    # ===================== 三、数据源 =====================
    st.subheader("📋 数据源筛选")

    # ---------------------- 筛选器（单选+默认“全部”） ----------------------
    col1, col2, col3, col4 = st.columns(4)

    # 1. 到货年月筛选器（单选+默认“全部”）
    with col1:
        month_unique = df_air["到货年月"].dropna().unique()
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
        if "仓库" in df_air.columns:
            warehouse_unique = df_air["仓库"].dropna().unique()
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
        if "货代" in df_air.columns:
            freight_unique = df_air["货代"].dropna().unique()
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
        if "提前/延期" in df_air.columns:
            status_unique = df_air["提前/延期"].dropna().unique()
            if len(status_unique) > 0:
                status_options_filter += list(status_unique)
        selected_status_filter = st.selectbox(
            "提前/延期",
            options=status_options_filter,
            index=0,  # 默认选中“全部”
            key="filter_status_single"
        )

    # ---------------------- 应用筛选逻辑 ----------------------
    filter_conditions = pd.Series([True] * len(df_air))
    if selected_month_filter != "全部" and len(df_air) > 0:
        filter_conditions = filter_conditions & (df_air["到货年月"] == selected_month_filter)
    if "仓库" in df_air.columns and selected_warehouse_filter != "全部" and len(df_air) > 0:
        filter_conditions = filter_conditions & (df_air["仓库"] == selected_warehouse_filter)
    if "货代" in df_air.columns and selected_freight_filter != "全部" and len(df_air) > 0:
        filter_conditions = filter_conditions & (df_air["货代"] == selected_freight_filter)
    if "提前/延期" in df_air.columns and selected_status_filter != "全部" and len(df_air) > 0:
        filter_conditions = filter_conditions & (df_air["提前/延期"] == selected_status_filter)
    df_filtered = df_air[filter_conditions].copy()

    # ---------------------- 计算平均值 ----------------------
    avg_target_cols = [
        "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架",
        "发货-签收", "发货-完成上架", "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值"
    ]
    display_cols = [
        "到货年月", "FBA号", "店铺", "仓库", "货代", "提前/延期",
        "异常备注", "发货-起飞", "到港-提取", "提取-签收","清关耗时", "签收-完成上架",
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
        "货代": "80px", "提前/延期": "80px", "异常备注": "100px", "发货-起飞": "80px",
        "到港-提取": "80px", "提取-签收": "80px", "签收-完成上架": "100px", "发货-签收": "80px",
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
        st.caption(f"当前筛选结果共 {len(df_filtered)} 条数据 | 总数据量：{len(df_air)} 条")
    else:
        st.caption("⚠️ 暂无符合筛选条件的业务数据")