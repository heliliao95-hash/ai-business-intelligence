
from data_generator import generate_business_data
from data_processor import clean_data
from ai_analyst import generate_business_report

df = generate_business_data(3000)

result = clean_data(df)

if isinstance(result, tuple):
    df = result[0]
else:
    df = result

print("正在生成 AI 经营分析报告，请稍候...")

try:
    report = generate_business_report(df)
    print("\nAI 经营分析报告：\n")
    print(report)

except Exception as e:
    print(f"AI 分析失败：{e}")
