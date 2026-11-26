```markdown
# AI 企业经营分析平台
基于 Python、Streamlit 和 AI 技术构建的企业经营分析平台。通过交互式数据可视化、经营指标分析、销售预测和 AI 智能问答，帮助用户了解企业经营状况，为经营决策提供数据参考。

## 一、项目简介
本项目使用 Sample Superstore 零售交易数据作为分析数据源，围绕销售、利润、商品、地区和经营趋势等维度进行分析。

平台提供用户登录验证、数据管理、经营对比分析、销售趋势分析、销售预测、AI 经营分析和 PDF 报告导出等功能。

## 二、核心功能

### 1. 用户登录与权限管理

- 用户身份验证
- 管理员与普通用户权限区分
- 用户管理
- 用户密码修改

### 2. 数据管理

- 读取和清洗业务数据
- 数据质量检查
- 数据导入与管理
- 数据筛选

### 3. 销售经营分析

- 销售额分析
- 利润与利润率分析
- 订单及销量分析
- 日期、城市和商品类别筛选
- 城市销售表现分析
- 商品销售排名
- 低利润商品分析

### 4. 经营数据对比

- 月度经营数据对比
- 季度经营数据对比
- 年度经营数据对比
- 不同周期的销售额和利润变化分析

### 5. 销售预测

- 未来 30 天销售预测
- 线性回归模型
- 随机森林模型
- 模型效果对比
- 预测误差评估

### 6. AI 智能经营分析

- 自动生成 AI 经营分析报告
- 自然语言经营数据问答
- 根据筛选后的数据提供分析参考

### 7. PDF 报告

- 导出经营分析报告
- 集成销售预测结果
- 生成 PDF 格式报告

## 三、技术栈

| 技术 | 用途 |
| --- | --- |
| Python | 核心开发语言 |
| Streamlit | Web 应用框架 |
| Pandas | 数据处理与分析 |
| Plotly | 数据可视化 |
| Scikit-learn | 机器学习与销售预测 |
| SQLite | 用户数据存储 |
| ReportLab | PDF 报告生成 |
| DashScope / Qwen | AI 智能分析 |

## 四、项目目录

```
ai-business-intelligence/
│
├── app.py
├── app_stable_20261126.py
├── app_recovered_backup.py
│
├── auth.py
├── ai_analyst.py
├── analysis.py
├── charts.py
├── data_generator.py
├── data_processor.py
├── database.py
├── forecasting.py
├── pdf_report.py
│
├── test_ai.py
├── test_charts.py
├── test_modules.py
│
├── data/
├── .streamlit/
├── .gitignore
├── README.md
└── requirements.txt
```

注：实际项目目录以仓库中提交的文件为准。`requirements.txt` 如尚未创建，需要根据项目实际依赖生成。

## 五、运行环境

- Windows
- Python 3.13
- Visual Studio Code
- Git

## 六、安装与运行

### 1. 克隆项目

```
git clone 你的GitHub仓库地址
```

### 2. 进入项目目录

```
cd ai-business-intelligence
```

### 3. 创建虚拟环境

```
python -m venv .venv
```

### 4. 激活虚拟环境
Windows PowerShell：

```
.\.venv\Scripts\Activate.ps1
```

### 5. 安装依赖

```
pip install -r requirements.txt
```

### 6. 启动应用

```
streamlit run app.py
```

浏览器访问：

```
http://localhost:8501
```

## 七、数据说明
本项目使用 Sample Superstore 零售交易数据。

数据包含订单日期、城市、商品类别、商品名称、销售额、利润、折扣、客户编号、运输方式等字段。

需要注意：

- 数据属于示例零售交易数据，并非真实企业经营数据。
- 原始数据中的 City 字段在项目中映射为城市维度，并不代表真实门店。
- 成本数据根据销售额减去利润推算，并非企业实际财务成本。
- 分析结果仅供学习、测试和经营分析方法参考。

## 八、注意事项

1. 请勿将 `.env`、API 密钥、用户数据库、密码或其他敏感信息上传到公开仓库。
2. 请勿将 `.venv` 和 `__pycache__` 上传到 GitHub。
3. 使用 AI 分析功能前，需要正确配置对应的 API 密钥。
4. 使用项目时，请确保必要的数据文件和 Python 依赖完整。

## 九、项目目标
本项目旨在探索 Python 数据分析、机器学习和大语言模型在企业经营分析场景中的应用，将传统数据统计与 AI 智能分析相结合，构建一个可交互、可扩展的企业经营分析平台。

---

**项目名称：** AI 企业经营分析平台  
**项目类型：** Python 数据分析与 AI 应用  
**开发框架：** Streamlit  
**数据来源：** Sample Superstore
```
