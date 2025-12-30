import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from streamlit_extras.dataframe_explorer import dataframe_explorer

# ======================== 全局配置 ========================
st.set_page_config(
    page_title="物流交期分析看板（红单+空派）",
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

        # 筛选存在的列
        existing_cols = [col for col in required_cols if col in df.columns]
        df = df[existing_cols].copy()
        df = df.dropna(subset=["FBA号", "到货年月"])

        # 数据类型转换
        df["到货年月"] = pd.to_datetime(df["到货年月"], format="%Y-%m", errors="coerce")
        time_cols = ["发货-提取", "提取-到港", "到港-签收", "签收-完成上架", "发货-签收", "发货-完成上架"]
        time_cols = [col for col in time_cols if col in df.columns]
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

        # 筛选存在的列
        existing_cols = [col for col in required_cols if col in df.columns]
        df = df[existing_cols].copy()
        df = df.dropna(subset=["FBA号", "到货年月"])

        # 数据类型转换
        df["到货年月"] = pd.to_datetime(df["到货年月"], format="%Y-%m", errors="coerce")
        time_cols = [
            "发货-起飞", "到港-提取", "提取-签收", "签收-完成上架",
            "发货-签收", "发货-完成上架", "清关耗时"
        ]
        time_cols = [col for col in time_cols if col in df.columns]
        for col in time_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["提前/延期"] = df["提前/延期"].fillna("未知")
        df["年月_str"] = df["到货年月"].dt.strftime("%Y-%m")

        return df
    except Exception as e:
        st.error(f"空派数据加载失败：{str(e)}")
        return pd.DataFrame()


# ======================== 红单分析模块 ========================
def red_analysis_module():
    """红单分析模块（完整展示）"""
    st.title("🎯 红单物流交期分析看板")
    st.divider()

    # 加载数据
    df_red = load_red_data()
    if df_red.empty:
        st.warning("暂无红单数据可分析")
        st.markdown("---")
        st.markdown("## ✈️ 空派物流交期分析看板")
        st.warning("红单数据加载失败，空派分析也无法进行")
        return

    # 侧边栏筛选（共用侧边栏，同时控制红单和空派）
    with st.sidebar:
        st.header("📌 数据筛选（全局生效）")

        # 红单年月筛选
        available_months_red = sorted(df_red["年月_str"].unique()) if "年月_str" in df_red.columns else []
        if available_months_red:
            selected_month_red = st.selectbox(
                "红单-选择到货年月",
                available_months_red,
                index=len(available_months_red) - 1 if available_months_red else 0,
                key="red_month"
            )
        else:
            selected_month_red = ""
            st.warning("红单无有效年月数据")

        # 空派年月筛选（提前加载空派数据获取月份）
        df_air_temp = load_air_data()
        available_months_air = sorted(df_air_temp["年月_str"].unique()) if (
                    not df_air_temp.empty and "年月_str" in df_air_temp.columns) else []
        if available_months_air:
            selected_month_air = st.selectbox(
                "空派-选择到货年月",
                available_months_air,
                index=len(available_months_air) - 1 if available_months_air else 0,
                key="air_month"
            )
        else:
            selected_month_air = ""
            st.warning("空派无有效年月数据")

        # 全局订单筛选
        order_filter = st.radio(
            "订单类型筛选（全局）",
            ["全部订单", "仅提前", "仅延期"],
            index=0,
            key="order_filter"
        )

        # 视图切换
        view_type = st.radio(
            "视图切换（全局）",
            ["汇总视图", "明细视图"],
            index=0,
            key="view_type"
        )

    # 红单数据筛选
    df_current_red = df_red[df_red["年月_str"] == selected_month_red].copy() if selected_month_red else pd.DataFrame()
    last_month_red = get_last_month(selected_month_red)
    df_last_red = df_red[df_red["年月_str"] == last_month_red].copy() if (
                last_month_red and "年月_str" in df_red.columns) else pd.DataFrame()

    if order_filter == "仅提前" and "提前/延期" in df_current_red.columns:
        df_current_red = df_current_red[df_current_red["提前/延期"] == "提前"].copy()
    elif order_filter == "仅延期" and "提前/延期" in df_current_red.columns:
        df_current_red = df_current_red[df_current_red["提前/延期"] == "延期"].copy()

    # 红单核心指标
    st.header(f"当月红单分析 ({selected_month_red})")
    col1, col2, col3, col4, col5 = st.columns(5)

    current_total_red = len(df_current_red)
    last_total_red = len(df_last_red)

    current_early_red = len(df_current_red[df_current_red["提前/延期"] == "提前"]) if (
                current_total_red > 0 and "提前/延期" in df_current_red.columns) else 0
    current_on_time_red = len(df_current_red[df_current_red["提前/延期"] == "准时"]) if (
                current_total_red > 0 and "提前/延期" in df_current_red.columns) else 0
    current_delay_red = len(df_current_red[df_current_red["提前/延期"] == "延期"]) if (
                current_total_red > 0 and "提前/延期" in df_current_red.columns) else 0

    last_early_red = len(df_last_red[df_last_red["提前/延期"] == "提前"]) if (
                last_total_red > 0 and "提前/延期" in df_last_red.columns) else 0
    last_on_time_red = len(df_last_red[df_last_red["提前/延期"] == "准时"]) if (
                last_total_red > 0 and "提前/延期" in df_last_red.columns) else 0
    last_delay_red = len(df_last_red[df_last_red["提前/延期"] == "延期"]) if (
                last_total_red > 0 and "提前/延期" in df_last_red.columns) else 0

    current_on_time_rate_red = (
                                           current_early_red + current_on_time_red) / current_total_red * 100 if current_total_red > 0 else 0
    last_on_time_rate_red = (last_early_red + last_on_time_red) / last_total_red * 100 if last_total_red > 0 else 0

    current_avg_duration_red = df_current_red["发货-完成上架"].mean() if (
                current_total_red > 0 and "发货-完成上架" in df_current_red.columns) else 0
    last_avg_duration_red = df_last_red["发货-完成上架"].mean() if (
                last_total_red > 0 and "发货-完成上架" in df_last_red.columns) else 0

    with col1:
        st.metric(
            label="红单FBA单数",
            value=current_total_red,
            delta=f"{calculate_percent_change(current_total_red, last_total_red)} (上月)"
        )
    with col2:
        st.metric(
            label="提前/准时数",
            value=current_early_red + current_on_time_red,
            delta=f"{calculate_percent_change(current_early_red + current_on_time_red, last_early_red + last_on_time_red)} (上月)"
        )
    with col3:
        st.metric(
            label="延期数",
            value=current_delay_red,
            delta=f"{calculate_percent_change(current_delay_red, last_delay_red)} (上月)"
        )
    with col4:
        st.metric(
            label="准时率",
            value=f"{current_on_time_rate_red:.1f}%",
            delta=f"{calculate_percent_change(current_on_time_rate_red, last_on_time_rate_red)} (上月)"
        )
    with col5:
        st.metric(
            label="平均全程时效(天)",
            value=f"{current_avg_duration_red:.1f}",
            delta=f"{calculate_percent_change(current_avg_duration_red, last_avg_duration_red)} (上月)"
        )

    st.divider()

    # 红单准时率与时效偏差分布
    st.subheader("红单-准时率与时效偏差分布")
    col_a, col_b = st.columns(2)

    with col_a:
        if "提前/延期" in df_current_red.columns and not df_current_red.empty:
            status_counts = df_current_red["提前/延期"].value_counts()
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="红单准时率分布",
                color_discrete_map={"提前": "#2ecc71", "准时": "#3498db", "延期": "#e74c3c", "未知": "#95a5a6"}
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("红单暂无准时率数据")

    with col_b:
        if "预计物流时效-实际物流时效差值" in df_current_red.columns and not df_current_red.empty:
            fig_hist = px.histogram(
                df_current_red,
                x="预计物流时效-实际物流时效差值",
                title="红单时效偏差分布",
                color_discrete_sequence=["#8e44ad"]
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("红单暂无时效偏差数据")

    st.divider()

    # 红单明细
    st.subheader("红单-明细数据（含平均值）")
    detail_cols_red = [
        "FBA号", "店铺", "仓库", "货代",
        "发货-提取", "提取-到港", "到港-签收",
        "签收-完成上架", "发货-签收", "发货-完成上架",
        "预计物流时效-实际物流时效差值", "提前/延期"
    ]
    detail_cols_red = [col for col in detail_cols_red if col in df_current_red.columns]
    df_detail_red = df_current_red[detail_cols_red].copy()

    if not df_detail_red.empty:
        # 平均值计算
        avg_columns_red = [col for col in detail_cols_red if col not in ["FBA号", "店铺", "仓库", "货代", "提前/延期"]]
        avg_data_red = {}
        for col in detail_cols_red:
            if col in avg_columns_red:
                avg_data_red[col] = [round(df_detail_red[col].mean(), 1)] if not df_detail_red[col].isna().all() else [
                    "0.0"]
            else:
                avg_data_red[col] = ["平均值"]

        df_avg_red = pd.DataFrame(avg_data_red)
        df_detail_with_avg_red = pd.concat([df_detail_red, df_avg_red], ignore_index=True)

        # 数据探索器
        if view_type == "明细视图":
            df_filtered_red = dataframe_explorer(df_detail_with_avg_red, case=False)
        else:
            df_filtered_red = df_detail_with_avg_red

        # 样式
        styled_df_red = df_filtered_red.style.apply(
            highlight_avg_row_red,
            avg_columns=avg_columns_red,
            axis=1
        )

        st.dataframe(
            styled_df_red,
            use_container_width=True,
            hide_index=True,
            column_config={
                "发货-提取": st.column_config.NumberColumn("发货-提取(天)", format="%.1f"),
                "提取-到港": st.column_config.NumberColumn("提取-到港(天)", format="%.1f"),
                "到港-签收": st.column_config.NumberColumn("到港-签收(天)", format="%.1f")
            }
        )

        # 下载
        csv_data_red = df_detail_red.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 下载红单明细数据",
            data=csv_data_red,
            file_name=f"红单明细_{selected_month_red}.csv",
            mime="text/csv"
        )
    else:
        st.info("红单暂无明细数据")

    st.divider()

    # 红单货代分析
    st.subheader("红单-货代准时情况分析")
    if "货代" in df_current_red.columns and "提前/延期" in df_current_red.columns and not df_current_red.empty:
        col_c, col_d = st.columns([1, 1])

        with col_c:
            forwarder_stats_red = df_current_red.groupby("货代").agg({
                "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100 if len(x) > 0 else 0,
                "FBA号": "count"
            }).round(2)
            forwarder_stats_red.columns = ["准时率(%)", "订单数"]
            forwarder_stats_red = forwarder_stats_red.sort_values("准时率(%)", ascending=False)

            fig_forwarder_red = px.bar(
                forwarder_stats_red,
                x=forwarder_stats_red.index,
                y="准时率(%)",
                title="各货代红单准时率",
                color="订单数",
                color_continuous_scale=px.colors.sequential.Blues
            )
            fig_forwarder_red.update_layout(height=400)
            st.plotly_chart(fig_forwarder_red, use_container_width=True)

        with col_d:
            st.dataframe(
                forwarder_stats_red,
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
    else:
        st.info("红单暂无货代准时率数据")

    st.divider()

    # 红单仓库分析
    st.subheader("红单-仓库准时情况分析")
    if "仓库" in df_current_red.columns and "提前/延期" in df_current_red.columns and not df_current_red.empty:
        col_e, col_f = st.columns([1, 1])

        with col_e:
            warehouse_stats_red = df_current_red.groupby("仓库").agg({
                "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100 if len(x) > 0 else 0,
                "FBA号": "count"
            }).round(2)
            warehouse_stats_red.columns = ["准时率(%)", "订单数"]
            warehouse_stats_red = warehouse_stats_red.sort_values("准时率(%)", ascending=False)

            fig_warehouse_red = px.bar(
                warehouse_stats_red,
                x=warehouse_stats_red.index,
                y="准时率(%)",
                title="各仓库红单准时率",
                color="订单数",
                color_continuous_scale=px.colors.sequential.Oranges
            )
            fig_warehouse_red.update_layout(height=400)
            st.plotly_chart(fig_warehouse_red, use_container_width=True)

        with col_f:
            st.dataframe(
                warehouse_stats_red,
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
    else:
        st.info("红单暂无仓库准时率数据")

    st.divider()

    # 红单趋势分析
    st.subheader("红单-不同月份趋势分析（货代/仓库维度）")
    if not df_red.empty and "年月_str" in df_red.columns:
        trend_dim_red = st.radio("红单-趋势分析维度", ["货代维度", "仓库维度"], horizontal=True, key="red_trend")
        trend_col_red = "货代" if trend_dim_red == "货代维度" else "仓库"

        if trend_col_red in df_red.columns:
            trend_data_red = df_red.groupby(["年月_str", trend_col_red]).agg({
                "FBA号": "count",
                "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100 if len(x) > 0 else 0
            }).round(2)
            trend_data_red.columns = ["订单数", "准时率(%)"]
            trend_data_red = trend_data_red.reset_index()

            fig_trend_red = px.line(
                trend_data_red,
                x="年月_str",
                y="准时率(%)",
                color=trend_col_red,
                title=f"红单-不同月份准时率趋势（{trend_dim_red}）",
                markers=True
            )
            fig_trend_red.update_layout(height=500)
            st.plotly_chart(fig_trend_red, use_container_width=True)

            st.dataframe(
                trend_data_red,
                use_container_width=True,
                column_config={
                    "准时率(%)": st.column_config.NumberColumn(format="%.1f")
                }
            )
        else:
            st.info(f"红单暂无{trend_col_red}维度数据")
    else:
        st.info("红单暂无趋势分析数据")

    # 红单模块结束，分隔线
    st.markdown("---")
    st.markdown("## ✈️ 空派物流交期分析看板")
    st.markdown("---")


# ======================== 空派分析模块（直接追加在红单下方） ========================
def air_analysis_module(selected_month_air, order_filter, view_type):
    """空派分析模块（无切换，直接展示）"""
    # 加载数据
    df_air = load_air_data()
    if df_air.empty:
        st.warning("暂无空派数据可分析")
        return

    # 空派数据筛选
    df_current_air = df_air[df_air["年月_str"] == selected_month_air].copy() if selected_month_air else pd.DataFrame()
    last_month_air = get_last_month(selected_month_air)
    df_last_air = df_air[df_air["年月_str"] == last_month_air].copy() if (
                last_month_air and "年月_str" in df_air.columns) else pd.DataFrame()

    if order_filter == "仅提前" and "提前/延期" in df_current_air.columns:
        df_current_air = df_current_air[df_current_air["提前/延期"] == "提前"].copy()
    elif order_filter == "仅延期" and "提前/延期" in df_current_air.columns:
        df_current_air = df_current_air[df_current_air["提前/延期"] == "延期"].copy()

    # 空派核心指标
    st.header(f"当月空派分析 ({selected_month_air})")
    col1, col2, col3, col4, col5 = st.columns(5)

    current_total_air = len(df_current_air)
    last_total_air = len(df_last_air)

    current_early_air = len(df_current_air[df_current_air["提前/延期"] == "提前"]) if (
                current_total_air > 0 and "提前/延期" in df_current_air.columns) else 0
    current_on_time_air = len(df_current_air[df_current_air["提前/延期"] == "准时"]) if (
                current_total_air > 0 and "提前/延期" in df_current_air.columns) else 0
    current_delay_air = len(df_current_air[df_current_air["提前/延期"] == "延期"]) if (
                current_total_air > 0 and "提前/延期" in df_current_air.columns) else 0

    last_early_air = len(df_last_air[df_last_air["提前/延期"] == "提前"]) if (
                last_total_air > 0 and "提前/延期" in df_last_air.columns) else 0
    last_on_time_air = len(df_last_air[df_last_air["提前/延期"] == "准时"]) if (
                last_total_air > 0 and "提前/延期" in df_last_air.columns) else 0
    last_delay_air = len(df_last_air[df_last_air["提前/延期"] == "延期"]) if (
                last_total_air > 0 and "提前/延期" in df_last_air.columns) else 0

    current_on_time_rate_air = (
                                           current_early_air + current_on_time_air) / current_total_air * 100 if current_total_air > 0 else 0
    last_on_time_rate_air = (last_early_air + last_on_time_air) / last_total_air * 100 if last_total_air > 0 else 0

    current_avg_duration_air = df_current_air["发货-完成上架"].mean() if (
                current_total_air > 0 and "发货-完成上架" in df_current_air.columns) else 0
    last_avg_duration_air = df_last_air["发货-完成上架"].mean() if (
                last_total_air > 0 and "发货-完成上架" in df_last_air.columns) else 0

    with col1:
        st.metric(
            label="空派FBA单数",
            value=current_total_air,
            delta=f"{calculate_percent_change(current_total_air, last_total_air)} (上月)"
        )
    with col2:
        st.metric(
            label="提前/准时数",
            value=current_early_air + current_on_time_air,
            delta=f"{calculate_percent_change(current_early_air + current_on_time_air, last_early_air + last_on_time_air)} (上月)"
        )
    with col3:
        st.metric(
            label="延期数",
            value=current_delay_air,
            delta=f"{calculate_percent_change(current_delay_air, last_delay_air)} (上月)"
        )
    with col4:
        st.metric(
            label="准时率",
            value=f"{current_on_time_rate_air:.1f}%",
            delta=f"{calculate_percent_change(current_on_time_rate_air, last_on_time_rate_air)} (上月)"
        )
    with col5:
        st.metric(
            label="平均全程时效(天)",
            value=f"{current_avg_duration_air:.1f}",
            delta=f"{calculate_percent_change(current_avg_duration_air, last_avg_duration_air)} (上月)"
        )

    st.divider()

    # 空派准时率与时效偏差分布
    st.subheader("空派-准时率与时效偏差分布")
    col_a, col_b = st.columns(2)

    with col_a:
        if "提前/延期" in df_current_air.columns and not df_current_air.empty:
            status_counts = df_current_air["提前/延期"].value_counts()
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="空派准时率分布",
                color_discrete_map={"提前": "#2ecc71", "准时": "#3498db", "延期": "#e74c3c", "未知": "#95a5a6"}
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("空派暂无准时率数据")

    with col_b:
        if "预计物流时效-实际物流时效差值" in df_current_air.columns and not df_current_air.empty:
            fig_hist = px.histogram(
                df_current_air,
                x="预计物流时效-实际物流时效差值",
                title="空派时效偏差分布",
                color_discrete_sequence=["#8e44ad"]
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("空派暂无时效偏差数据")

    st.divider()

    # 空派明细（核心修改）
    st.subheader("空派-明细数据（含平均值）")
    detail_cols_air = [
        "FBA号", "店铺", "仓库", "货代",
        "发货-起飞", "到港-提取", "提取-签收", "异常备注", "清关耗时",
        "签收-完成上架", "发货-签收", "发货-完成上架",
        "预计物流时效-实际物流时效差值", "提前/延期"
    ]
    detail_cols_air = [col for col in detail_cols_air if col in df_current_air.columns]
    df_detail_air = df_current_air[detail_cols_air].copy()

    if not df_detail_air.empty:
        # 平均值计算（排除清关耗时）
        avg_columns_air = [
            col for col in detail_cols_air
            if col not in ["FBA号", "店铺", "仓库", "货代", "异常备注", "提前/延期", "清关耗时"]
        ]
        avg_data_air = {}
        for col in detail_cols_air:
            if col in avg_columns_air:
                avg_data_air[col] = [round(df_detail_air[col].mean(), 1)] if not df_detail_air[col].isna().all() else [
                    "0.0"]
            else:
                avg_data_air[col] = ["平均值"]

        df_avg_air = pd.DataFrame(avg_data_air)
        df_detail_with_avg_air = pd.concat([df_detail_air, df_avg_air], ignore_index=True)

        # 数据探索器
        if view_type == "明细视图":
            df_filtered_air = dataframe_explorer(df_detail_with_avg_air, case=False)
        else:
            df_filtered_air = df_detail_with_avg_air

        # 样式（清关耗时标红+平均值高亮）
        styled_df_air = df_filtered_air.style.apply(
            highlight_avg_row_air,
            avg_columns=avg_columns_air,
            axis=1
        ).applymap(
            highlight_clearance_cell,
            subset=["清关耗时"] if "清关耗时" in df_filtered_air.columns else []
        )

        st.dataframe(
            styled_df_air,
            use_container_width=True,
            hide_index=True,
            column_config={
                "发货-起飞": st.column_config.NumberColumn("发货-起飞(天)", format="%.1f"),
                "到港-提取": st.column_config.NumberColumn("到港-提取(天)", format="%.1f"),
                "提取-签收": st.column_config.NumberColumn("提取-签收(天)", format="%.1f"),
                "清关耗时": st.column_config.NumberColumn("清关耗时(天)", format="%.1f")
            }
        )

        # 下载
        csv_data_air = df_detail_air.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 下载空派明细数据",
            data=csv_data_air,
            file_name=f"空派明细_{selected_month_air}.csv",
            mime="text/csv"
        )
    else:
        st.info("空派暂无明细数据")

    st.divider()

    # 空派货代分析
    st.subheader("空派-货代准时情况分析")
    if "货代" in df_current_air.columns and "提前/延期" in df_current_air.columns and not df_current_air.empty:
        col_c, col_d = st.columns([1, 1])

        with col_c:
            forwarder_stats_air = df_current_air.groupby("货代").agg({
                "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100 if len(x) > 0 else 0,
                "FBA号": "count"
            }).round(2)
            forwarder_stats_air.columns = ["准时率(%)", "订单数"]
            forwarder_stats_air = forwarder_stats_air.sort_values("准时率(%)", ascending=False)

            fig_forwarder_air = px.bar(
                forwarder_stats_air,
                x=forwarder_stats_air.index,
                y="准时率(%)",
                title="各货代空派准时率",
                color="订单数",
                color_continuous_scale=px.colors.sequential.Blues
            )
            fig_forwarder_air.update_layout(height=400)
            st.plotly_chart(fig_forwarder_air, use_container_width=True)

        with col_d:
            st.dataframe(
                forwarder_stats_air,
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
    else:
        st.info("空派暂无货代准时率数据")

    st.divider()

    # 空派仓库分析
    st.subheader("空派-仓库准时情况分析")
    if "仓库" in df_current_air.columns and "提前/延期" in df_current_air.columns and not df_current_air.empty:
        col_e, col_f = st.columns([1, 1])

        with col_e:
            warehouse_stats_air = df_current_air.groupby("仓库").agg({
                "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100 if len(x) > 0 else 0,
                "FBA号": "count"
            }).round(2)
            warehouse_stats_air.columns = ["准时率(%)", "订单数"]
            warehouse_stats_air = warehouse_stats_air.sort_values("准时率(%)", ascending=False)

            fig_warehouse_air = px.bar(
                warehouse_stats_air,
                x=warehouse_stats_air.index,
                y="准时率(%)",
                title="各仓库空派准时率",
                color="订单数",
                color_continuous_scale=px.colors.sequential.Oranges
            )
            fig_warehouse_air.update_layout(height=400)
            st.plotly_chart(fig_warehouse_air, use_container_width=True)

        with col_f:
            st.dataframe(
                warehouse_stats_air,
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
    else:
        st.info("空派暂无仓库准时率数据")

    st.divider()

    # 空派趋势分析
    st.subheader("空派-不同月份趋势分析（货代/仓库维度）")
    if not df_air.empty and "年月_str" in df_air.columns:
        trend_dim_air = st.radio("空派-趋势分析维度", ["货代维度", "仓库维度"], horizontal=True, key="air_trend")
        trend_col_air = "货代" if trend_dim_air == "货代维度" else "仓库"

        if trend_col_air in df_air.columns:
            trend_data_air = df_air.groupby(["年月_str", trend_col_air]).agg({
                "FBA号": "count",
                "提前/延期": lambda x: (x.isin(["提前", "准时"]).sum() / len(x)) * 100 if len(x) > 0 else 0
            }).round(2)
            trend_data_air.columns = ["订单数", "准时率(%)"]
            trend_data_air = trend_data_air.reset_index()

            fig_trend_air = px.line(
                trend_data_air,
                x="年月_str",
                y="准时率(%)",
                color=trend_col_air,
                title=f"空派-不同月份准时率趋势（{trend_dim_air}）",
                markers=True
            )
            fig_trend_air.update_layout(height=500)
            st.plotly_chart(fig_trend_air, use_container_width=True)

            st.dataframe(
                trend_data_air,
                use_container_width=True,
                column_config={
                    "准时率(%)": st.column_config.NumberColumn(format="%.1f")
                }
            )
        else:
            st.info(f"空派暂无{trend_col_air}维度数据")
    else:
        st.info("空派暂无趋势分析数据")


# ======================== 主程序入口（无切换，直接展示红单+空派） ========================
def main():
    """主程序：同一页面展示红单+空派完整分析"""
    # 第一步：展示红单分析模块
    red_analysis_module()

    # 第二步：从侧边栏获取空派筛选参数
    selected_month_air = st.session_state.get("air_month", "")
    order_filter = st.session_state.get("order_filter", "全部订单")
    view_type = st.session_state.get("view_type", "汇总视图")

    # 第三步：直接展示空派分析模块（红单下方）
    air_analysis_module(selected_month_air, order_filter, view_type)


# 运行程序
if __name__ == "__main__":
    # 检查依赖
    try:
        from streamlit_extras.dataframe_explorer import dataframe_explorer
    except ImportError:
        st.error("请先安装依赖：pip install streamlit-extras openpyxl pandas plotly numpy")
        st.stop()

    main()