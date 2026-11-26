
from io import BytesIO
from pathlib import Path
import re
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether
)

def setup_fonts():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    font_candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc"
    ]

    for font_path in font_candidates:
        if Path(font_path).exists():
            font_manager.fontManager.addfont(font_path)
            font_name = font_manager.FontProperties(
                fname=font_path
            ).get_name()
            plt.rcParams["font.sans-serif"] = [font_name]
            break

    plt.rcParams["axes.unicode_minus"] = False

def money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"

def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value)

def make_table(data, widths=None, font_size=8):
    table = Table(
        data,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT"
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#24364B")),
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 4),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D2DC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F7F9FC")
        ])
    ]))

    return table

def make_forecast_chart(forecast_df):
    setup_fonts()

    daily = forecast_df.copy()
    daily["日期"] = pd.to_datetime(daily["日期"], errors="coerce")
    daily["销售额"] = pd.to_numeric(
        daily["销售额"],
        errors="coerce"
    )
    daily = daily.dropna(subset=["日期", "销售额"])

    if daily.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 4.5))

    ax.plot(
        daily["日期"],
        daily["销售额"],
        linewidth=2,
        label="预测销售额"
    )

    if "预测下限" in daily.columns:
        lower = pd.to_numeric(
            daily["预测下限"],
            errors="coerce"
        )

        upper = pd.to_numeric(
            daily["预测上限"],
            errors="coerce"
        )

        ax.fill_between(
            daily["日期"],
            lower,
            upper,
            alpha=0.2,
            label="预测区间"
        )

    ax.set_title("未来30天销售额预测")
    ax.set_xlabel("日期")
    ax.set_ylabel("销售额（美元）")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    image_buffer = BytesIO()
    fig.savefig(
        image_buffer,
        format="png",
        dpi=180,
        bbox_inches="tight"
    )
    plt.close(fig)
    image_buffer.seek(0)

    return image_buffer

def make_history_forecast_chart(df, forecast_df):
    setup_fonts()

    history = (
        df.groupby(df["order_date"].dt.date)["revenue"]
        .sum()
        .reset_index()
    )

    history.columns = ["日期", "销售额"]
    history["日期"] = pd.to_datetime(history["日期"])
    history = history.sort_values("日期")

    future = forecast_df.copy()
    future["日期"] = pd.to_datetime(future["日期"])

    fig, ax = plt.subplots(figsize=(10, 4.5))

    ax.plot(
        history["日期"],
        history["销售额"],
        linewidth=0.8,
        alpha=0.65,
        label="历史每日销售额"
    )

    rolling = history["销售额"].rolling(
        window=7,
        min_periods=1
    ).mean()

    ax.plot(
        history["日期"],
        rolling,
        linewidth=2,
        label="7日移动平均"
    )

    ax.plot(
        future["日期"],
        future["销售额"],
        linewidth=2,
        linestyle="--",
        label="未来销售预测"
    )

    if "预测下限" in future.columns and "预测上限" in future.columns:
        ax.fill_between(
            future["日期"],
            future["预测下限"],
            future["预测上限"],
            alpha=0.2,
            label="预测区间"
        )

    ax.set_title("历史销售额与未来30天预测")
    ax.set_xlabel("日期")
    ax.set_ylabel("销售额（美元）")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    image_buffer = BytesIO()
    fig.savefig(
        image_buffer,
        format="png",
        dpi=180,
        bbox_inches="tight"
    )
    plt.close(fig)
    image_buffer.seek(0)

    return image_buffer

def clean_ai_report(report):
    text = safe_text(report)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("`", "")
    return text.strip()

