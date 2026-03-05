import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
import base64

# 页面配置（完全保留）
st.set_page_config(
    page_title="FBA海运物流交期分析看板",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------- 工具函数（完全保留你的原有代码） ----------------------
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
        if pd.isna(val) or val == "-" or str(val).strip() == "":
            return ""
        val_str = str(val).replace('%', '').strip()
        val_num = float(val_str)
        if val_num > 0:
            return "color: red"
        elif val_num < 0:
            return "color: green"
    except:
        pass
    return ""

def get_table_download_link(df, filename, text):
    """生成表格下载链接"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='FBA海运明细')
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
    return href

# ---------------------- 数据加载函数（两份数据逻辑） ----------------------
@st.cache_data
def load_data():
    url = "https://github.com/Jane-zzz-123/Logistics/raw/main/Logisticsdata.xlsx"
    try:
        df_all = pd.read_excel(url, sheet_name="上架完成-海运")  # 全部数据
    except Exception as e:
        st.error(f"读取数据失败：{str(e)}")
        return pd.DataFrame(), pd.DataFrame()

    # 处理「是否为异常数据」列
    abnormal_col = "是否为异常数据"
    if abnormal_col in df_all.columns:
        df_all[abnormal_col] = df_all[abnormal_col].str.strip().fillna("否")
        df_all[abnormal_col] = df_all[abnormal_col].replace({
            "异常数据": "是", "正常数据": "否", "异常": "是", "正常": "否"
        })
        df_clean = df_all[df_all[abnormal_col] == "否"].copy()  # 纯净数据
    else:
        df_all[abnormal_col] = "否"
        df_clean = df_all.copy()
        st.warning(f"未找到「{abnormal_col}」列，已默认全部为正常数据（否）")

    # 核心列筛选
    core_columns = [
        "FBA号", "区域", "计划物流方式", "店铺", "仓库", "货代", "异常备注",
        "发货-开船", "开船-到港", "到港-提柜", "提柜-签收", "签收-完成上架",
        "到货年月", "签收-发货时间", "上架完成-发货时间",
        "预计物流时效-实际物流时效差值(绝对值)",
        "预计物流时效-实际物流时效差值", "提前/延期",
        "预计物流时效-实际物流时效差值（货代）",
        "提前/延期（货代）", "提前/延期（仓库）", abnormal_col
    ]
    existing_columns = [col for col in core_columns if col in df_all.columns]
    missing_columns = [col for col in core_columns if col not in df_all.columns]
    if missing_columns:
        st.warning(f"以下列不存在，已忽略：{missing_columns}")
    df_all = df_all[existing_columns]
    df_clean = df_clean[existing_columns]

    # 统一到货年月格式
    df_all["到货年月"] = pd.to_datetime(df_all["到货年月"], errors='coerce').dt.strftime("%Y-%m")
    df_clean["到货年月"] = pd.to_datetime(df_clean["到货年月"], errors='coerce').dt.strftime("%Y-%m")
    df_all = df_all.dropna(subset=["到货年月"])
    df_clean = df_clean.dropna(subset=["到货年月"])

    # 清洗数值列
    abs_diff_col = "预计物流时效-实际物流时效差值(绝对值)"
    real_diff_col = "预计物流时效-实际物流时效差值"
    if abs_diff_col in df_all.columns:
        df_all[abs_diff_col] = pd.to_numeric(df_all[abs_diff_col], errors='coerce').fillna(0)
        df_clean[abs_diff_col] = pd.to_numeric(df_clean[abs_diff_col], errors='coerce').fillna(0)
    if real_diff_col in df_all.columns:
        df_all[real_diff_col] = pd.to_numeric(df_all[real_diff_col], errors='coerce').fillna(0)
        df_clean[real_diff_col] = pd.to_numeric(df_clean[real_diff_col], errors='coerce').fillna(0)

    return df_all, df_clean

# ---------------------- 主程序逻辑 ----------------------
# 1. 加载两份基础数据
df_all, df_clean = load_data()
if df_all.empty:
    st.error("暂无可用数据，请检查数据源或列名！")
    st.stop()

# 2. 顶部筛选按钮
st.header("FBA海运物流交期分析看板")
data_filter = st.radio(
    "📊 选择数据范围：",
    options=["全部数据", "纯净数据（剔除异常）"],
    index=0,
    horizontal=True,
    key="data_filter"
)

# 3. 核心：按钮切换数据（统一变量df_selected）
if data_filter == "纯净数据（剔除异常）":
    df_selected = df_clean.copy()
    exclude_count = len(df_all) - len(df_clean)
    st.success(f"✅ 已筛选为纯净数据，剔除 {exclude_count} 条异常数据（全局），当前共 {len(df_selected)} 条记录")
else:
    df_selected = df_all.copy()
    abnormal_count_total = len(df_all[df_all["是否为异常数据"] == "是"])
    st.info(f"ℹ️ 当前展示全部数据（全局），共 {len(df_selected)} 条记录（含 {abnormal_count_total} 条异常数据）")

# 4. 数据预览
st.subheader("筛选后数据预览")
abnormal_col = "是否为异常数据"
preview_cols = [abnormal_col, "FBA号", "到货年月", "异常备注"]
preview_cols = [col for col in preview_cols if col in df_selected.columns]
st.dataframe(df_selected[preview_cols].head(20), use_container_width=True)

# 5. 主看板区域
st.title("🚢 FBA海运分析看板区域")
st.divider()

# 6. 当月数据筛选（基于df_selected，不会丢数据）
st.subheader("🔍 当月FBA海运分析")
month_options = sorted(df_selected["到货年月"].unique(), reverse=True)
if not month_options:
    st.warning("⚠️ 暂无可用的到货年月数据")
    st.stop()

selected_month = st.selectbox(
    "选择到货年月",
    options=month_options,
    index=0,
    key="month_selector_current"
)
st.subheader("")  # 空行分隔，优化排版
# 获取所有计划物流方式选项（去重），并添加“全部”选项
logistics_methods = ['全部'] + list(df_selected['计划物流方式'].dropna().unique())
# 创建下拉筛选器，默认选中“全部”
selected_logistics = st.selectbox(
    "选择计划物流方式",
    options=logistics_methods,
    index=0,  # 默认选中第一个选项（全部）
    key="logistics_filter"  # 唯一key，避免streamlit缓存冲突
)

# 7. 当月数据（基于选中的df_selected + 计划物流方式筛选）
df_current = df_selected[df_selected["到货年月"] == selected_month].copy()
# 新增：过滤计划物流方式
if selected_logistics != '全部':
    df_current = df_current[df_current['计划物流方式'] == selected_logistics].copy()

# 8. 上月数据（基于df_selected + 计划物流方式筛选）
prev_month = get_prev_month(selected_month)
df_prev = df_selected[df_selected["到货年月"] == prev_month].copy() if prev_month and prev_month in month_options else pd.DataFrame()
# 新增：过滤计划物流方式（上月数据同步筛选）
if selected_logistics != '全部' and not df_prev.empty:
    df_prev = df_prev[df_prev['计划物流方式'] == selected_logistics].copy()

# 9. 当月异常数据统计（同步筛选计划物流方式）
# 第一步：先筛选年月
abnormal_filter = (df_all["到货年月"] == selected_month) & (df_all["是否为异常数据"] == "是")
# 第二步：如果选了具体物流方式，再叠加筛选
if selected_logistics != '全部':
    abnormal_filter = abnormal_filter & (df_all["计划物流方式"] == selected_logistics)
# 第三步：计算符合条件的异常数据条数
abnormal_current_month = len(df_all[abnormal_filter])
# 当月提示（新增物流方式说明）
logistics_tip = f"，筛选物流方式：{selected_logistics}" if selected_logistics != "全部" else ""
if data_filter == "纯净数据（剔除异常）":
    st.info(f"📌 【{selected_month}】已筛选为纯净数据，剔除 {abnormal_current_month} 条异常数据{logistics_tip}，当前共 {len(df_current)} 条记录")
else:
    st.info(f"📌 【{selected_month}】当前显示全部数据{logistics_tip}，共 {len(df_current)} 条记录（含 {abnormal_current_month} 条异常数据）")

# ---------------------- 你的核心指标/可视化/表格代码（仅改数据源引用） ----------------------
# ---------------------- ① 核心指标卡片 ----------------------
st.markdown("### 核心指标")

# 计算核心指标
# 1. FBA单数
current_fba = len(df_current)
prev_fba = len(df_prev) if not df_prev.empty else 0
fba_change = current_fba - prev_fba
fba_change_text = f"{'↑' if fba_change > 0 else '↓' if fba_change < 0 else '—'} {abs(fba_change)} (上月: {prev_fba})"
fba_change_color = "red" if fba_change > 0 else "green" if fba_change < 0 else "gray"

# 2. 提前/准时数（修复：匹配实际数据中的值，比如可能是"提前"或"准时"分开存储）
# 兼容处理：如果数据中是"提前"和"准时"分开，合并统计
if "提前/延期" in df_current.columns:
    # 适配不同的数据值：支持"提前/准时"、"提前"、"准时"三种情况
    current_on_time = len(df_current[df_current["提前/延期"].isin(["提前/准时", "提前", "准时"])])
else:
    current_on_time = 0

if not df_prev.empty and "提前/延期" in df_prev.columns:
    prev_on_time = len(df_prev[df_prev["提前/延期"].isin(["提前/准时", "提前", "准时"])])
else:
    prev_on_time = 0

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
    core_conclusion = f"{selected_month}FBA海运物流整体表现优秀，准时率达{on_time_rate:.1f}%，远高于行业基准"
elif on_time_rate >= 80:
    core_conclusion = f"{selected_month}FBA海运物流表现良好，准时率{on_time_rate:.1f}%，整体可控"
elif on_time_rate >= 70:
    core_conclusion = f"{selected_month}FBA海运物流表现一般，准时率{on_time_rate:.1f}%，需关注延期问题"
else:
    core_conclusion = f"{selected_month}FBA海运物流表现较差，准时率仅{on_time_rate:.1f}%，延期风险显著"

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
### {selected_month}FBA海运物流核心分析
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
        # 兼容数据值：合并"提前/准时"、"提前"、"准时"为同一类别
        df_current["提前/延期_分类"] = df_current["提前/延期"].apply(
            lambda x: "提前/准时" if x in ["提前/准时", "提前", "准时"] else "延期" if x == "延期" else "其他"
        )
        pie_data = df_current["提前/延期_分类"].value_counts()

        # 确保颜色映射严格生效（显式指定颜色列表）
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
            title=f"{selected_month} FBA海运准时率分布",
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
# ---------------------- ③ 当月FBA海运明细表格 ----------------------
st.markdown("### FBA海运明细（含平均值）")

# 准备明细数据
detail_cols = [
    "到货年月", "提前/延期", "FBA号", "计划物流方式", "店铺", "仓库", "货代",
    # 新增的物流阶段列（加在货代右边）
    "发货-开船", "开船-到港", "到港-提柜", "提柜-签收", "签收-完成上架",
    "签收-发货时间", "上架完成-发货时间", "提前/延期（货代）",
    "提前/延期（仓库）",
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
        "发货-开船", "开船-到港", "到港-提柜", "提柜-签收", "签收-完成上架",
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
        elif col in ["提前/延期", "FBA号", "店铺", "仓库", "货代", "计划物流方式", "提前/延期（货代）",
                     "提前/延期（仓库）"]:
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
    # 构建带平均值的完整数据（用于下载）
    df_download = pd.concat([pd.DataFrame([avg_row]), df_detail], ignore_index=True)

    # 显示下载按钮
    st.markdown(
        get_table_download_link(
            df_download,
            f"FBA海运明细_{selected_month}.xlsx",
            "📥 下载FBA海运明细表格（Excel格式）"
        ),
        unsafe_allow_html=True
    )

else:
    st.write("⚠️ 暂无明细数据")

st.divider()
# --------------------------
# 1. 数据预处理 & 字段定义（核心：匹配你的业务逻辑）
# --------------------------
st.subheader("📝 延期订单深度归因分析")

# 请确认以下字段名与你的数据完全一致！
main_delay_col = "提前/延期"  # 总提前/延期列
forwarder_delay_col = "提前/延期（货代）"  # 货代延期分类列
warehouse_delay_col = "提前/延期（仓库）"  # 仓库延期分类列
# 环节字段定义
forwarder_stage_cols = [  # 货代负责的环节
    "发货-开船",
    "开船-到港",
    "到港-提柜",
    "提柜-签收"
]
warehouse_stage_col = "签收-完成上架"  # 仓库负责的环节（单独列）
all_stage_cols = forwarder_stage_cols + [warehouse_stage_col]  # 所有环节

# 1.1 基础字段清洗（统一格式，避免筛选错误）
df_current[main_delay_col] = df_current[main_delay_col].fillna("未知").apply(
    lambda x: x.strip() if isinstance(x, str) else "未知")
df_current[forwarder_delay_col] = df_current[forwarder_delay_col].fillna("未知").apply(
    lambda x: x.strip() if isinstance(x, str) else "未知")
df_current[warehouse_delay_col] = df_current[warehouse_delay_col].fillna("未知").apply(
    lambda x: x.strip() if isinstance(x, str) else "未知")

# 1.2 环节字段数值化（确保均值计算准确）
for col in all_stage_cols:
    df_current[col] = pd.to_numeric(df_current[col], errors="coerce").fillna(0.0)

# --------------------------
# 2. 严格按业务逻辑筛选数据集
# --------------------------
# 2.1 正常订单集：总状态=提前/准时
df_normal = df_current[df_current[main_delay_col] == "提前/准时"].copy()
# 2.2 货代延期订单集：总状态=延期 + 货代状态=延期
df_forwarder_delay = df_current[
    (df_current[main_delay_col] == "延期") &
    (df_current[forwarder_delay_col] == "延期")
    ].copy()
# 2.3 仓库延期订单集：总状态=延期 + 仓库状态=延期
df_warehouse_delay = df_current[
    (df_current[main_delay_col] == "延期") &
    (df_current[warehouse_delay_col] == "延期")
    ].copy()
# 2.4 总延期订单数（用于占比计算）
df_total_delay = df_current[df_current[main_delay_col] == "延期"].copy()
total_delay = len(df_total_delay)
total_normal = len(df_normal)
total_current = len(df_current)

# --------------------------
# 3. 无延期订单时的展示
# --------------------------
if total_delay == 0:
    st.success("✅ 本月无延期订单，各物流环节时效均符合预期！")
    # 仅展示正常订单的各环节均值
    st.markdown("### 📈 正常订单各环节耗时均值")
    normal_mean = df_normal[all_stage_cols].mean().round(2)
    for stage in forwarder_stage_cols:
        st.markdown(f"- **{stage}**：{float(normal_mean[stage])} 天")
    st.markdown(f"- **{warehouse_stage_col}**：{float(normal_mean[warehouse_stage_col])} 天")
else:
    # --------------------------
    # 4. 统计货代/仓库延期订单数（精准匹配）
    # --------------------------
    forwarder_count = int(len(df_forwarder_delay))
    warehouse_count = int(len(df_warehouse_delay))
    other_count = int(total_delay - forwarder_count - warehouse_count)  # 其他原因

    # 计算占比（纯Python原生计算，防错）
    forwarder_pct = round((forwarder_count / total_delay) * 100, 1) if total_delay > 0 else 0.0
    warehouse_pct = round((warehouse_count / total_delay) * 100, 1) if total_delay > 0 else 0.0
    other_pct = round((other_count / total_delay) * 100, 1) if total_delay > 0 else 0.0
    normal_pct = round((total_normal / total_current) * 100, 1) if total_current > 0 else 0.0
    delay_pct = round((total_delay / total_current) * 100, 1) if total_current > 0 else 0.0

    # --------------------------
    # 5. 基础数据汇总
    # --------------------------
    st.markdown(f"""
    ### 📊 基础数据
    - 当月总订单数：{total_current} 单
    - 正常订单数：{total_normal} 单（占比 {normal_pct}%）
    - 延期订单数：{total_delay} 单（占比 {delay_pct}%）
    """)

    # --------------------------
    # 6. 货代/仓库延期占比
    # --------------------------
    st.markdown("### 🎯 延期订单主因占比")
    st.markdown(f"- **货代原因**：{forwarder_count} 单（占延期订单的 {forwarder_pct}%）")
    st.markdown(f"- **仓库原因**：{warehouse_count} 单（占延期订单的 {warehouse_pct}%）")
    st.markdown(f"- **其他原因**：{other_count} 单（占延期订单的 {other_pct}%）")

    # --------------------------
    # 7. 严格按你的逻辑计算各环节均值（核心！）
    # --------------------------
    st.markdown("### 📈 各环节耗时均值（按业务逻辑计算）")

    # 7.1 正常订单的所有环节均值（总状态=提前/准时）
    st.markdown("#### 🔹 正常订单（提前/准时）")
    normal_mean = df_normal[all_stage_cols].mean().round(2)
    for stage in forwarder_stage_cols:
        st.markdown(f"- **{stage}**：{float(normal_mean[stage])} 天")
    st.markdown(f"- **{warehouse_stage_col}**：{float(normal_mean[warehouse_stage_col])} 天")

    # 7.2 货代延期的货代环节均值（总状态=延期 + 货代=延期 → 仅货代环节）
    st.markdown("#### 🔹 货代延期订单（总延期+货代延期）")
    if forwarder_count > 0:
        forwarder_delay_mean = df_forwarder_delay[forwarder_stage_cols].mean().round(2)
        for stage in forwarder_stage_cols:
            n_mean = float(normal_mean[stage])
            d_mean = float(forwarder_delay_mean[stage])
            diff_pct = round(((d_mean - n_mean) / n_mean) * 100, 1) if n_mean > 0 else 0.0
            st.markdown(f"""
            - **{stage}**：
              均值：{d_mean} 天 | 
              对比正常偏差：{diff_pct:+}%
            """)
    else:
        st.markdown("- 无货代延期订单")

    # 7.3 仓库延期的仓库环节均值（总状态=延期 + 仓库=延期 → 仅仓库环节）
    st.markdown("#### 🔹 仓库延期订单（总延期+仓库延期）")
    if warehouse_count > 0:
        warehouse_delay_mean = df_warehouse_delay[warehouse_stage_col].mean().round(2)
        n_mean = float(normal_mean[warehouse_stage_col])
        d_mean = float(warehouse_delay_mean)
        diff_pct = round(((d_mean - n_mean) / n_mean) * 100, 1) if n_mean > 0 else 0.0
        st.markdown(f"""
        - **{warehouse_stage_col}**：
          均值：{d_mean} 天 | 
          对比正常偏差：{diff_pct:+}%
        """)
    else:
        st.markdown("- 无仓库延期订单")

    # --------------------------
    # 8. 针对性优化建议
    # --------------------------
    st.markdown("### 💡 优化建议")
    suggestions = []
    if forwarder_count > 0:
        suggestions.append(
            f"针对货代延期：{forwarder_count} 单订单因货代环节延期，货代环节均值较正常偏高{diff_pct:+}%，建议与货代明确各环节时效标准，建立延期追责机制。")
    if warehouse_count > 0:
        suggestions.append(
            f"针对仓库延期：{warehouse_count} 单订单因仓库环节延期，「{warehouse_stage_col}」均值 {d_mean} 天（正常 {n_mean} 天，偏高{diff_pct:+}%），建议优化FBA上架预约及仓内操作流程。")
    if other_count > 0:
        suggestions.append(
            f"针对其他原因：{other_count} 单延期订单无明确货代/仓库责任，建议核查订单基础信息或外部政策、天气等因素。")

    for idx, suggestion in enumerate(suggestions, 1):
        st.markdown(f"{idx}. {suggestion}")