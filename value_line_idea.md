# value_line_idea.md

## 1. 目标

本项目希望基于 Tushare 的数据，为 A 股做一份类似 **Value Line Research Report** 的「单页股票报告」。

目标效果：

- 一只股票 = 一张报告页面（网页 + 可导出为 PDF）。
- 上半部分以 **股价 + 估值 + 核心指标图表** 为主；
- 下半部分是 **多年财务统计表 + 资本结构 + 年化增速**；
- 右侧/底部有一小块 **文字点评 + 简单评级**。

本文件用来告诉 Gemini / LLM 要实现的版式和数据字段，不限制具体前端框架（Streamlit / Dash / Vue / React 均可）。

---

## 2. 整体布局（参考 Value Line 经典版式）

页面为纵向单页，整体分为 4 个大区域：

1. **页眉 Header 区**（公司名称、代码、核心评级）
2. **上半部 图表 & 估值区**（股价图 + 核心估值/收益指标）
3. **中下部 Statistical Array（多年财务表）**
4. **右下部 / 底部 文字点评 & 衍生信息**

布局示意（仅为逻辑分区，不是最终 CSS）：

- 第一行：页眉 + 顶部指标带
- 第二行：左侧大图（股价/估值/相对强弱），右侧目标价区间 & 指标概览
- 第三行：整行多列表格（类似 Value Line 中部的长表）
- 第四行：左侧资本结构 & 年化增速，右侧文字点评和补充表

---

## 3. 页眉 Header 区

位置：页面最顶部。

### 3.1 基本信息行

- 公司全称（中文）
- 英文名（如有）
- 交易所 & 股票代码（例：`SZSE 300443`）
- 行业分类（申万或中信一级行业）
- 报告日期（取最近交易日）

### 3.2 Value Line 风格评级条

仿照截图中 “TIMELINESS / SAFETY / TECHNICAL / BETA” 的形式：

- **TIMELINESS**：1–5 级  
  - 自研含义：未来 6–12 个月相对收益预期（综合估值分位 + 动量因子）。
- **SAFETY**：1–5 级  
  - 自研含义：公司财务稳健度 + 波动性（杠杆、现金流、波动率等）。
- **TECHNICAL**：1–5 级  
  - 自研含义：纯技术面趋势强弱（如 6 个月动量、均线多头/空头、换手等）。
- **BETA**：相对沪深 300 或中证 800 的贝塔。

实现要求：

- 先用简单的规则生成评分（MVP 阶段），算法后续再优化。
- UI 上用紧凑的一行展示：`TIMELINESS: 2   SAFETY: 1   TECHNICAL: 4   BETA: 0.95`。

可预留：Financial Strength / Price Stability / Earnings Predictability 等评分的占位符位。

---

## 4. 顶部指标带（Top Metrics Strip）

紧接页眉，仿照原版上方那条 “RECENT PRICE / P/E / DIV’D YLD / TARGET PRICE RANGE” 的横条。

需要展示：

1. **近期价格**  
   - 字段：`recent_price`（最近收盘价，元）
   - 旁边小号展示：`52 周最高 / 最低`。

2. **市盈率信息**  
   - `pe_ttm`：当前 TTM PE  
   - `pe_trailing`：过去 4 个财报期合计 EPS 对应的 PE  
   - `pe_10y_median`：近 10 年年末 PE 的中位数（不够 10 年则用全部历史）  
   - `pe_relative`：`pe_ttm / 市场整体中位 PE`（市场可选沪深 300 全体成分）。

3. **股息信息**  
   - `div_yield`：最近 12 个月分红 / 当前股价（%）
   - 可留备注：最近一次派息时间和金额。

4. **3–5 年目标价区间（仿 Value Line Target Price Range）**  
   - `target_price_low`  
   - `target_price_high`  
   - `target_total_return_low/high`：3–5 年总收益率估计区间（包含股息）。  
   - `target_annual_return_low/high`：年化收益率估计区间（可选）。

注意：MVP 阶段目标价可以用简单假设（比如：用合理 PE 区间 * 预期 EPS）得到，算法不必复杂，但接口要预留好字段。

---

## 5. 图表区（上半部分）

### 5.1 主图：股价 + EPS + 估值 / 相对强度

目的：模仿原版中上半部的价格图（带阴影区域、相对强度等），但先做简化版。

**X 轴：**

- 时间轴，尽量覆盖 10–15 年（新股则取全部历史）。

**左侧 Y 轴：股价 & 估值**

- 前复权股价（折线）；
- 可选：月度高低价（蜡烛 / high-low 线）；
- 可选：PE 或 PB（第二条折线，颜色/线型区分）。

**右侧 Y 轴：每股指标**

- EPS（按 TTM 或年度 EPS -> 阶梯线延展到下一财报发布日）；
- 可选：每股分红 DPS；
- 可选：ROE（%）。

**附加曲线（可选项，先可占位）：**

- `cash_flow_per_share` 线（EPS + 折旧摊销），模仿 Value Line 的 “Cash Flow line”；  
- `relative_strength` 线：个股相对沪深 300 的强弱（如：股票价格指数 / 指数价格指数）。

**交互与样式：**

