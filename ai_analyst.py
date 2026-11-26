
import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_ai_client():
    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise ValueError("没有找到 DASHSCOPE_API_KEY，请检查项目根目录下的 .env 文件。")

    return OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

def build_data_summary(df):
    if df is None or df.empty:
        return "当前没有可供分析的经营数据。"

    required_columns = [
        "revenue",
        "profit",
        "store",
        "category",
        "product",
        "quantity"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"数据缺少必要字段：{', '.join(missing_columns)}")

    total_revenue = df["revenue"].sum()
    total_profit = df["profit"].sum()
    total_orders = len(df)
    total_quantity = df["quantity"].sum()

    profit_margin = (
        total_profit / total_revenue * 100
        if total_revenue else 0
    )

    store_analysis = df.groupby("store").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("product", "count")
    ).sort_values("revenue", ascending=False)

    category_analysis = df.groupby("category").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        quantity=("quantity", "sum")
    ).sort_values("revenue", ascending=False)

    product_analysis = df.groupby("product").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        quantity=("quantity", "sum")
    ).sort_values("revenue", ascending=False).head(15)

    return f"""
企业经营数据摘要：

销售总额：{total_revenue:.2f} 元
总利润：{total_profit:.2f} 元
订单数量：{total_orders}
销售商品数量：{total_quantity}
整体利润率：{profit_margin:.2f}%

门店经营数据：
{store_analysis.to_string()}

商品类别经营数据：
{category_analysis.to_string()}

商品销售排行：
{product_analysis.to_string()}
"""

def generate_business_report(df):
    if df is None or df.empty:
        return "当前没有可供分析的经营数据。"

    data_summary = build_data_summary(df)

    prompt = f"""
你是一名专业的企业经营数据分析师。

请根据以下经营数据生成一份完整的中文经营分析报告。

{data_summary}

报告需要包含：

一、整体经营情况
二、门店经营分析
三、商品类别分析
四、重点商品分析
五、经营问题与风险
六、经营优化建议
七、经营总结

要求：
1. 所有结论必须以提供的数据为依据。
2. 不要编造数据。
3. 对数据无法支持的结论明确说明。
4. 使用中文回答。
5. 提供具体、可执行的经营建议。
"""

    client = get_ai_client()

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {
                "role": "system",
                "content": "你是一名严谨、专业的企业经营数据分析师。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4
    )

    return response.choices[0].message.content

def answer_business_question(df, question):
    if df is None or df.empty:
        return "当前没有可供分析的经营数据。"

    if not question or not question.strip():
        return "请输入你想了解的经营问题。"

    data_summary = build_data_summary(df)

    prompt = f"""
你是一名专业的企业经营数据分析师。

以下是当前企业经营数据：

{data_summary}

用户的问题是：

{question}

请根据数据回答用户的问题。

要求：
1. 优先使用提供的数据回答。
2. 涉及金额时使用人民币单位。
3. 涉及比例时明确使用百分比。
4. 不要编造数据或虚构事实。
5. 数据无法支持的问题，请明确说明。
6. 回答使用中文，表达清晰、简洁。
7. 如果可以，提供具体的经营建议。
"""

    client = get_ai_client()

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {
                "role": "system",
                "content": "你是一名严谨的企业经营数据问答助手，只能依据提供的数据作出判断。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content