def generate_business_pdf(
    df,
    report,
    future_forecast=None,
    forecast_metrics=None
):
    setup_fonts()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="AI企业经营分析与销售预测报告",
        author="AI企业经营分析平台"
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ChineseTitle",
        parent=styles["Title"],
        fontName="STSong-Light",
        fontSize=22,
        leading=32,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#172B4D"),
        spaceAfter=18
    )

    heading_style = ParagraphStyle(
        "ChineseHeading",
        parent=styles["Heading2"],
        fontName="STSong-Light",
        fontSize=15,
        leading=22,
        textColor=colors.HexColor("#24364B"),
        spaceBefore=12,
        spaceAfter=9
    )

    body_style = ParagraphStyle(
        "ChineseBody",
        parent=styles["BodyText"],
        fontName="STSong-Light",
        fontSize=9,
        leading=16,
        spaceAfter=6
    )

    small_style = ParagraphStyle(
        "ChineseSmall",
        parent=body_style,
        fontSize=8,
        leading=12
    )

    story = []

    start_date = df["order_date"].min().strftime("%Y-%m-%d")
    end_date = df["order_date"].max().strftime("%Y-%m-%d")

    revenue = float(df["revenue"].sum())
    profit = float(df["profit"].sum())
    quantity = float(df["quantity"].sum())
    order_count = int(df["order_id"].nunique())
    margin = profit / revenue if revenue else 0

    story.append(Paragraph(
        "AI企业经营分析与销售预测报告",
        title_style
    ))

    story.append(Paragraph(
        f"数据期间：{start_date} 至 {end_date}",
        body_style
    ))

    story.append(Spacer(1, 12))

    story.append(Paragraph("一、核心经营指标", heading_style))

    metric_data = [
        ["指标", "结果", "指标", "结果"],
        ["销售总额", money(revenue), "利润总额", money(profit)],
        ["利润率", f"{margin:.2%}", "订单数量", f"{order_count:,}"],
        ["商品销量", f"{quantity:,.0f}", "数据记录数", f"{len(df):,}"]
    ]

    story.append(make_table(
        metric_data,
        widths=[
            3.2 * cm,
            4.0 * cm,
            3.2 * cm,
            5.0 * cm
        ]
    ))

    city_data = (
        df.groupby("store")
        .agg(
            销售额=("revenue", "sum"),
            利润=("profit", "sum")
        )
        .reset_index()
        .sort_values("销售额", ascending=False)
        .head(10)
    )

    story.append(Paragraph("二、城市经营表现", heading_style))

    city_table = [["城市", "销售额", "利润"]]

    for _, row in city_data.iterrows():
        city_table.append([
            safe_text(row["store"]),
            money(row["销售额"]),
            money(row["利润"])
        ])

    story.append(make_table(
        city_table,
        widths=[
            6.0 * cm,
            4.5 * cm,
            4.5 * cm
        ]
    ))

    category_data = (
        df.groupby("category")
        .agg(
            销售额=("revenue", "sum"),
            利润=("profit", "sum")
        )
        .reset_index()
        .sort_values("销售额", ascending=False)
    )

    story.append(Paragraph("三、商品类别表现", heading_style))

    category_table = [["商品类别", "销售额", "利润"]]

    for _, row in category_data.iterrows():
        category_table.append([
            safe_text(row["category"]),
            money(row["销售额"]),
            money(row["利润"])
        ])

    story.append(make_table(
        category_table,
        widths=[
            6.0 * cm,
            4.5 * cm,
            4.5 * cm
        ]
    ))

    if future_forecast is not None and not future_forecast.empty:
        forecast_df = future_forecast.copy()
        forecast_df["日期"] = pd.to_datetime(
            forecast_df["日期"],
            errors="coerce"
        )
        forecast_df = forecast_df.dropna(subset=["日期"])

        forecast_total = float(
            pd.to_numeric(
                forecast_df["销售额"],
                errors="coerce"
            ).fillna(0).sum()
        )

        forecast_average = (
            forecast_total / len(forecast_df)
            if len(forecast_df)
            else 0
        )

        story.append(PageBreak())
        story.append(Paragraph("四、未来30天销售预测", heading_style))

        forecast_summary = [
            ["预测指标", "预测结果"],
            ["未来30天预计销售额", money(forecast_total)],
            ["预计日均销售额", money(forecast_average)],
            ["预测天数", f"{len(forecast_df)} 天"]
        ]

        story.append(make_table(
            forecast_summary,
            widths=[7.0 * cm, 7.0 * cm]
        ))

        story.append(Spacer(1, 12))

        history_chart = make_history_forecast_chart(
            df,
            forecast_df
        )

        if history_chart:
            story.append(Image(
                history_chart,
                width=16.5 * cm,
                height=7.4 * cm
            ))

        story.append(Paragraph(
            "每日预测趋势",
            heading_style
        ))

        forecast_chart = make_forecast_chart(forecast_df)

        if forecast_chart:
            story.append(Image(
                forecast_chart,
                width=16.5 * cm,
                height=7.4 * cm
            ))

        if forecast_metrics:
            story.append(Paragraph(
                "五、预测模型评估",
                heading_style
            ))

            selected_model = safe_text(
                forecast_metrics.get("selected_model", "未提供")
            )

            model_data = [
                ["评估指标", "结果"],
                ["最终选择模型", selected_model],
                [
                    "MAE",
                    money(forecast_metrics.get("mae", 0))
                ],
                [
                    "RMSE",
                    money(forecast_metrics.get("rmse", 0))
                ],
                [
                    "滚动回测窗口数",
                    str(forecast_metrics.get("backtest_windows", 0))
                ]
            ]

            story.append(make_table(
                model_data,
                widths=[7.0 * cm, 7.0 * cm]
            ))

            comparison = forecast_metrics.get("comparison", {})

            if comparison:
                comparison_table = [
                    ["模型", "MAE", "RMSE"]
                ]

                for model_name, values in comparison.items():
                    comparison_table.append([
                        safe_text(model_name),
                        money(values.get("mae", 0)),
                        money(values.get("rmse", 0))
                    ])

                story.append(Spacer(1, 10))
                story.append(make_table(
                    comparison_table,
                    widths=[
                        5.0 * cm,
                        4.5 * cm,
                        4.5 * cm
                    ]
                ))

            if forecast_metrics.get("cumulative_interval_available"):
                lower = forecast_metrics.get(
                    "cumulative_lower",
                    0
                )
                upper = forecast_metrics.get(
                    "cumulative_upper",
                    0
                )

                story.append(Spacer(1, 8))
                story.append(Paragraph(
                    f"未来30天累计销售额经验参考区间："
                    f"{money(lower)} 至 {money(upper)}。",
                    body_style
                ))

            story.append(Paragraph(
                "模型使用历史数据进行滚动时间顺序回测。"
                "MAE 和 RMSE 越低，通常表示回测预测误差越小。"
                "预测结果仅用于经营参考，不构成实际销售承诺。"
                "预测区间为基于历史回测误差估算的经验参考范围，"
                "不等同于严格校准的统计置信区间。",
                small_style
            ))

        story.append(PageBreak())
        story.append(Paragraph(
            "六、未来30天预测明细",
            heading_style
        ))

        detail_table = [[
            "日期",
            "预测销售额",
            "预测下限",
            "预测上限"
        ]]

        for _, row in forecast_df.iterrows():
            detail_table.append([
                row["日期"].strftime("%Y-%m-%d"),
                money(row.get("销售额", 0)),
                money(row.get("预测下限", 0)),
                money(row.get("预测上限", 0))
            ])

        story.append(make_table(
            detail_table,
            widths=[
                3.5 * cm,
                3.8 * cm,
                3.8 * cm,
                3.8 * cm
            ],
            font_size=7
        ))

    story.append(PageBreak())
    story.append(Paragraph(
        "七、AI智能经营分析与建议",
        heading_style
    ))

    ai_text = clean_ai_report(report)

    if ai_text:
        for paragraph in re.split(r"\n+", ai_text):
            paragraph = paragraph.strip()

            if paragraph:
                paragraph = (
                    paragraph
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )

                story.append(Paragraph(
                    paragraph,
                    body_style
                ))
    else:
        story.append(Paragraph(
            "当前未提供 AI 分析内容。",
            body_style
        ))

    story.append(Spacer(1, 18))

    story.append(Paragraph(
        "报告说明：本报告基于所选数据范围生成。"
        "Sample Superstore 为示例零售数据，金额单位为美元。"
        "成本由销售额减去利润推算，并非企业实际成本账目。"
        "其中城市字段来源于原始数据中的 City 字段。",
        small_style
    ))

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("STSong-Light", 8)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawCentredString(
            A4[0] / 2,
            0.9 * cm,
            f"第 {document.page} 页"
        )
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    buffer.seek(0)
    return buffer.getvalue()
