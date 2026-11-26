
import shutil
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from auth import require_login
from ai_analyst import generate_business_report, answer_business_question
from pdf_report import generate_business_pdf
from forecasting import forecast_sales

st.set_page_config(page_title="AI 企业经营分析平台", page_icon="📊", layout="wide")

if not require_login():
    st.stop()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
ORIGINAL_FILE = DATA_DIR / "Sample - Superstore.csv"
ACTIVE_FILE = DATA_DIR / "active_data.csv"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = [
    "order_id", "order_date", "store", "category", "product",
    "quantity", "unit_price", "discount", "revenue", "cost",
    "profit", "region", "state", "sub_category", "customer_id",
    "ship_mode"
]

COLUMN_ALIASES = {
    "order_id": ["order_id", "订单编号", "订单ID", "Order ID"],
    "order_date": ["order_date", "订单日期", "日期", "Order Date"],
    "store": ["store", "city", "城市", "门店", "地区"],
    "category": ["category", "类别", "商品类别", "Category"],
    "product": ["product", "product_name", "商品", "商品名称", "Product Name"],
    "quantity": ["quantity", "数量", "销量", "Quantity"],
    "unit_price": ["unit_price", "单价", "商品单价"],
    "discount": ["discount", "折扣", "Discount"],
    "revenue": ["revenue", "sales", "销售额", "营业额", "Sales"],
    "cost": ["cost", "成本", "总成本"],
    "profit": ["profit", "利润", "Profit"],
    "region": ["region", "区域", "Region"],
    "state": ["state", "省份", "州", "State"],
    "sub_category": ["sub_category", "subcategory", "子类别", "Sub-Category"],
    "customer_id": ["customer_id", "客户编号", "客户ID", "Customer ID"],
    "ship_mode": ["ship_mode", "shipping_mode", "配送方式", "Ship Mode"]
}


def format_money(value):
    return f"${value:,.2f}"


def normalize_column_name(value):
    return re.sub(r"[\s_\-]+", "", str(value).strip().lower())


def map_columns(df):
    normalized = {
        normalize_column_name(column): column
        for column in df.columns
    }
    rename_map = {}

    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = normalize_column_name(alias)
            if key in normalized:
                rename_map[normalized[key]] = target
                break

    return df.rename(columns=rename_map)


def clean_data(df):
    df = df.copy()
    df = map_columns(df)

    if "order_date" not in df.columns:
        raise ValueError("缺少订单日期字段，请检查文件中的日期列。")

    if "revenue" not in df.columns:
        raise ValueError("缺少销售额字段，请检查文件中的销售额列。")

    if "profit" not in df.columns and "cost" not in df.columns:
        raise ValueError("至少需要提供利润或成本字段。")

    defaults = {
        "order_id": "",
        "store": "未分类",
        "category": "未分类",
        "product": "未命名商品",
        "quantity": 1,
        "unit_price": None,
        "discount": 0,
        "cost": None,
        "region": "未分类",
        "state": "未分类",
        "sub_category": "未分类",
        "customer_id": "未分类",
        "ship_mode": "未分类"
    }

    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    numeric_columns = ["quantity", "unit_price", "discount", "revenue", "cost", "profit"]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "profit" not in df.columns:
        df["profit"] = df["revenue"] - df["cost"]

    if "cost" not in df.columns:
        df["cost"] = df["revenue"] - df["profit"]

    if "unit_price" not in df.columns or df["unit_price"].isna().all():
        df["unit_price"] = df["revenue"] / df["quantity"].replace(0, pd.NA)

    for column in [
        "order_id", "store", "category", "product", "region",
        "state", "sub_category", "customer_id", "ship_mode"
    ]:
        df[column] = df[column].fillna("未分类").astype(str)

    invalid_date = df["order_date"].isna()
    invalid_revenue = df["revenue"].isna()
    invalid_profit = df["profit"].isna()
    invalid_quantity = df["quantity"].isna() | (df["quantity"] <= 0)

    invalid_mask = invalid_date | invalid_revenue | invalid_profit | invalid_quantity

    report = {
        "total": len(df),
        "invalid_date": int(invalid_date.sum()),
        "invalid_revenue": int(invalid_revenue.sum()),
        "invalid_profit": int(invalid_profit.sum()),
        "invalid_quantity": int(invalid_quantity.sum()),
        "invalid_total": int(invalid_mask.sum())
    }

    df = df.loc[~invalid_mask].copy()

    if df.empty:
        raise ValueError("清洗后没有有效数据，请检查上传文件。")

    df["unit_price"] = df["unit_price"].fillna(
        df["revenue"] / df["quantity"].replace(0, pd.NA)
    )

    df["discount"] = df["discount"].fillna(0)

    return df[REQUIRED_COLUMNS].reset_index(drop=True), report


