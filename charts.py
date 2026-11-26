import plotly.express as px
import plotly.graph_objects as go


def create_store_chart(df):
	"""创建门店销售额排名柱状图。"""

	fig = px.bar(
		df,
		x="store",
		y="total_revenue",
		color="total_revenue",
		text="total_revenue",
		title="各门店销售额排名",
		labels={
			"store": "门店",
			"total_revenue": "销售额",
		},
		color_continuous_scale="Blues",
	)

	fig.update_traces(
		texttemplate="%{text:,.0f}",
		textposition="outside",
	)

	fig.update_layout(
		xaxis_title="门店",
		yaxis_title="销售额",
		showlegend=False,
		template="plotly_white",
	)

	return fig


def create_category_chart(df):
	"""创建商品类别销售额占比饼图。"""

	fig = px.pie(
		df,
		names="category",
		values="total_revenue",
		title="商品类别销售额占比",
		hole=0.4,
	)

	fig.update_traces(
		textposition="inside",
		textinfo="label+percent",
	)

	fig.update_layout(
		template="plotly_white",
	)

	return fig


def create_monthly_chart(df):
	"""创建月度销售额与利润趋势图。"""

	fig = go.Figure()

	fig.add_trace(
		go.Scatter(
			x=df["month"],
			y=df["total_revenue"],
			mode="lines+markers",
			name="销售额",
		)
	)

	fig.add_trace(
		go.Scatter(
			x=df["month"],
			y=df["total_profit"],
			mode="lines+markers",
			name="利润",
		)
	)

	fig.update_layout(
		title="月度销售额与利润趋势",
		xaxis_title="月份",
		yaxis_title="金额",
		hovermode="x unified",
		template="plotly_white",
	)

	return fig


def create_profit_chart(df):
	"""创建商品利润率对比图。"""

	fig = px.bar(
		df,
		x="product",
		y="profit_margin",
		color="profit_margin",
		text="profit_margin",
		title="商品利润率分析",
		labels={
			"product": "商品",
			"profit_margin": "利润率（%）",
		},
		color_continuous_scale="RdYlGn",
	)

	fig.update_traces(
		texttemplate="%{text:.2f}%",
		textposition="outside",
	)

	fig.update_layout(
		xaxis_title="商品",
		yaxis_title="利润率（%）",
		showlegend=False,
		template="plotly_white",
	)

	return fig
