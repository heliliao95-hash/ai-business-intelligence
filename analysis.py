import pandas as pd

from database import load_data, execute_query


def get_business_kpis():
	"""获取企业整体经营指标。"""

	sql = """
		SELECT
			COUNT(*) AS order_count,
			SUM(quantity) AS total_quantity,
			ROUND(SUM(revenue), 2) AS total_revenue,
			ROUND(SUM(cost), 2) AS total_cost,
			ROUND(SUM(profit), 2) AS total_profit,
			ROUND(
				SUM(profit) * 100.0 / NULLIF(SUM(revenue), 0),
				2
			) AS profit_margin
		FROM sales
	"""

	return execute_query(sql)


def get_store_analysis():
	"""获取各门店经营情况。"""

	sql = """
		SELECT
			store,
			COUNT(*) AS order_count,
			ROUND(SUM(revenue), 2) AS total_revenue,
			ROUND(SUM(profit), 2) AS total_profit,
			ROUND(
				SUM(profit) * 100.0 / NULLIF(SUM(revenue), 0),
				2
			) AS profit_margin
		FROM sales
		GROUP BY store
		ORDER BY total_revenue DESC
	"""

	return execute_query(sql)


def get_category_analysis():
	"""获取商品类别经营情况。"""

	sql = """
		SELECT
			category,
			SUM(quantity) AS total_quantity,
			ROUND(SUM(revenue), 2) AS total_revenue,
			ROUND(SUM(profit), 2) AS total_profit
		FROM sales
		GROUP BY category
		ORDER BY total_revenue DESC
	"""

	return execute_query(sql)


def get_monthly_analysis():
	"""获取月度销售趋势。"""

	sql = """
		SELECT
			strftime('%Y-%m', order_date) AS month,
			ROUND(SUM(revenue), 2) AS total_revenue,
			ROUND(SUM(profit), 2) AS total_profit
		FROM sales
		GROUP BY strftime('%Y-%m', order_date)
		ORDER BY month
	"""

	return execute_query(sql)


def get_product_ranking(limit=10):
	"""获取商品销售排行榜。"""

	sql = """
		SELECT
			product,
			category,
			SUM(quantity) AS total_quantity,
			ROUND(SUM(revenue), 2) AS total_revenue,
			ROUND(SUM(profit), 2) AS total_profit
		FROM sales
		GROUP BY product, category
		ORDER BY total_revenue DESC
		LIMIT ?
	"""

	return execute_query(sql, (limit,))


def get_low_profit_products(limit=10):
	"""获取利润率较低的商品。"""

	sql = """
		SELECT
			product,
			category,
			ROUND(SUM(revenue), 2) AS total_revenue,
			ROUND(SUM(profit), 2) AS total_profit,
			ROUND(
				SUM(profit) * 100.0 / NULLIF(SUM(revenue), 0),
				2
			) AS profit_margin
		FROM sales
		GROUP BY product, category
		HAVING SUM(revenue) > 0
		ORDER BY profit_margin ASC
		LIMIT ?
	"""

	return execute_query(sql, (limit,))


if __name__ == "__main__":
	print("企业经营分析模块测试")

	print("\n一、整体经营 KPI")
	print(get_business_kpis().to_string(index=False))

	print("\n二、门店经营排名")
	print(get_store_analysis().to_string(index=False))

	print("\n三、商品类别分析")
	print(get_category_analysis().to_string(index=False))

	print("\n四、月度销售趋势")
	print(get_monthly_analysis().to_string(index=False))

	print("\n五、商品销售排行榜")
	print(get_product_ranking().to_string(index=False))

	print("\n六、低利润率商品")
	print(get_low_profit_products().to_string(index=False))
