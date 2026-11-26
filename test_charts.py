from analysis import (
	get_store_analysis,
	get_category_analysis,
	get_monthly_analysis,
	get_low_profit_products,
)

from charts import (
	create_store_chart,
	create_category_chart,
	create_monthly_chart,
	create_profit_chart,
)


def main():
	print("开始测试企业经营可视化模块...")

	store_df = get_store_analysis()
	category_df = get_category_analysis()
	monthly_df = get_monthly_analysis()
	profit_df = get_low_profit_products()

	charts = [
		("门店销售额排名", create_store_chart(store_df)),
		("商品类别销售额占比", create_category_chart(category_df)),
		("月度销售趋势", create_monthly_chart(monthly_df)),
		("商品利润率分析", create_profit_chart(profit_df)),
	]

	for name, fig in charts:
		fig.write_html(
			f"{name}.html",
			include_plotlyjs=True
		)
		print(f"{name}：生成成功")

	print("\n所有图表生成完成！")


if __name__ == "__main__":
	main()
