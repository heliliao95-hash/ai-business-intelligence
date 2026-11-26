import random
from datetime import datetime, timedelta

import pandas as pd


def generate_business_data(
	num_records=3000,
	seed=42
):
	"""生成企业经营模拟销售数据。"""

	random.seed(seed)

	stores = [
		"长沙五一广场店",
		"长沙梅溪湖店",
		"长沙万家丽店",
		"株洲中心广场店",
		"湘潭步步高店",
	]

	products = {
		"奶茶": [12, 15, 18, 22],
		"咖啡": [16, 20, 24, 28],
		"果茶": [14, 18, 21, 25],
		"甜品": [10, 15, 20, 26],
		"轻食": [18, 22, 28, 32],
	}

	start_date = datetime(2025, 1, 1)

	records = []

	for i in range(num_records):
		category = random.choice(list(products.keys()))
		unit_price = random.choice(products[category])
		quantity = random.randint(1, 8)

		discount = random.choice([
			1.0, 1.0, 0.95, 0.9, 0.85
		])

		revenue = round(
			unit_price * quantity * discount, 2
		)

		cost_rate = random.uniform(0.35, 0.65)
		cost = round(
			unit_price * quantity * cost_rate, 2
		)

		order_date = start_date + timedelta(
			days=random.randint(0, 364),
			hours=random.randint(8, 22),
			minutes=random.randint(0, 59)
		)

		records.append({
			"order_id": f"ORD{i + 1:06d}",
			"order_date": order_date,
			"store": random.choice(stores),
			"category": category,
			"product": f"{category}-{random.randint(1, 5)}号",
			"unit_price": unit_price,
			"quantity": quantity,
			"discount": discount,
			"revenue": revenue,
			"cost": cost,
			"profit": round(revenue - cost, 2),
			"payment_method": random.choice([
				"微信支付",
				"支付宝",
				"银行卡",
			]),
		})

	return pd.DataFrame(records)


if __name__ == "__main__":
	df = generate_business_data()

	print("模拟数据生成成功！")
	print(f"数据行数：{len(df)}")
	print("\n数据预览：")
	print(df.head())

	print("\n数据基本信息：")
	print(df.describe(include="all"))
