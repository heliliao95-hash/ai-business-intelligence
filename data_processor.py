
import pandas as pd


def inspect_data(df):
    """检查数据质量，返回检测报告。"""

    if df is None or df.empty:
        raise ValueError("数据为空，无法进行质量检测！")

    report = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "duplicate_count": int(df.duplicated().sum()),
        "missing_values": df.isnull().sum().to_dict(),
        "missing_total": int(df.isnull().sum().sum()),
        "columns": list(df.columns),
    }

    return report


def clean_data(df):
    """清洗经营数据，返回清洗后的数据和清洗报告。"""

    if df is None or df.empty:
        raise ValueError("数据为空，无法进行清洗！")

    cleaned = df.copy()

    original_rows = len(cleaned)

    # 1. 删除完全重复的记录
    duplicate_count = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates()

    # 2. 处理日期字段
    if "order_date" in cleaned.columns:
        cleaned["order_date"] = pd.to_datetime(
            cleaned["order_date"],
            errors="coerce"
        )

    # 3. 处理数值字段
    numeric_columns = [
        "unit_price",
        "quantity",
        "discount",
        "revenue",
        "cost",
        "profit",
    ]

    for column in numeric_columns:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(
                cleaned[column],
                errors="coerce"
            )

    # 4. 删除关键字段缺失的记录
    required_columns = [
        column
        for column in ["order_id", "order_date", "store"]
        if column in cleaned.columns
    ]

    if required_columns:
        cleaned = cleaned.dropna(
            subset=required_columns
        )

    # 5. 删除数量、价格等关键指标不合理的记录
    if "quantity" in cleaned.columns:
        cleaned = cleaned[
            cleaned["quantity"] > 0
        ]

    if "unit_price" in cleaned.columns:
        cleaned = cleaned[
            cleaned["unit_price"] >= 0
        ]

    if "discount" in cleaned.columns:
        cleaned = cleaned[
            cleaned["discount"].between(0, 1)
        ]

    # 6. 根据单价、数量和折扣重新计算销售额
    if all(
        column in cleaned.columns
        for column in ["unit_price", "quantity", "discount"]
    ):
        cleaned["revenue"] = (
            cleaned["unit_price"]
            * cleaned["quantity"]
            * cleaned["discount"]
        ).round(2)

    # 7. 根据销售额和成本重新计算利润
    if all(
        column in cleaned.columns
        for column in ["revenue", "cost"]
    ):
        cleaned["profit"] = (
            cleaned["revenue"] - cleaned["cost"]
        ).round(2)

    # 8. 重置索引
    cleaned = cleaned.reset_index(drop=True)

    # 9. 生成清洗报告
    report = {
        "original_rows": original_rows,
        "cleaned_rows": len(cleaned),
        "removed_rows": original_rows - len(cleaned),
        "duplicate_rows": duplicate_count,
        "remaining_missing_values": int(
            cleaned.isnull().sum().sum()
        ),
    }

    return cleaned, report


if __name__ == "__main__":
    print("数据清洗模块加载成功！")
