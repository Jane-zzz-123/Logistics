import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
import os
import sys

# ========== 基础配置和警告处理 ==========
warnings.filterwarnings('ignore')
# 基础环境配置
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

# 设置页面配置（必须在所有st.调用之前）
st.set_page_config(
    page_title="物流交期分析看板 - 红单",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------- 数据加载函数 ----------------------
@st.cache_data(show_spinner="正在加载数据...")
def load_data():
    """加载红单数据并处理列名兼容性"""
    url = "https://github.com/Jane-zzz-123/Logistics/raw/main/Logisticsdata.xlsx"
    try:
        # 读取红单sheet
        df_red = pd.read_excel(url, sheet_name="上架完成-红单")

        # 显示原始列名（调试用）
        st.sidebar.subheader("📝 数据列名信息")
        st.sidebar.write("原始列名：")
        for col in df_red.columns:
            st.sidebar.write(f"- {col}")

        # 列名清理和标准化
        df_red.columns = [col.strip() for col in df_red.columns]  # 去除首尾空格
        df_red.columns = [col.replace(" ", "") for col in df_red.columns]  # 去除中间空格

        # 定义列名映射（处理可能的列名变体）
        column_mapping = {
            "到货年月": ["到货年月", "到货月", "年月", "到货日期", "月份"],
            "提前/延期": ["提前/延期", "提前延期", "准时状态", "交期状态"],
            "预计物流时效-实际物流时效差值(绝对值)": ["预计物流时效-实际物流时效差值(绝对值)", "时效差值绝对值",
                                                      "差值绝对值"],
            "预计物流时效-实际物流时效差值": ["预计物流时效-实际物流时效差值", "时效差值", "差值"],
            "签收-发货时间": ["签收-发货时间", "签收发货时间", "签收时长"],
            "上架完成-发货时间": ["上架完成-发货时间", "上架发货时间", "上架时长"],
            "FBA号": ["FBA号", "FBA单号", "订单号"],
            "店铺": ["店铺", "店铺名称"],
            "仓库": ["仓库", "仓库名称"],
            "货代": ["货代", "货代名称", "物流公司"]
        }

        # 自动匹配列名
        matched_columns = {}
        for target_col, possible_names in column_mapping.items():
            for name in possible_names:
                if name in df_red.columns:
                    matched_columns[target_col] = name
                    break

        # 重命名列
        reverse_mapping = {v: k for k, v in matched_columns.items()}
        df_red = df_red.rename(columns=reverse_mapping)

        # 检查关键列是否存在
        required_columns = ["到货年月", "提前/延期", "预计物流时效-实际物流时效差值(绝对值)",
                            "预计物流时效-实际物流时效差值"]
        missing_cols = [col for col in required_columns if col not in df_red.columns]

        if missing_cols:
            st.sidebar.error(f"⚠️ 缺少关键列：{', '.join(missing_cols)}")
            return pd.DataFrame()

        # 数据预处理
        # 确保到货年月为字符串格式，便于筛选
        df_red["到货年月"] = df_red["到货年月"].astype(str)

        # 处理缺失值
        fill_values = {
            "提前/延期": "未知",
            "预计物流时效-实际物流时效差值(绝对值)": 0,
            "预计物流时效-实际物流时效差值": 0,
            "签收-发货时间": 0,
            "上架完成-发货时间": 0
        }
        # 只填充存在的列
        fill_values = {k: v for k, v in fill_values.items() if k in df_red.columns}
        df_red = df_red.fillna(fill_values)

        # 按到货年月排序
        try:
            df_red["到货年月_sort"] = pd.to_datetime(df_red["到货年月"] + "01", format="%Y%m%d", errors='coerce')
        except:
            # 尝试其他日期格式
            try:
                df_red["到货年月_sort"] = pd.to_datetime(df_red["到货年月"], format="%Y%m", errors='coerce')
            except:
                df_red["到货年月_sort"] = pd.to_datetime(df_red["到货年月"], errors='coerce')

        df_red = df_red.sort_values("到货年月_sort", ascending=False)

        st.sidebar.success("✅ 数据加载成功！")
        return df_red

    except Exception as e:
        st.error(f"数据加载失败：{str(e)}")
        st.sidebar.error(f"详细错误：{str(e)}")
        return pd.DataFrame()


# ---------------------- 数据计算函数 ----------------------
def calculate_monthly_metrics(df, month):
    """计算指定月份的核心指标"""
    df_month = df[df["到货年月"] == month].copy()

    # 初始化指标
    metrics = {
        "fba_count": len(df_month),
        "on_time_count": 0,
        "delay_count": 0,
        "abs_diff_avg": 0,
        "diff_avg": 0,
        "sign_send_avg": 0,
        "shelf_send_avg": 0
    }

    # 计算提前/准时数
    if "提前/延期" in df_month.columns:
        metrics["on_time_count"] = len(df_month[df_month["提前/延期"] == "提前/准时"])
        metrics["delay_count"] = len(df_month[df_month["提前/延期"] == "延期"])

    # 计算差值平均值
    if "预计物流时效-实际物流时效差值(绝对值)" in df_month.columns:
        metrics["abs_diff_avg"] = df_month["预计物流时效-实际物流时效差值(绝对值)"].mean()

    if "预计物流时效-实际物流时效差值" in df_month.columns:
        metrics["diff_avg"] = df_month["预计物流时效-实际物流时效差值"].mean()

    # 计算时间平均值
    if "签收-发货时间" in df_month.columns:
        metrics["sign_send_avg"] = df_month["签收-发货时间"].mean()

    if "上架完成-发货时间" in df_month.columns:
        metrics["shelf_send_avg"] = df_month["上架完成-发货时间"].mean()

    return metrics


def get_prev_month(current_month):
    """获取上个月的年月字符串"""
    try:
        # 尝试多种日期格式
        for fmt in ["%Y%m", "%Y-%m", "%Y/%m", "%Y年%m月"]:
            try:
                current_date = pd.to_datetime(current_month, format=fmt)
                prev_date = current_date - pd.DateOffset(months=1)
                # 返回与原格式匹配的字符串
                if fmt == "%Y%m":
                    return prev_date.strftime("%Y%m")
                elif fmt == "%Y-%m":
                    return prev_date.strftime("%Y-%m")
                elif fmt == "%Y/%m":
                    return prev_date.strftime("%Y/%m")
                else:
                    return prev_date.strftime("%Y年%m月")
            except:
                continue

        # 尝试拼接01的格式
        current_date = pd.to_datetime(current_month + "01", format="%Y%m%d", errors='coerce')
        if pd.notna(current_date):
            prev_date = current_date - pd.DateOffset(months=1)
            return prev_date.strftime("%Y%m")

        return None
    except:
        return None


def compare_with_prev(df, current_month, metric_name):
    """对比当月与上月指标"""
    prev_month = get_prev_month(current_month)
    if not prev_month or prev_month not in df["到货年月"].unique():
        return None, None, None

    current_metrics = calculate_monthly_metrics(df, current_month)
    prev_metrics = calculate_monthly_metrics(df, prev_month)

    current_val = current_metrics[metric_name]
    prev_val = prev_metrics[metric_name]

    if prev_val == 0:
        change_pct = 0 if current_val == 0 else 100
    else:
        change_pct = ((current_val - prev_val) / prev_val) * 100

    change_abs = current_val - prev_val

    return prev_val, change_abs, change_pct


# ---------------------- 可视化样式函数 ----------------------
def highlight_cell(val, avg_val):
    """高亮大于平均值的单元格"""
    if pd.isna(val) or pd.isna(avg_val):
        return ""
    try:
        val_num = float(val)
        avg_num = float(avg_val)
        if val_num > avg_num:
            return "background-color: #ffcccc"
    except:
        pass
    return ""


# ---------------------- 主程序 ----------------------
def main():
    st.title("📦 物流交期分析看板")
    st.markdown("---")

    # 加载数据
    df_red = load_data()
    if df_red.empty:
        st.warning("⚠️ 数据加载失败或数据为空，请检查数据源和列名")
        st.stop()

    # 红单分析看板区域
    st.header("红单分析看板区域")
    st.markdown("---")

    # 获取所有到货年月并排序
    try:
        unique_months = sorted(
            df_red["到货年月"].unique(),
            key=lambda x: pd.to_datetime(x + "01", format="%Y%m%d", errors='coerce') if len(
                str(x)) == 6 else pd.to_datetime(x, errors='coerce'),
            reverse=True
        )
        # 过滤掉无效的日期值
        unique_months = [m for m in unique_months if
                         pd.notna(pd.to_datetime(str(m) + "01", format="%Y%m%d", errors='coerce')) or pd.notna(
                             pd.to_datetime(str(m), errors='coerce'))]
    except:
        # 简单排序
        unique_months = sorted(df_red["到货年月"].unique(), reverse=True)

    if not unique_months:
        st.warning("⚠️ 没有找到有效的到货年月数据")
        st.stop()

    # ===================== 一、总的概括 =====================
    st.subheader("📊 总体概况分析")

    # 时间筛选器
    selected_month = st.selectbox(
        "选择到货年月",
        options=unique_months,
        index=0,
        key="summary_month"
    )

    # 计算当前月和上月指标
    current_metrics = calculate_monthly_metrics(df_red, selected_month)
    prev_month = get_prev_month(selected_month)
    prev_metrics = calculate_monthly_metrics(df_red, prev_month) if (
                prev_month and prev_month in unique_months) else None

    # 创建5列布局展示核心指标
    col1, col2, col3, col4, col5 = st.columns(5)

    # 1. FBA单数
    with col1:
        st.metric("FBA单数", value=current_metrics["fba_count"])
        if prev_metrics:
            fba_change = current_metrics["fba_count"] - prev_metrics["fba_count"]
            prev_val = prev_metrics["fba_count"]
            if fba_change > 0:
                st.markdown(f'<span style="color:red;">增加 {fba_change} (上月：{prev_val})</span>',
                            unsafe_allow_html=True)
            elif fba_change < 0:
                st.markdown(f'<span style="color:green;">减少 {abs(fba_change)} (上月：{prev_val})</span>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:gray;">持平 (上月：{prev_val})</span>', unsafe_allow_html=True)

    # 2. 提前/准时数
    with col2:
        st.metric("提前/准时数", value=current_metrics["on_time_count"], delta_color="normal")
        if current_metrics["fba_count"] > 0:
            st.markdown(
                f'<span style="color:green;">占比：{(current_metrics["on_time_count"] / current_metrics["fba_count"] * 100):.1f}%</span>',
                unsafe_allow_html=True)
        else:
            st.markdown(f'<span style="color:green;">占比：0.0%</span>', unsafe_allow_html=True)

    # 3. 延期数
    with col3:
        st.metric("延期数", value=current_metrics["delay_count"], delta_color="normal")
        if current_metrics["fba_count"] > 0:
            st.markdown(
                f'<span style="color:red;">占比：{(current_metrics["delay_count"] / current_metrics["fba_count"] * 100):.1f}%</span>',
                unsafe_allow_html=True)
        else:
            st.markdown(f'<span style="color:red;">占比：0.0%</span>', unsafe_allow_html=True)

    # 4. 预计-实际差值（绝对值）平均值
    with col4:
        st.metric("差值绝对值平均值", value=f"{current_metrics['abs_diff_avg']:.2f}")
        if prev_metrics and prev_metrics["abs_diff_avg"] != 0:
            abs_change_pct = ((current_metrics["abs_diff_avg"] - prev_metrics["abs_diff_avg"]) / prev_metrics[
                "abs_diff_avg"]) * 100
            prev_val = prev_metrics["abs_diff_avg"]
            if abs_change_pct > 0:
                st.markdown(f'<span style="color:red;">上升 {abs_change_pct:.2f}% (上月：{prev_val:.2f})</span>',
                            unsafe_allow_html=True)
            elif abs_change_pct < 0:
                st.markdown(f'<span style="color:green;">下降 {abs(abs_change_pct):.2f}% (上月：{prev_val:.2f})</span>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:gray;">持平 (上月：{prev_val:.2f})</span>', unsafe_allow_html=True)
        elif prev_metrics:
            st.markdown(f'<span style="color:gray;">上月无数据</span>', unsafe_allow_html=True)

    # 5. 预计-实际差值平均值
    with col5:
        st.metric("差值平均值", value=f"{current_metrics['diff_avg']:.2f}")
        if prev_metrics:
            diff_change = current_metrics["diff_avg"] - prev_metrics["diff_avg"]
            prev_val = prev_metrics["diff_avg"]
            if diff_change > 0:
                st.markdown(f'<span style="color:red;">增加 {diff_change:.2f} (上月：{prev_val:.2f})</span>',
                            unsafe_allow_html=True)
            elif diff_change < 0:
                st.markdown(f'<span style="color:green;">减少 {abs(diff_change):.2f} (上月：{prev_val:.2f})</span>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:gray;">持平 (上月：{prev_val:.2f})</span>', unsafe_allow_html=True)

    st.markdown("---")

    # ===================== 二、不同月份红单时效情况 =====================
    st.subheader("📈 不同月份红单时效趋势")

    # 左侧：月度统计表
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # 计算所有月份的指标
        monthly_data = []
        for month in unique_months:
            metrics = calculate_monthly_metrics(df_red, month)
            monthly_data.append({
                "到货年月": month,
                "FBA单数": metrics["fba_count"],
                "提前/准时数": metrics["on_time_count"],
                "延期数": metrics["delay_count"],
                "差值绝对值平均值": metrics["abs_diff_avg"],
                "差值平均值": metrics["diff_avg"]
            })

        # 创建月度统计表
        df_monthly = pd.DataFrame(monthly_data)

        # 计算各列平均值（排除0值）
        avg_row = {
            "到货年月": "平均值",
            "FBA单数": df_monthly["FBA单数"].mean(),
            "提前/准时数": df_monthly["提前/准时数"].mean(),
            "延期数": df_monthly["延期数"].mean(),
            "差值绝对值平均值": df_monthly[df_monthly["差值绝对值平均值"] > 0]["差值绝对值平均值"].mean() if any(
                df_monthly["差值绝对值平均值"] > 0) else 0,
            "差值平均值": df_monthly["差值平均值"].mean()
        }

        # 插入平均值行到顶部
        df_monthly = pd.concat([pd.DataFrame([avg_row]), df_monthly], ignore_index=True)

        # 添加环比列
        df_monthly["FBA单数环比"] = ""
        df_monthly["差值绝对值环比(%)"] = ""
        df_monthly["差值平均值环比"] = ""

        # 计算环比
        for i in range(1, len(df_monthly)):
            if i == 1:  # 跳过平均值行
                continue
            current_idx = i
            prev_idx = i - 1
            if prev_idx >= 1:
                # FBA单数环比
                fba_current = df_monthly.loc[current_idx, "FBA单数"]
                fba_prev = df_monthly.loc[prev_idx, "FBA单数"]
                if fba_prev > 0:
                    fba_change = fba_current - fba_prev
                    if fba_change > 0:
                        df_monthly.loc[current_idx, "FBA单数环比"] = f'<span style="color:red;">+{fba_change}</span>'
                    elif fba_change < 0:
                        df_monthly.loc[current_idx, "FBA单数环比"] = f'<span style="color:green;">{fba_change}</span>'
                    else:
                        df_monthly.loc[current_idx, "FBA单数环比"] = "0"

                # 差值绝对值环比
                abs_current = df_monthly.loc[current_idx, "差值绝对值平均值"]
                abs_prev = df_monthly.loc[prev_idx, "差值绝对值平均值"]
                if abs_prev > 0:
                    abs_change_pct = ((abs_current - abs_prev) / abs_prev * 100)
                    if abs_change_pct > 0:
                        df_monthly.loc[
                            current_idx, "差值绝对值环比(%)"] = f'<span style="color:red;">+{abs_change_pct:.1f}%</span>'
                    elif abs_change_pct < 0:
                        df_monthly.loc[
                            current_idx, "差值绝对值环比(%)"] = f'<span style="color:green;">{abs_change_pct:.1f}%</span>'
                    else:
                        df_monthly.loc[current_idx, "差值绝对值环比(%)"] = "0%"

                # 差值平均值环比
                diff_current = df_monthly.loc[current_idx, "差值平均值"]
                diff_prev = df_monthly.loc[prev_idx, "差值平均值"]
                diff_change = diff_current - diff_prev
                if diff_change > 0:
                    df_monthly.loc[
                        current_idx, "差值平均值环比"] = f'<span style="color:red;">+{diff_change:.2f}</span>'
                elif diff_change < 0:
                    df_monthly.loc[
                        current_idx, "差值平均值环比"] = f'<span style="color:green;">{diff_change:.2f}</span>'
                else:
                    df_monthly.loc[current_idx, "差值平均值环比"] = "0.00"

        # 高亮大于平均值的单元格
        def highlight_above_avg(val):
            if val == "平均值":
                return "background-color: #f0f0f0; font-weight: bold"
            try:
                col_name = val.name
                avg_val = df_monthly.loc[0, col_name]
                val_num = float(val)
                if val_num > avg_val and avg_val > 0:
                    return "background-color: #ffcccc"
            except:
                pass
            return ""

        # 显示表格
        st.write("月度指标统计表")
        styled_df = df_monthly.style.apply(highlight_above_avg, axis=0)
        st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)

    # 右侧：折线图
    with col_right:
        # 过滤掉平均值行
        df_chart = df_monthly[df_monthly["到货年月"] != "平均值"].copy()

        if len(df_chart) > 0:
            # 创建双折线图
            fig = go.Figure()
            # 差值绝对值折线
            fig.add_trace(go.Scatter(
                x=df_chart["到货年月"],
                y=df_chart["差值绝对值平均值"],
                name="差值绝对值平均值",
                line=dict(color="#e74c3c", width=2),
                marker=dict(size=6)
            ))
            # 差值平均值折线
            fig.add_trace(go.Scatter(
                x=df_chart["到货年月"],
                y=df_chart["差值平均值"],
                name="差值平均值",
                line=dict(color="#3498db", width=2),
                marker=dict(size=6)
            ))

            # 图表样式设置
            fig.update_layout(
                title="月度时效差值趋势",
                xaxis_title="到货年月",
                yaxis_title="平均值",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无足够数据生成图表")

    st.markdown("---")

    # ===================== 三、当月源数据展示 =====================
    st.subheader("📋 当月源数据详情")

    # 时间筛选器
    detail_month = st.selectbox(
        "选择到货年月",
        options=unique_months,
        index=0,
        key="detail_month"
    )

    # 筛选当月数据
    df_detail = df_red[df_red["到货年月"] == detail_month].copy()

    # 选择需要展示的列（只选择存在的列）
    display_cols = [
        "到货年月", "提前/延期", "FBA号", "店铺", "仓库", "货代",
        "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值"
    ]
    display_cols = [col for col in display_cols if col in df_detail.columns]

    if display_cols:
        df_display = df_detail[display_cols].copy()

        # 按差值升序排序（如果列存在）
        if "预计物流时效-实际物流时效差值" in df_display.columns:
            df_display = df_display.sort_values("预计物流时效-实际物流时效差值", ascending=True)

        # 计算平均值行
        avg_vals = {}
        for col in display_cols:
            if col in ["到货年月", "提前/延期", "FBA号", "店铺", "仓库", "货代"]:
                avg_vals[col] = "-"
            else:
                avg_vals[col] = df_display[col].mean() if len(df_display) > 0 else 0

        # 插入平均值行
        if len(df_display) > 0:
            df_display = pd.concat([pd.DataFrame([avg_vals]), df_display], ignore_index=True)

        # 高亮大于平均值的单元格
        def highlight_detail_cell(val):
            col_name = val.name
            numeric_cols = ["签收-发货时间", "上架完成-发货时间",
                            "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值"]
            numeric_cols = [col for col in numeric_cols if col in df_display.columns]

            if col_name not in numeric_cols:
                return ""

            avg_val = df_display.loc[0, col_name] if len(df_display) > 0 else 0
            if pd.isna(val) or pd.isna(avg_val):
                return ""

            try:
                val_num = float(val)
                if val_num > avg_val and avg_val > 0:
                    return "background-color: #ffcccc"
            except:
                pass
            return ""

        # 显示表格
        styled_detail = df_display.style.apply(highlight_detail_cell, axis=0)
        st.dataframe(styled_detail, use_container_width=True, height=400)
    else:
        st.info("暂无可用的展示列")

    st.markdown("---")

    # ===================== 四、货代分析 =====================
    st.subheader("🏢 货代绩效分析")

    # 检查必要列是否存在
    if "货代" in df_red.columns and "提前/延期" in df_red.columns:
        # 数据预处理
        df_forwarder = df_red[df_red["到货年月"] == selected_month].copy()
        forwarder_cols = [
            "货代", "提前/延期",
            "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值"
        ]
        forwarder_cols = [col for col in forwarder_cols if col in df_forwarder.columns]

        if forwarder_cols:
            df_forwarder_analysis = df_forwarder[forwarder_cols].copy()

            # 计算货代指标
            forwarder_metrics = []
            for forwarder in df_forwarder_analysis["货代"].unique():
                if pd.isna(forwarder):
                    continue

                df_f = df_forwarder_analysis[df_forwarder_analysis["货代"] == forwarder]
                total = len(df_f)
                if total == 0:
                    continue

                on_time = len(df_f[df_f["提前/延期"] == "提前/准时"]) if "提前/延期" in df_f.columns else 0
                delay = len(df_f[df_f["提前/延期"] == "延期"]) if "提前/延期" in df_f.columns else 0

                # 准时率
                on_time_rate = (on_time / total * 100) if total > 0 else 0

                # 差值指标
                abs_diff_avg = df_f[
                    "预计物流时效-实际物流时效差值(绝对值)"].mean() if "预计物流时效-实际物流时效差值(绝对值)" in df_f.columns else 0
                diff_avg = df_f[
                    "预计物流时效-实际物流时效差值"].mean() if "预计物流时效-实际物流时效差值" in df_f.columns else 0

                forwarder_metrics.append({
                    "货代名称": forwarder,
                    "总单数": total,
                    "准时单数": on_time,
                    "延期单数": delay,
                    "准时率(%)": on_time_rate,
                    "差值绝对值平均值": abs_diff_avg,
                    "差值平均值": diff_avg
                })

            if forwarder_metrics:
                df_forwarder_metrics = pd.DataFrame(forwarder_metrics)
                df_forwarder_metrics = df_forwarder_metrics.sort_values("准时率(%)", ascending=False)

                # 布局：表格 + 图表
                col_f1, col_f2 = st.columns([1, 1])

                with col_f1:
                    st.write("货代绩效统计表")
                    st.dataframe(df_forwarder_metrics, use_container_width=True)

                with col_f2:
                    # 准时率柱状图
                    fig1 = px.bar(
                        df_forwarder_metrics,
                        x="货代名称",
                        y="准时率(%)",
                        title="各货代准时率对比",
                        color="准时率(%)",
                        color_continuous_scale=["red", "yellow", "green"],
                        height=400
                    )
                    fig1.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig1, use_container_width=True)

                # 差值指标对比图
                col_f3, col_f4 = st.columns([1, 1])

                with col_f3:
                    if "差值绝对值平均值" in df_forwarder_metrics.columns:
                        fig2 = px.bar(
                            df_forwarder_metrics,
                            x="货代名称",
                            y="差值绝对值平均值",
                            title="各货代差值绝对值平均值",
                            color="差值绝对值平均值",
                            color_continuous_scale="Reds",
                            height=400
                        )
                        fig2.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig2, use_container_width=True)

                with col_f4:
                    if "差值平均值" in df_forwarder_metrics.columns:
                        fig3 = px.bar(
                            df_forwarder_metrics,
                            x="货代名称",
                            y="差值平均值",
                            title="各货代差值平均值",
                            color="差值平均值",
                            color_continuous_scale=px.colors.diverging.RdBu,
                            height=400
                        )
                        fig3.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("暂无货代数据可分析")
        else:
            st.info("缺少货代分析所需的列")
    else:
        st.info("缺少货代或提前/延期列，无法进行货代分析")

    st.markdown("---")

    # ===================== 五、仓库分析 =====================
    st.subheader("🏬 仓库绩效分析")

    # 检查必要列是否存在
    if "仓库" in df_red.columns and "提前/延期" in df_red.columns:
        # 数据预处理
        df_warehouse = df_red[df_red["到货年月"] == selected_month].copy()
        warehouse_cols = [
            "仓库", "提前/延期",
            "预计物流时效-实际物流时效差值(绝对值)", "预计物流时效-实际物流时效差值"
        ]
        warehouse_cols = [col for col in warehouse_cols if col in df_warehouse.columns]

        if warehouse_cols:
            df_warehouse_analysis = df_warehouse[warehouse_cols].copy()

            # 计算仓库指标
            warehouse_metrics = []
            for warehouse in df_warehouse_analysis["仓库"].unique():
                if pd.isna(warehouse):
                    continue

                df_w = df_warehouse_analysis[df_warehouse_analysis["仓库"] == warehouse]
                total = len(df_w)
                if total == 0:
                    continue

                on_time = len(df_w[df_w["提前/延期"] == "提前/准时"]) if "提前/延期" in df_w.columns else 0
                delay = len(df_w[df_w["提前/延期"] == "延期"]) if "提前/延期" in df_w.columns else 0

                # 准时率
                on_time_rate = (on_time / total * 100) if total > 0 else 0

                # 差值指标
                abs_diff_avg = df_w[
                    "预计物流时效-实际物流时效差值(绝对值)"].mean() if "预计物流时效-实际物流时效差值(绝对值)" in df_w.columns else 0
                diff_avg = df_w[
                    "预计物流时效-实际物流时效差值"].mean() if "预计物流时效-实际物流时效差值" in df_w.columns else 0

                warehouse_metrics.append({
                    "仓库名称": warehouse,
                    "总单数": total,
                    "准时单数": on_time,
                    "延期单数": delay,
                    "准时率(%)": on_time_rate,
                    "差值绝对值平均值": abs_diff_avg,
                    "差值平均值": diff_avg
                })

            if warehouse_metrics:
                df_warehouse_metrics = pd.DataFrame(warehouse_metrics)
                df_warehouse_metrics = df_warehouse_metrics.sort_values("准时率(%)", ascending=False)

                # 布局：表格 + 图表
                col_w1, col_w2 = st.columns([1, 1])

                with col_w1:
                    st.write("仓库绩效统计表")
                    st.dataframe(df_warehouse_metrics, use_container_width=True)

                with col_w2:
                    # 订单量占比饼图
                    fig4 = px.pie(
                        df_warehouse_metrics,
                        values="总单数",
                        names="仓库名称",
                        title="各仓库订单量占比",
                        hole=0.3
                    )
                    st.plotly_chart(fig4, use_container_width=True)

                # 差值指标对比
                col_w3, col_w4 = st.columns([1, 1])

                with col_w3:
                    # 准时率 vs 差值绝对值散点图
                    if "准时率(%)" in df_warehouse_metrics.columns and "差值绝对值平均值" in df_warehouse_metrics.columns:
                        fig5 = px.scatter(
                            df_warehouse_metrics,
                            x="准时率(%)",
                            y="差值绝对值平均值",
                            size="总单数",
                            color="仓库名称",
                            title="仓库准时率 vs 差值绝对值",
                            size_max=60,
                            height=400
                        )
                        st.plotly_chart(fig5, use_container_width=True)

                with col_w4:
                    # 差值平均值趋势线图
                    if "差值平均值" in df_warehouse_metrics.columns:
                        fig6 = px.line(
                            df_warehouse_metrics,
                            x="仓库名称",
                            y="差值平均值",
                            title="各仓库差值平均值趋势",
                            markers=True,
                            height=400
                        )
                        fig6.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig6, use_container_width=True)
            else:
                st.info("暂无仓库数据可分析")
        else:
            st.info("缺少仓库分析所需的列")
    else:
        st.info("缺少仓库或提前/延期列，无法进行仓库分析")


# ========== 运行入口 ==========
if __name__ == "__main__":
    # 检查运行方式，确保通过streamlit run启动
    if "streamlit" not in sys.argv[0]:
        # 如果不是，自动调用streamlit run
        import subprocess

        subprocess.run(["streamlit", "run", __file__] + sys.argv[1:], check=True)
    else:
        main()