# 大鸡腿股票估值系统 (Stock PE Analysis System)

本项目是一个专注于A股市场数据的股票分析工具，提供股价、市盈率（PE TTM）和净资产收益率（ROE）的可视化分析。后端采用 FastAPI 框架，数据源使用 Tushare Pro。

## 项目概览

-   **目标:** 分析并可视化 A 股股票估值指标（股价、PE、ROE）。
-   **前端:** HTML5, CSS3, JavaScript (原生), Plotly.js (通过 CDN 引入)。
-   **后端:** Python 3.8+, FastAPI, Uvicorn。
-   **数据源:** Tushare Pro API (需要 Token)。
-   **主要功能:**
    -   拥有三个坐标轴（股价、PE、ROE）的交互式图表。
    -   支持按代码或名称搜索股票。
    -   支持自定义时间范围的历史数据分析。

## 目录结构

-   `app.py`: FastAPI 应用的主要入口文件。处理 API 端点并提供静态 HTML 页面服务。
-   `index.html`: 单页前端应用。包含用户界面、样式 (CSS) 和数据获取与可视化的逻辑 (JS)。
-   `requirements.txt`: Python 依赖列表。
-   `.vscode/`: VS Code 配置文件。

## 构建与运行

### 前置要求

-   Python 3.8 或更高版本。
-   Tushare Pro Token (可以在 [Tushare](https://tushare.pro/) 获取)。

### 安装步骤

1.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **环境配置:**
    设置 `TUSHARE_TOKEN` 环境变量。
    *   **Windows (PowerShell):** `$env:TUSHARE_TOKEN="你的token"`
    *   **Linux/macOS:** `export TUSHARE_TOKEN="你的token"`
    *   *替代方案:* 直接修改 `app.py` (不建议用于生产环境) 来设置 `TUSHARE_TOKEN` 的默认值。

3.  **启动服务:**
    ```bash
    python app.py
    ```
    服务将在 `http://0.0.0.0:8000` 启动。

4.  **访问应用:**
    打开浏览器访问 `http://localhost:8000`。
    API 文档地址: `http://localhost:8000/docs`。

## 开发规范

-   **后端:**
    -   遵循标准的 FastAPI 模式。
    -   使用 `pydantic` 进行数据验证 (Request/Response 模型)。
    -   使用 `HTTPException` 处理错误。
    -   日志配置为输出到标准输出 (stdout)。
    -   数据处理使用 `pandas`。
-   **前端:**
    -   为保持简单，使用单文件 HTML 结构。
    -   样式内嵌在 `<style>` 标签中。
    -   JavaScript 逻辑内嵌在 `<script>` 标签中。
    -   使用 async/await 进行 API 调用。
    -   使用 Plotly.js 绘制图表，配置了多 Y 轴显示。
-   **数据处理:**
    -   股票代码会自动转换为 Tushare 格式 (例如: `000001` -> `000001.SZ`)。
    -   `pe_ttm` 和 `roe` 设有默认值和边界限制，以防止图表显示异常。

## 主要 API

-   `GET /`: 返回 `index.html` 页面。
-   `POST /api/stock_data`: 获取指定股票和日期范围的历史数据 (股价, PE, ROE)。
-   `GET /api/stock_search/{keyword}`: 按代码或名称搜索股票。
-   `GET /api/health`: 健康检查接口。