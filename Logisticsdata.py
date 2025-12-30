import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from streamlit_extras.dataframe_explorer import dataframe_explorer

# ======================== 全局配置 ========================
st.set_page_config(
    page_title="物流交期分析看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 数据源地址
DATA_URL = "https://github.com/Jane-zzz-123/Logistics/raw/main/Logisticsdata.xlsx"


# ======================== 通用工具函数 ========================
def get_last_month(date_str):
    """获取上月日期（格式：YYYY-MM）"""
    try:
        date = pd.to_datetime(date_str)
        last_month = date - pd.DateOffset(months=1)
        return last_month.strftime("%Y-%m")
    except:
        return None


def calculate_percent_change(current, previous):
    """计算环比变化率"""
    if previous == 0 or pd.isna(previous):
        return "N/A"
    change = ((current - previous) / previous) * 100
    return f"{change:.1f}%"


def highlight_avg_row_red(row, avg_columns):
    """红单-高亮平均值行"""
    styles = []
    for col in row.index:
        if row.name == "平均值" and col in avg_columns:
            styles.append("background-color: #ffff99; font-weight: bold")
        else:
            styles.append("")
    return styles


def highlight_avg_row_air(row, avg_columns):
    """空派-高亮平均值行（排除清关耗时）"""
    styles = []
    for col in row.index:
        if col == "清关耗时":
            styles.append("")
        elif row.name == "平均值" and col in avg_columns:
            styles.append("background-color: #ffff99; font-weight: bold")
        else:
            styles.append("")
    return styles


def highlight_clearance_cell(val):
    """空派-清关耗时>=1标浅红色"""
    if pd.isna(val):
        return ""
    try:
        val = float(val)
        if val >= 1:
            return "background-color: #ffcccc; color: #333"
        return ""
    except:
        return ""


# ======================== 红单数据加载 ========================
@st.cache_data(ttl=3600)
def load_red_data():
    """加载红单数据"""
    try:
        df = pd.read_excel(DATA_URL, sheet_name="上架完成-红单")

        # 红单核心列
        required_cols = [
            "FBA号", "店铺", "仓库", "货代",
            "发货-提取", "提取-到港", "到港-签收", "签收-完成上架",
            "发货-签收", "发货-完成上架", "到货年月",
            "上架完成-发货时间", "预计物流时效-实际物流时效差值(绝对值)",
            "预计物流时效-实际物流时效差值", "提前/延期"
        ]

        df = df[required_cols].copy()
        df = df.dropna(subset=["FBA号", "到货年月"])

        # 数据类型转换
        df["到货年月"] = pd.to_datetime(df["到货年月"], format="%Y-%m", errors="coerce")
        time_cols = ["发货-提取", "提取-到港", "到港-签收", "签收-完成上架", "发货-签收", "发货-完成上架"]
        for col in time_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["提前/延期"] = df["提前/延期"].fillna("未知")
        df["年月_str"] = df["到货年月"].dt.strftime("%Y-%m")

        return df
    except Exception as e:
        st.error(f"红单数据加载失败：{str(e)}")
        return pd.DataFrame()


# ======================== 空派数据加载 ========================
@st.cache_data(ttl=3600)
def load_air_data():
    """加载空派数据"""
    try:
        df = pd.read_excel(DATA_URL, sheet_name="上架完成-空运")

        # 空派核心列（按需求修改）
        required_cols = [
            "FBA号", "店铺", "仓库", "货代", "异常备注",
            "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架",
            "发货-签收", "发货-完成上架", "清关耗时", "到货年月",
            "上架完成-发货时间", "预计物流时效-实际物流时效差值(绝对值)",
            "预计物流时效-实际物流时效差值", "提前/延期"
        ]

        df = df[required_cols].copy()
        df = df.dropna(subset=["FBA号", "到货年月"])

        # 数据类型转换
        df["到货年月"] = pd.to_datetime(df["到货年月"], format="%Y-%m", errors="coerce")
        time_cols = [
            "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架",
            "发货-签收", "发货-完成上架", "清关耗时"
        ]
        for col in time_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["提前/延期"] = df["提前/延期"].fillna("未知")
        df["年月_str"] = df["到货年月"].dt.strftime("%Y-%m")

        return df
    except Exception as e:
        st.error(f"空派数据加载失败：{str(e)}")
        return pd.DataFrame()


# ======================== 红单分析主函数 ========================
def red_analysis():
    """红单物流分析"""
    st.title("🎯 红单物流交期分析看板")
    st.divider()

    # 加载数据
    df_red = load_red_data()
    if df_red.empty:
        st.warning("暂无红单数据可分析")
        return

    # 侧边栏筛选
    with st.sidebar:
        st.header("📌 红单数据筛选")
        available_months = sorted(df_red["年月_str"].unique())
        selected_month = st.selectbox(
            "选择到货年月",
            available_months,
            index=len(available_months) - 1 if available_months else 0
        )

        order_filter = st.radio(
            "订单类型筛选",
            ["全部订单", "仅提前", "仅延期"],
            index=0
        )

        view_type = st.radio(
            "视图切换",
            ["汇总视图", "明细视图"],
            index=0
        )

    # 数据筛选
    df_current = df_red[df_red["年月_str"] == selected_month].copy()
    last_month = get_last_month(selected_month)
    df_last = df_red[df_red["年月_str"] == last_month].copy() if last_month else pd.DataFrame()

    if order_filter == "仅提前":
        df_current = df_current[df_current["提前/延期"] == "提前"].copy()
    elif order_filter == "仅延期":
        df_current = df_current[df_current["提前/延期"] == "延期"].copy()

    # 核心指标
    st.header(f"当月红单分析 ({selected_month})")
    col1, col2, col3, col4, col5 = st.columns(5)

    current_total = len(df_current)
    last_total = len(df_last)

    current_early = len(df_current[df_current["提前/延期"] == "提前"]) if current_total > 0 else 0
    current_on_time = len(df_current[df_current["提前/延期"] == "准时"]) if current_total > 0 else 0
    current_delay = len(df_current[df_current["提前/延期"] == "延期"]) if current_total > 0 else 0

    last_early = len(df_last[df_last["提前/延期"] == "提前"]) if last_total > 0 else 0
    last_on_time = len(df_last[df_last["提前/延期"] == "准时"]) if last_total > 0 else 0
    last_delay = len(df_last[df_last["提前/延期"] == "延期"]) if last_total > 0 else 0

    current_on_time_rate = (current_early + current_on_time) / current_total * 100 if current_total > 0 else 0
    last_on_time_rate = (last_early + last_on_time) / last_total * 100 if last_total > 0 else 0

    current_avg_duration = df_current["发货-完成上架"].mean() if current_total > 0 else 0
    last_avg_duration = df_last["发货-完成上架"].mean() if last_total > 0 else 0

    with col1:
        st.metric(
            label="红单FBA单数",
            value=current_total,
            delta=f"{calculate_percent_change(current_total, last_total)} (上月)"
        )
    with col2:
        st.metric(
            label="提前/准时数",
            value=current_early + current_on_time,
            delta=f"{calculate_percent_change(current_early + current_on_time, last_early + last_on_time)} (上月)"
        )
    with col3:
        st.metric(
            label="延期数",
            value=current_delay,
            delta=f"{calculate_percent_change(current_delay, last_delay)} (上月)"
        )
    with col4:
        st.metric(
            label="准时率",
            value=f"{current_on_time_rate:.1f}%",
            delta=f"{calculate_percent_change(current_on_time_rate, last_on_time_rate)} (上月)"
        )
    with col5:
        st.metric(
            label="平均全程时效(天)",
            value=f"{current_avg_duration:.1f}",
            delta=f"{calculate_percent_change(current_avg_duration, last_avg_duration)} (上月)"
        )

    st.divider()

    # 准时率与时效偏差分布
    st.subheader("准时率与时效偏差分布")
    col_a, col_b = st.columns(2)

    with col_a:
        status_counts = df_current["提前/延期"].value_counts()
        fig_pie = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="红单准时率分布",
            color_discrete_map={"提前": "#2ecc71", "准时": "#3498db", "延期": "#e74c3c", "未知": "#95a5a6"}
        )
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        fig_hist = px.histogram(
            df_current,
            x="预计物流时效-实际物流时效差值",
            title="红单时效偏差分布",
            color_discrete_sequence=["#8e44ad"]
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    # 红单明细
    st.subheader("红单明细（含平均值）")
    detail_cols = [
        "FBA号", "店铺", "仓库", "货代",
        "发货-提取", "提取-到港", "到港-签收",
        "签收-完成上架", "发货-签收", "发货-完成上架",
        "预计物流时效-实际物流时效差值", "提前/延期"
    ]
    df_detail = df_current[detail_cols].copy()

    # 平均值计算
    avg_columns = [col for col in detail_cols if col not in ["FBA号", "店铺", "仓库", "货代", "提前/延期"]]
    avg_data = {}
    for col in detail_cols:
        if col in avg_columns:
            avg_data[col] = [round(df_detail[col].mean(), 1)]
        else:
            avg_data[col] = ["平均值"]

    df_avg = pd.DataFrame(avg_data)
    df_detail_with_avg = pd.concat([df_detail, df_avg], ignore_index=True)

    # 数据筛选
    if view_type == "明细视图":
        df_filtered = dataframe_explorer(df_detail_with_avg, case=False)
    else:
        df_filtered = df_detail_with_avg

    # 样式
    styled_df = df_filtered.style.apply(
        highlight_avg_row_red,
        avg_columns=avg_columns,
        axis=1
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "发货-提取": st.column_config.NumberColumn("发货-提取(天)", format="%.1f"),
            "提取-到港": st.column_config.NumberColumn("提取-到港(天)", format="%.1f"),
            "到港-签收": st.column_config.NumberColumn("到港-签收(天)", format="%.1f")
        }
    )

    # 下载
    csv_data = df_detail.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 下载红单明细数据",
        data=csv_data,
        file_name=f"红单明细_{selected_month}.csv",
        mime="text/csv"
    )

    st.divider()

    # 货代准时情况
    st.subheader("货代准时情况分析")
    col_c, col_d = st.columns([1, 1])

    with col_c:
        forwarder_stats = df_current.groupby("货代").agg({
            "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100,
            "FBA号": "count"
        }).round(2)
        forwarder_stats.columns = ["准时率(%)", "订单数"]
        forwarder_stats = forwarder_stats.sort_values("准时率(%)", ascending=False)

        fig_forwarder = px.bar(
            forwarder_stats,
            x=forwarder_stats.index,
            y="准时率(%)",
            title="各货代红单准时率",
            color="订单数",
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_forwarder.update_layout(height=400)
        st.plotly_chart(fig_forwarder, use_container_width=True)

    with col_d:
        st.dataframe(
            forwarder_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "准时率(%)": st.column_config.ProgressColumn(
                    "准时率(%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100
                )
            }
        )

    st.divider()

    # 仓库准时情况
    st.subheader("仓库准时情况分析")
    col_e, col_f = st.columns([1, 1])

    with col_e:
        warehouse_stats = df_current.groupby("仓库").agg({
            "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100,
            "FBA号": "count"
        }).round(2)
        warehouse_stats.columns = ["准时率(%)", "订单数"]
        warehouse_stats = warehouse_stats.sort_values("准时率(%)", ascending=False)

        fig_warehouse = px.bar(
            warehouse_stats,
            x=warehouse_stats.index,
            y="准时率(%)",
            title="各仓库红单准时率",
            color="订单数",
            color_continuous_scale=px.colors.sequential.Oranges
        )
        fig_warehouse.update_layout(height=400)
        st.plotly_chart(fig_warehouse, use_container_width=True)

    with col_f:
        st.dataframe(
            warehouse_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "准时率(%)": st.column_config.ProgressColumn(
                    "准时率(%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100
                )
            }
        )

    st.divider()

    # 趋势分析
    st.subheader("不同月份红单趋势分析（货代/仓库维度）")
    trend_dim = st.radio("趋势分析维度", ["货代维度", "仓库维度"], horizontal=True)
    trend_col = "货代" if trend_dim == "货代维度" else "仓库"

    trend_data = df_red.groupby(["年月_str", trend_col]).agg({
        "FBA号": "count",
        "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100
    }).round(2)
    trend_data.columns = ["订单数", "准时率(%)"]
    trend_data = trend_data.reset_index()

    fig_trend = px.line(
        trend_data,
        x="年月_str",
        y="准时率(%)",
        color=trend_col,
        title=f"不同月份红单准时率趋势（{trend_dim}）",
        markers=True
    )
    fig_trend.update_layout(height=500)
    st.plotly_chart(fig_trend, use_container_width=True)

    st.dataframe(
        trend_data,
        use_container_width=True,
        column_config={
            "准时率(%)": st.column_config.NumberColumn(format="%.1f")
        }
    )