def load_real_data():
    if ACTIVE_FILE.exists():
        raw = pd.read_csv(ACTIVE_FILE, encoding="utf-8-sig")
        return clean_data(raw)[0]

    if not ORIGINAL_FILE.exists():
        raise FileNotFoundError("未找到原始数据文件，请检查 data 文件夹。")

    raw = pd.read_csv(ORIGINAL_FILE, encoding="cp1252")

    quantity = pd.to_numeric(raw["Quantity"], errors="coerce")
    sales = pd.to_numeric(raw["Sales"], errors="coerce")
    profit = pd.to_numeric(raw["Profit"], errors="coerce")

    df = pd.DataFrame({
        "order_id": raw["Order ID"].astype(str),
        "order_date": pd.to_datetime(raw["Order Date"], errors="coerce"),
        "store": raw["City"].astype(str),
        "category": raw["Category"].astype(str),
        "product": raw["Product Name"].astype(str),
        "quantity": quantity,
        "unit_price": sales / quantity.replace(0, pd.NA),
        "discount": pd.to_numeric(raw["Discount"], errors="coerce"),
        "revenue": sales,
        "cost": sales - profit,
        "profit": profit,
        "region": raw["Region"].astype(str),
        "state": raw["State"].astype(str),
        "sub_category": raw["Sub-Category"].astype(str),
        "customer_id": raw["Customer ID"].astype(str),
        "ship_mode": raw["Ship Mode"].astype(str)
    })

    return clean_data(df)[0]


def read_uploaded_file(uploaded_file):
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        try:
            raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            raw = pd.read_csv(uploaded_file, encoding="cp1252")
    elif file_name.endswith((".xlsx", ".xls")):
        raw = pd.read_excel(uploaded_file)
    else:
        raise ValueError("仅支持 CSV、XLSX 和 XLS 文件。")

    return clean_data(raw)