- 图例：允许用户单独开关各条线；
- 悬浮提示：展示当前日期附近的所有数值。

### 5.2 副图：成交 / 换手（可选但建议）

放在主图下方小条，类似原版中的 “Percent shares traded”：

- 柱状图：月度成交量 / 换手率；
- 折线：`percent_shares_traded`（每个月成交量占总股本的比例）。

---

## 6. Statistical Array（多年财务表）

位置：图表下方，占据页面宽度的大表，是本页的“数据主体”，参考原版中间那块密密麻麻的多年数据表。

### 6.1 行 = 指标，列 = 年份

默认展示最近 **15 年**（或上市以来全部），每列为一个年份，如 2010, 2011, …, 2024。

建议包含（可调）：

1. **每股类指标**  
   - 每股销售收入（Sales per Share）  
   - 每股“现金流”（Cash Flow per Share = EPS + 折旧摊销/股）  
   - 每股收益（EPS）  
   - 每股股息（DPS）  
   - 每股净资产（Book Value per Share）

2. **估值/收益率**  
   - 年末 PE  
   - 年末 PB  
   - 年均股息率

3. **盈利能力**  
   - 毛利率  
   - 净利率  
   - ROE  
   - ROIC（如数据方便）

4. **现金流 & 负债**  
   - 经营性现金流（亿元）  
   - 经营性现金流 / 净利  
   - 资产负债率  
   - 有息负债率 / 利息保障倍数（选填）

5. **股本 & 其他**  
   - 总股本 / 流通股本  
   - 分红率（现金分红 / 净利）

数据来源：Tushare 的财报接口；必要时用自定义计算补齐。

### 6.2 Annual Rates of Change（年化增速区块）

在多年表下方，单独做小表，模仿 Value Line 的 “Annual Rates of Change” 区块：

展示近 5 年、10 年、未来 3–5 年（如有预测）的复合增速（CAGR）：

- Sales per Share CAGR（5y / 10y）
- EPS CAGR（5y / 10y）
- DPS CAGR（5y / 10y）
- Book Value per Share CAGR（可选）

未来 3–5 年增速可以先使用简单假设或留空。

---

## 7. 资本结构 & 资产负债简表

参考原版左下角的 “Capital Structure / Current Position”。

内容建议：

### 7.1 Capital Structure（最近一季）

- 短期借款  
- 长期借款  
- 总有息负债  
- 少数股东权益  
- 股东权益合计  
- 各项占“全部资本”的比例（%）

### 7.2 Current Position（流动性）

- 货币资金  
- 应收账款  
- 存货  
- 流动资产合计  
- 流动负债合计  
- 流动比率 / 速动比率

---

## 8. Quarterly Array（季度销售 / 盈利 / 股息）

右侧或底部补充一个类似 Value Line 的小表：

- 行：最近 8–12 个季度；
- 列：
  - 季度营业收入；
  - 季度 EPS（标明预测值用粗体或特殊标记）；
  - 季度实际分红金额（若有）。

用途：对标原版的 “Quarterly Sales / Earnings / Dividends” 区块。

---

## 9. 简要评级 & 点评区（Analyst’s Commentary）

位置：页面右下角，类似原版那段 300–400 字的分析评论。

### 9.1 自动摘要 + 预留人工修改

- 生成一段 200–400 字的中文摘要，包括：
  - 公司业务简述 & 行业定位；
  - 最近 1–2 年的关键变化（收入、利润、ROE、负债等）；
  - 当前估值处于历史哪个区间（贵/便宜/中性）；
  - 主要风险提示（政策风险、行业景气度、股权质押、商誉减值等）。

目前先允许完全由 LLM 自动生成文本；未来可扩展人工编辑。

### 9.2 附加评级（可与页眉不同）

预留展示下列指标（从数据中计算）：

- Financial Strength（财务实力，A–C 或 1–5 级）
- Price Stability（股价波动稳定度）
- Earnings Predictability（盈利可预测性）
- Price Growth Persistence（股价长期趋势持续性）

MVP 阶段可先只给出简单标签或留空。

---

## 10. 后端数据接口设计（建议）

建议统一一个函数 / API，供网页和 PDF 共同使用，例如：

```python
def get_value_line_report(ts_code: str, end_date: str) -> dict:
    """
    生成 A 股 Value Line 风格报告所需的全部数据。
    end_date 为最近交易日或用户选择的日期（YYYY-MM-DD）。
    """

    return {
        "meta": {...},              # 基本信息 & 行业
        "ranks": {...},             # Timeliness / Safety / Technical / Beta 等
        "top_metrics": {...},       # 最近价格、PE/PE 分位、股息率、目标价区间
        "chart": {...},             # 主图 & 副图数据（日期、价格、EPS、分红、ROE、相对强度等）
        "statistical_array": {...}, # 多年财务大表
        "growth_rates": {...},      # Annual Rates of Change
        "capital_structure": {...}, # 资本结构 & 流动性
        "quarterly_array": {...},   # 季度销售 / EPS / 股息
        "summary_scores": {...},    # 衍生评分（Financial Strength 等，可选）
        "commentary": "....",       # 文字点评
    }