# ======================== 空派分析主函数（按需求修改） ========================
def air_analysis():
    """空派物流分析（核心修改部分）"""
    st.title("✈️ 空派物流交期分析看板")
    st.divider()

    # 加载数据
    df_air = load_air_data()
    if df_air.empty:
        st.warning("暂无空派数据可分析")
        return

    # 侧边栏筛选
    with st.sidebar:
        st.header("📌 空派数据筛选")
        available_months = sorted(df_air["年月_str"].unique())
        selected_month = st.selectbox(
            "选择到货年月",
            available_months,
            index=len(available_months) - 1 if available_months else 0
        )

        order_filter = st.radio(
            "订单类型筛选",
            ["全部订单", "仅提前", "仅延期"],
            index=0
        )

        view_type = st.radio(
            "视图切换",
            ["汇总视图", "明细视图"],
            index=0
        )

    # 数据筛选
    df_current = df_air[df_air["年月_str"] == selected_month].copy()
    last_month = get_last_month(selected_month)
    df_last = df_air[df_air["年月_str"] == last_month].copy() if last_month else pd.DataFrame()

    if order_filter == "仅提前":
        df_current = df_current[df_current["提前/延期"] == "提前"].copy()
    elif order_filter == "仅延期":
        df_current = df_current[df_current["提前/延期"] == "延期"].copy()

    # 核心指标（仅文字替换为"空派"）
    st.header(f"当月空派分析 ({selected_month})")
    col1, col2, col3, col4, col5 = st.columns(5)

    current_total = len(df_current)
    last_total = len(df_last)

    current_early = len(df_current[df_current["提前/延期"] == "提前"]) if current_total > 0 else 0
    current_on_time = len(df_current[df_current["提前/延期"] == "准时"]) if current_total > 0 else 0
    current_delay = len(df_current[df_current["提前/延期"] == "延期"]) if current_total > 0 else 0

    last_early = len(df_last[df_last["提前/延期"] == "提前"]) if last_total > 0 else 0
    last_on_time = len(df_last[df_last["提前/延期"] == "准时"]) if last_total > 0 else 0
    last_delay = len(df_last[df_last["提前/延期"] == "延期"]) if last_total > 0 else 0

    current_on_time_rate = (current_early + current_on_time) / current_total * 100 if current_total > 0 else 0
    last_on_time_rate = (last_early + last_on_time) / last_total * 100 if last_total > 0 else 0

    current_avg_duration = df_current["发货-完成上架"].mean() if current_total > 0 else 0
    last_avg_duration = df_last["发货-完成上架"].mean() if last_total > 0 else 0

    with col1:
        st.metric(
            label="空派FBA单数",
            value=current_total,
            delta=f"{calculate_percent_change(current_total, last_total)} (上月)"
        )
    with col2:
        st.metric(
            label="提前/准时数",
            value=current_early + current_on_time,
            delta=f"{calculate_percent_change(current_early + current_on_time, last_early + last_on_time)} (上月)"
        )
    with col3:
        st.metric(
            label="延期数",
            value=current_delay,
            delta=f"{calculate_percent_change(current_delay, last_delay)} (上月)"
        )
    with col4:
        st.metric(
            label="准时率",
            value=f"{current_on_time_rate:.1f}%",
            delta=f"{calculate_percent_change(current_on_time_rate, last_on_time_rate)} (上月)"
        )
    with col5:
        st.metric(
            label="平均全程时效(天)",
            value=f"{current_avg_duration:.1f}",
            delta=f"{calculate_percent_change(current_avg_duration, last_avg_duration)} (上月)"
        )

    st.divider()

    # 准时率与时效偏差分布（文字替换为"空派"）
    st.subheader("准时率与时效偏差分布")
    col_a, col_b = st.columns(2)

    with col_a:
        status_counts = df_current["提前/延期"].value_counts()
        fig_pie = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="空派准时率分布",
            color_discrete_map={"提前": "#2ecc71", "准时": "#3498db", "延期": "#e74c3c", "未知": "#95a5a6"}
        )
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        fig_hist = px.histogram(
            df_current,
            x="预计物流时效-实际物流时效差值",
            title="空派时效偏差分布",
            color_discrete_sequence=["#8e44ad"]
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    # 空派明细（核心修改：列替换+新增异常备注/清关耗时）
    st.subheader("空派明细（含平均值）")
    detail_cols = [
        "FBA号", "店铺", "仓库", "货代",
        "发货-起飞", "到港-提取", "提取-签收", "异常备注", "清关耗时",  # 重点修改列
        "签收-完成上架", "发货-签收", "发货-完成上架",
        "预计物流时效-实际物流时效差值", "提前/延期"
    ]
    df_detail = df_current[detail_cols].copy()

    # 平均值计算（排除清关耗时）
    avg_columns = [
        col for col in detail_cols
        if col not in ["FBA号", "店铺", "仓库", "货代", "异常备注", "提前/延期", "清关耗时"]
    ]
    avg_data = {}
    for col in detail_cols:
        if col in avg_columns:
            avg_data[col] = [round(df_detail[col].mean(), 1)]
        else:
            avg_data[col] = ["平均值"]

    df_avg = pd.DataFrame(avg_data)
    df_detail_with_avg = pd.concat([df_detail, df_avg], ignore_index=True)

    # 数据筛选
    if view_type == "明细视图":
        df_filtered = dataframe_explorer(df_detail_with_avg, case=False)
    else:
        df_filtered = df_detail_with_avg

    # 样式（清关耗时>=1标红+平均值行高亮）
    styled_df = df_filtered.style.apply(
        highlight_avg_row_air,
        avg_columns=avg_columns,
        axis=1
    ).applymap(
        highlight_clearance_cell,
        subset=["清关耗时"]
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "发货-起飞": st.column_config.NumberColumn("发货-起飞(天)", format="%.1f"),
            "到港-提取": st.column_config.NumberColumn("到港-提取(天)", format="%.1f"),
            "提取-签收": st.column_config.NumberColumn("提取-签收(天)", format="%.1f"),
            "清关耗时": st.column_config.NumberColumn("清关耗时(天)", format="%.1f")  # 新增列配置
        }
    )

    # 下载
    csv_data = df_detail.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 下载空派明细数据",
        data=csv_data,
        file_name=f"空派明细_{selected_month}.csv",
        mime="text/csv"
    )

    st.divider()

    # 货代准时情况（仅文字替换为"空派"）
    st.subheader("货代准时情况分析")
    col_c, col_d = st.columns([1, 1])

    with col_c:
        forwarder_stats = df_current.groupby("货代").agg({
            "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100,
            "FBA号": "count"
        }).round(2)
        forwarder_stats.columns = ["准时率(%)", "订单数"]
        forwarder_stats = forwarder_stats.sort_values("准时率(%)", ascending=False)

        fig_forwarder = px.bar(
            forwarder_stats,
            x=forwarder_stats.index,
            y="准时率(%)",
            title="各货代空派准时率",
            color="订单数",
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_forwarder.update_layout(height=400)
        st.plotly_chart(fig_forwarder, use_container_width=True)

    with col_d:
        st.dataframe(
            forwarder_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "准时率(%)": st.column_config.ProgressColumn(
                    "准时率(%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100
                )
            }
        )

    st.divider()

    # 仓库准时情况（仅文字替换为"空派"）
    st.subheader("仓库准时情况分析")
    col_e, col_f = st.columns([1, 1])

    with col_e:
        warehouse_stats = df_current.groupby("仓库").agg({
            "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100,
            "FBA号": "count"
        }).round(2)
        warehouse_stats.columns = ["准时率(%)", "订单数"]
        warehouse_stats = warehouse_stats.sort_values("准时率(%)", ascending=False)

        fig_warehouse = px.bar(
            warehouse_stats,
            x=warehouse_stats.index,
            y="准时率(%)",
            title="各仓库空派准时率",
            color="订单数",
            color_continuous_scale=px.colors.sequential.Oranges
        )
        fig_warehouse.update_layout(height=400)
        st.plotly_chart(fig_warehouse, use_container_width=True)

    with col_f:
        st.dataframe(
            warehouse_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "准时率(%)": st.column_config.ProgressColumn(
                    "准时率(%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100
                )
            }
        )

    st.divider()

    # 趋势分析（仅文字替换为"空派"）
    st.subheader("不同月份空派趋势分析（货代/仓库维度）")
    trend_dim = st.radio("趋势分析维度", ["货代维度", "仓库维度"], horizontal=True)
    trend_col = "货代" if trend_dim == "货代维度" else "仓库"

    trend_data = df_air.groupby(["年月_str", trend_col]).agg({
        "FBA号": "count",
        "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100
    }).round(2)
    trend_data.columns = ["订单数", "准时率(%)"]
    trend_data = trend_data.reset_index()

    fig_trend = px.line(
        trend_data,
        x="年月_str",
        y="准时率(%)",
        color=trend_col,
        title=f"不同月份空派准时率趋势（{trend_dim}）",
        markers=True
    )
    fig_trend.update_layout(height=500)
    st.plotly_chart(fig_trend, use_container_width=True)

    st.dataframe(
        trend_data,
        use_container_width=True,
        column_config={
            "准时率(%)": st.column_config.NumberColumn(format="%.1f")
        }
    )


# ======================== 主程序入口（单文件切换） ========================
def main():
    """主程序：切换红单/空派分析"""
    # 顶部导航菜单
    st.sidebar.title("📋 物流分析导航")
    analysis_type = st.sidebar.selectbox(
        "选择分析类型",
        ["红单物流分析", "空派物流分析"],
        index=0
    )

    # 执行对应分析
    if analysis_type == "红单物流分析":
        red_analysis()
    else:
        air_analysis()


# 运行程序
if __name__ == "__main__":
    # 检查依赖
    try:
        from streamlit_extras.dataframe_explorer import dataframe_explorer
    except ImportError:
        st.error("请先安装依赖：pip install streamlit-extras openpyxl pandas plotly numpy")
        st.stop()

    main()