def render_data_management():
    if st.session_state.get("role") != "admin":
        return

    st.divider()
    st.header("🗂️ 数据管理中心")
    st.caption("管理员专属功能：上传、检查、预览和导入经营数据。")

    with st.container(border=True):
        st.subheader("上传经营数据")

        uploaded_file = st.file_uploader(
            "选择 CSV 或 Excel 文件",
            type=["csv", "xlsx", "xls"],
            key="business_data_upload"
        )

        if uploaded_file is not None:
            st.info(f"已选择文件：{uploaded_file.name}")

            if st.button("检查并预览数据", type="primary"):
                try:
                    preview_df, report = read_uploaded_file(uploaded_file)
                    st.session_state["import_preview"] = preview_df
                    st.session_state["import_report"] = report
                    st.session_state["import_filename"] = uploaded_file.name
                    st.success("数据检查完成，请确认预览结果。")
                except Exception as error:
                    st.session_state.pop("import_preview", None)
                    st.session_state.pop("import_report", None)
                    st.error(f"文件检查失败：{error}")

        preview_df = st.session_state.get("import_preview")
        report = st.session_state.get("import_report")

        if preview_df is not None and report is not None:
            st.divider()
            st.subheader("数据质量检查结果")

            a, b, c, d = st.columns(4)
            a.metric("原始记录数", f"{report['total']:,}")
            b.metric("有效记录数", f"{len(preview_df):,}")
            c.metric("异常记录数", f"{report['invalid_total']:,}")
            d.metric("导入后字段数", len(preview_df.columns))

            st.write({
                "日期异常": report["invalid_date"],
                "销售额异常": report["invalid_revenue"],
                "利润异常": report["invalid_profit"],
                "销量异常": report["invalid_quantity"]
            })

            st.subheader("数据预览")
            st.dataframe(preview_df.head(30), use_container_width=True, hide_index=True)

            st.caption(
                "系统会自动清除日期、销售额、利润或销量无效的记录。"
                "导入后将使用标准字段结构保存数据。"
            )

            confirm = st.checkbox(
                "我已检查数据预览，确认使用这份数据替换当前经营数据。",
                key="confirm_data_import"
            )

            if st.button("确认导入数据", disabled=not confirm, type="primary"):
                try:
                    if ACTIVE_FILE.exists():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_file = BACKUP_DIR / f"active_data_{timestamp}.csv"
                        shutil.copy2(ACTIVE_FILE, backup_file)
                    elif ORIGINAL_FILE.exists():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_file = BACKUP_DIR / f"original_data_{timestamp}.csv"
                        shutil.copy2(ORIGINAL_FILE, backup_file)

                    preview_df.to_csv(ACTIVE_FILE, index=False, encoding="utf-8-sig")

                    from auth import log_event
                    log_event(
                        st.session_state.get("username", "unknown"),
                        "导入经营数据",
                        f"文件：{st.session_state.get('import_filename', '')}，记录数：{len(preview_df)}"
                    )

                    st.session_state.pop("import_preview", None)
                    st.session_state.pop("import_report", None)
                    st.session_state.pop("import_filename", None)
                    st.session_state.pop("confirm_data_import", None)

                    st.success("数据导入成功，原始数据已备份。")
                    st.rerun()

                except Exception as error:
                    st.error(f"导入失败：{error}")

    with st.container(border=True):
        st.subheader("当前数据与备份")

        if ACTIVE_FILE.exists():
            st.success("当前使用：管理员导入的数据")
        else:
            st.info("当前使用：项目自带 Sample Superstore 原始数据")

        backup_files = sorted(
            BACKUP_DIR.glob("*.csv"),
            key=lambda item: item.stat().st_mtime,
            reverse=True
        )

        st.metric("本地备份文件数量", len(backup_files))

        if backup_files:
            backup_table = pd.DataFrame([
                {
                    "备份文件": item.name,
                    "文件大小": f"{item.stat().st_size / 1024:.1f} KB",
                    "备份时间": datetime.fromtimestamp(
                        item.stat().st_mtime
                    ).strftime("%Y-%m-%d %H:%M:%S")
                }
                for item in backup_files[:20]
            ])

            st.dataframe(backup_table, use_container_width=True, hide_index=True)

            selected_backup = st.selectbox(
                "选择需要恢复的备份",
                backup_files,
                format_func=lambda item: item.name
            )

            restore_confirm = st.checkbox(
                "确认用选中的备份替换当前经营数据。",
                key="confirm_restore"
            )

            if st.button("恢复选中的备份", disabled=not restore_confirm):
                try:
                    if ACTIVE_FILE.exists():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        shutil.copy2(
                            ACTIVE_FILE,
                            BACKUP_DIR / f"before_restore_{timestamp}.csv"
                        )

                    restored_df = pd.read_csv(selected_backup, encoding="utf-8-sig")
                    restored_df, _ = clean_data(restored_df)
                    restored_df.to_csv(
                        ACTIVE_FILE,
                        index=False,
                        encoding="utf-8-sig"
                    )

                    from auth import log_event
                    log_event(
                        st.session_state.get("username", "unknown"),
                        "恢复经营数据备份",
                        f"备份文件：{selected_backup.name}"
                    )

                    st.success("数据恢复成功。")
                    st.rerun()

                except Exception as error:
                    st.error(f"备份恢复失败：{error}")


st.title("📊 AI 企业经营分析平台")
st.caption("基于真实零售交易数据的企业经营分析与智能决策系统")

render_data_management()

try:
    df = load_real_data()
except Exception as error:
    st.error(f"数据加载失败：{error}")
    st.stop()

with st.sidebar:
    st.header("数据管理")
    st.success(f"已加载 {len(df):,} 条数据")
    st.caption(
        "当前数据来源：" +
        ("管理员导入数据" if ACTIVE_FILE.exists() else "Sample Superstore")
    )
    st.divider()
    st.header("分析筛选")

    min_date = df["order_date"].min().date()
    max_date = df["order_date"].max().date()

    date_range = st.date_input(
        "日期范围",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    stores = sorted(df["store"].unique().tolist())
    categories = sorted(df["category"].unique().tolist())

    selected_stores = st.multiselect("城市", stores, default=stores)
    selected_categories = st.multiselect("商品类别", categories, default=categories)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered_df = df[
    (df["order_date"].dt.date >= start_date)
    & (df["order_date"].dt.date <= end_date)
    & (df["store"].isin(selected_stores))
    & (df["category"].isin(selected_categories))
].copy()

if filtered_df.empty:
    st.warning("当前筛选条件下没有数据，请调整筛选条件。")
    st.stop()

revenue = filtered_df["revenue"].sum()
profit = filtered_df["profit"].sum()
orders = filtered_df["order_id"].nunique()
quantity = filtered_df["quantity"].sum()
margin = profit / revenue if revenue else 0

st.subheader("核心经营指标")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("销售总额", format_money(revenue))
c2.metric("利润总额", format_money(profit))
c3.metric("利润率", f"{margin:.2%}")
c4.metric("订单数量", f"{orders:,}")
c5.metric("商品销量", f"{quantity:,.0f}")

st.divider()
st.subheader("📈 经营数据对比分析")
st.caption("按月度、季度或年度汇总经营表现，并与上一周期比较变化额和变化率。")

comparison_type = st.radio(
    "对比周期",
    ["月度", "季度", "年度"],
    horizontal=True,
    key="business_comparison_type"
)

comparison_data = df[
    df["store"].isin(selected_stores)
    & df["category"].isin(selected_categories)
].copy()

if comparison_type == "月度":
    comparison_data["对比周期"] = comparison_data["order_date"].dt.to_period("M").astype(str)
elif comparison_type == "季度":
    comparison_data["对比周期"] = comparison_data["order_date"].dt.to_period("Q").astype(str)
else:
    comparison_data["对比周期"] = comparison_data["order_date"].dt.to_period("Y").astype(str)

comparison_data = comparison_data[
    (comparison_data["order_date"].dt.date >= start_date)
    & (comparison_data["order_date"].dt.date <= end_date)
]

comparison_summary = (
    comparison_data.groupby("对比周期")
    .agg(
        销售额=("revenue", "sum"),
        利润=("profit", "sum"),
        订单数=("order_id", "nunique"),
        销量=("quantity", "sum")
    )
    .reset_index()
    .sort_values("对比周期")
)

if not comparison_summary.empty:
    comparison_summary["利润率"] = comparison_summary.apply(
        lambda row: row["利润"] / row["销售额"] if row["销售额"] else 0,
        axis=1
    )

    comparison_metrics = ["销售额", "利润", "利润率", "订单数", "销量"]

    for metric in comparison_metrics:
        comparison_summary[f"{metric}变化额"] = comparison_summary[metric].diff()
        previous_values = comparison_summary[metric].shift(1)
        comparison_summary[f"{metric}变化率"] = (
            (comparison_summary[metric] - previous_values)
            / previous_values.abs().replace(0, pd.NA)
        )

    comparison_summary = comparison_summary.replace([float("inf"), float("-inf")], pd.NA)

    display_comparison = comparison_summary.copy()

    for metric in ["销售额", "利润", "销售额变化额", "利润变化额"]:
        display_comparison[metric] = display_comparison[metric].map(
            lambda value: "" if pd.isna(value) else f"${value:,.2f}"
        )

    for metric in ["利润率", "利润率变化额", "销售额变化率", "利润变化率", "利润率变化率", "订单数变化率", "销量变化率"]:
        if metric in display_comparison.columns:
            display_comparison[metric] = display_comparison[metric].map(
                lambda value: "" if pd.isna(value) else f"{value:.2%}"
            )

    for metric in ["订单数", "销量", "订单数变化额", "销量变化额"]:
        display_comparison[metric] = display_comparison[metric].map(
            lambda value: "" if pd.isna(value) else f"{value:,.0f}"
        )

    display_columns = [
        "对比周期", "销售额", "销售额变化额", "销售额变化率",
        "利润", "利润变化额", "利润变化率",
        "利润率", "利润率变化额", "利润率变化率",
        "订单数", "订单数变化额", "订单数变化率",
        "销量", "销量变化额", "销量变化率"
    ]

    st.dataframe(
        display_comparison[display_columns],
        use_container_width=True,
        hide_index=True
    )

    comparison_tab1, comparison_tab2, comparison_tab3 = st.tabs(
        ["销售额与利润对比", "利润率对比", "订单数与销量对比"]
    )

    with comparison_tab1:
        comparison_chart = comparison_summary.melt(
            id_vars="对比周期",
            value_vars=["销售额", "利润"],
            var_name="指标",
            value_name="金额"
        )
        fig = px.bar(
            comparison_chart,
            x="对比周期",
            y="金额",
            color="指标",
            barmode="group",
            title=f"{comparison_type}销售额与利润对比"
        )
        st.plotly_chart(fig, use_container_width=True)

    with comparison_tab2:
        fig = px.line(
            comparison_summary,
            x="对比周期",
            y="利润率",
            markers=True,
            title=f"{comparison_type}利润率变化趋势"
        )
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)

    with comparison_tab3:
        volume_chart = comparison_summary.melt(
            id_vars="对比周期",
            value_vars=["订单数", "销量"],
            var_name="指标",
            value_name="数量"
        )
        fig = px.bar(
            volume_chart,
            x="对比周期",
            y="数量",
            color="指标",
            barmode="group",
            title=f"{comparison_type}订单数与销量对比"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.caption("变化额和变化率均与上一周期比较。首个周期没有上一周期，因此不计算变化值。利润率变化额以百分点表示。")

    if st.button("🤖 AI 解读经营对比结果", key="analyze_comparison"):
        comparison_prompt = (
            f"请根据当前筛选后的经营数据，对以下{comparison_type}经营对比结果进行分析。"
            "重点说明销售额、利润、利润率、订单数和销量的变化趋势，指出表现较好和需要关注的周期，"
            "分析可能原因并给出可执行的经营建议。不要编造数据中没有的信息。"
            f"对比汇总数据：{comparison_summary.to_string(index=False)}"
        )
        with st.spinner("AI 正在解读经营对比结果..."):
            try:
                comparison_answer = answer_business_question(filtered_df, comparison_prompt)
                st.session_state["comparison_ai_answer"] = comparison_answer
            except Exception as error:
                st.error(f"AI 对比解读失败：{error}")

    if st.session_state.get("comparison_ai_answer"):
        st.markdown(st.session_state["comparison_ai_answer"])
else:
    st.info("当前筛选范围内没有可用于对比的经营数据。")

st.divider()
st.subheader("销售趋势分析")

daily = (
    filtered_df.groupby(filtered_df["order_date"].dt.date)
    .agg(销售额=("revenue", "sum"), 利润=("profit", "sum"))
    .reset_index()
)
daily.columns = ["日期", "销售额", "利润"]

tab1, tab2 = st.tabs(["销售额趋势", "利润趋势"])

with tab1:
    fig = px.line(daily, x="日期", y="销售额", markers=True, title="每日销售额趋势")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = px.line(daily, x="日期", y="利润", markers=True, title="每日利润趋势")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("🔮 未来 30 天销售额预测")
st.caption("比较线性回归与随机森林模型，并根据滚动回测表现自动选择模型。")

combined_forecast = None
future_forecast = None
forecast_metrics = None

try:
    combined_forecast, future_forecast, forecast_metrics = forecast_sales(
        filtered_df,
        days=30
    )

    forecast_total = float(future_forecast["销售额"].sum())
    forecast_daily_average = float(future_forecast["销售额"].mean())

    historical_daily_average = float(
        combined_forecast[
            combined_forecast["类型"] == "历史销售"
        ]["销售额"].mean()
    )

    f1, f2, f3 = st.columns(3)
    f1.metric("未来 30 天预计销售额", format_money(forecast_total))
    f2.metric("预计日均销售额", format_money(forecast_daily_average))
    f3.metric("历史日均销售额", format_money(historical_daily_average))

    st.subheader("模型评估与自动选择")
    st.success(f'当前选择模型：{forecast_metrics["selected_model"]}')

    m1, m2, m3 = st.columns(3)
    m1.metric("MAE 平均绝对误差", format_money(forecast_metrics["mae"]))
    m2.metric("RMSE 均方根误差", format_money(forecast_metrics["rmse"]))
    m3.metric("滚动回测窗口数", f'{forecast_metrics["backtest_windows"]} 轮')

    comparison = pd.DataFrame([
        {
            "模型": name,
            "MAE": values["mae"],
            "RMSE": values["rmse"]
        }
        for name, values in forecast_metrics["comparison"].items()
    ])

    st.dataframe(
        comparison.style.format({"MAE": "${:,.2f}", "RMSE": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "每轮回测仅使用预测起点之前的历史数据训练模型，"
        "再预测之后 30 天。MAE 和 RMSE 越低通常代表回测误差越小。"
    )

    st.subheader("30 天累计预测区间")

    if forecast_metrics["cumulative_interval_available"]:
        lower_total = forecast_metrics["cumulative_lower"]
        upper_total = forecast_metrics["cumulative_upper"]

        st.info(
            f"未来 30 天累计销售额预测：{format_money(forecast_total)}\n\n"
            f"根据滚动回测累计误差估算的经验参考区间："
            f"{format_money(lower_total)} 至 {format_money(upper_total)}。\n\n"
            f"有效滚动回测窗口：{forecast_metrics['block_sample_count']} 轮。"
        )
    else:
        st.warning("滚动回测样本不足，暂不展示累计预测区间。")

    st.caption(
        "该区间为历史滚动回测误差的经验参考范围，"
        "不是严格校准的统计置信区间，也不代表实际销售承诺。"
    )

    history_data = combined_forecast[
        combined_forecast["类型"] == "历史销售"
    ]

    forecast_data = combined_forecast[
        combined_forecast["类型"] == "预测销售"
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=history_data["日期"],
        y=history_data["销售额"],
        mode="lines",
        name="历史每日销售额",
        line=dict(width=1)
    ))

    fig.add_trace(go.Scatter(
        x=history_data["日期"],
        y=history_data["7日移动平均"],
        mode="lines",
        name="7日移动平均",
        line=dict(width=3)
    ))

    fig.add_trace(go.Scatter(
        x=forecast_data["日期"],
        y=forecast_data["预测上限"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        name="每日预测上限"
    ))

    fig.add_trace(go.Scatter(
        x=forecast_data["日期"],
        y=forecast_data["预测下限"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        name="每日预测区间",
        opacity=0.2
    ))

    fig.add_trace(go.Scatter(
        x=forecast_data["日期"],
        y=forecast_data["销售额"],
        mode="lines",
        name="未来销售额预测",
        line=dict(width=3, dash="dash")
    ))

    fig.update_layout(
        title="历史销售额、7日移动平均与未来30天预测",
        xaxis_title="日期",
        yaxis_title="销售额（美元）",
        hovermode="x unified",
        legend_title_text="数据类型"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("未来 30 天预测明细")

    forecast_display = future_forecast.copy()
    forecast_display["日期"] = forecast_display["日期"].dt.strftime("%Y-%m-%d")

    for column in ["销售额", "预测下限", "预测上限"]:
        forecast_display[column] = forecast_display[column].round(2)

    st.dataframe(forecast_display, use_container_width=True, hide_index=True)

    st.download_button(
        "下载 30 天销售预测 CSV",
        data=forecast_display.to_csv(index=False, encoding="utf-8-sig"),
        file_name="sales_forecast_30_days.csv",
        mime="text/csv"
    )

except Exception as error:
    st.warning(f"销售预测暂时无法生成：{error}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("城市经营分析")

    city_data = (
        filtered_df.groupby("store")
        .agg(销售额=("revenue", "sum"), 利润=("profit", "sum"))
        .reset_index()
        .sort_values("销售额", ascending=False)
    )

    fig = px.bar(city_data, x="store", y="销售额", title="各城市销售额对比")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("商品类别分析")

    category_data = (
        filtered_df.groupby("category")
        .agg(销售额=("revenue", "sum"))
        .reset_index()
    )

    fig = px.pie(
        category_data,
        names="category",
        values="销售额",
        title="商品类别销售占比"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("商品销售 TOP 10")

    product_top = (
        filtered_df.groupby("product")
        .agg(
            销售额=("revenue", "sum"),
            销量=("quantity", "sum"),
            利润=("profit", "sum")
        )
        .reset_index()
        .sort_values("销售额", ascending=False)
        .head(10)
    )

    fig = px.bar(
        product_top.sort_values("销售额"),
        x="销售额",
        y="product",
        orientation="h",
        title="销售额最高的 10 种商品"
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("低利润商品")

    low_profit = (
        filtered_df.groupby("product")
        .agg(销售额=("revenue", "sum"), 利润=("profit", "sum"))
        .reset_index()
        .sort_values("利润")
        .head(10)
    )

    st.dataframe(low_profit, use_container_width=True, hide_index=True)

st.divider()
st.subheader("详细经营数据")
st.dataframe(filtered_df, use_container_width=True, hide_index=True)

st.download_button(
    "下载当前筛选数据 CSV",
    data=filtered_df.to_csv(index=False, encoding="utf-8-sig"),
    file_name="business_analysis_data.csv",
    mime="text/csv"
)

st.divider()
st.subheader("🤖 AI 自动经营分析")

if st.button("生成 AI 经营分析报告", type="primary"):
    with st.spinner("AI 正在分析数据..."):
        try:
            report = generate_business_report(filtered_df)
            st.session_state["business_report"] = report
        except Exception as error:
            st.error(f"报告生成失败：{error}")

if st.session_state.get("business_report"):
    st.markdown(st.session_state["business_report"])

    if future_forecast is not None and forecast_metrics is not None:
        try:
            pdf_data = generate_business_pdf(
                filtered_df,
                st.session_state["business_report"],
                future_forecast,
                forecast_metrics
            )

            st.download_button(
                label="📄 下载完整 PDF 经营分析与预测报告",
                data=pdf_data,
                file_name="AI企业经营分析与销售预测报告.pdf",
                mime="application/pdf"
            )
        except Exception as error:
            st.error(f"PDF 报告生成失败：{error}")
    else:
        st.warning("当前预测结果不可用，PDF 将无法包含销售预测章节。")

st.divider()
st.subheader("💬 AI 经营数据问答")

question = st.text_input(
    "请输入经营问题",
    placeholder="例如：哪个城市销售额最高？"
)

if st.button("提交问题"):
    if not question.strip():
        st.warning("请先输入问题")
    else:
        with st.spinner("AI 正在回答..."):
            try:
                answer = answer_business_question(filtered_df, question)
                st.session_state["business_answer"] = answer
                st.session_state["business_question"] = question
            except Exception as error:
                st.error(f"问答失败：{error}")

if st.session_state.get("business_answer"):
    st.markdown(
        f'**问题：** {st.session_state.get("business_question", "")}'
    )
    st.markdown(st.session_state["business_answer"])

st.caption("数据来源：Sample Superstore 或管理员导入数据 | AI 企业经营分析平台")
