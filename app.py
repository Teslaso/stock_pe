from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
# akshare已移除，专注使用Tushare Pro数据源
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import uvicorn
from typing import Optional
import logging
import os

from services import ValueLineService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置Tushare Pro API
# 注意：请设置环境变量 TUSHARE_TOKEN 或在此处直接设置token
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', 'your_tushare_token_here')
if TUSHARE_TOKEN and TUSHARE_TOKEN != 'your_tushare_token_here':
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    vl_service = ValueLineService(TUSHARE_TOKEN)
    logger.info("✅ Tushare Pro API 初始化成功")
else:
    pro = None
    vl_service = None
    logger.error("❌ Tushare Pro token未配置，请设置TUSHARE_TOKEN环境变量")

app = FastAPI(title="A股股票分析API", description="基于Tushare Pro的股票数据分析服务")
app.mount("/static", StaticFiles(directory="."), name="static")

def convert_to_ts_code(stock_code: str) -> str:
    """
    将6位股票代码转换为Tushare格式的TS代码
    例如: 000001 -> 000001.SZ, 600000 -> 600000.SH
    """
    if stock_code.startswith('6'):
        return f"{stock_code}.SH"  # 上海交易所
    elif stock_code.startswith(('0', '3')):
        return f"{stock_code}.SZ"  # 深圳交易所
    else:
        return f"{stock_code}.SH"  # 默认上海交易所

def get_stock_data_tushare(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用Tushare Pro获取股票历史数据和PE_TTM数据
    """
    if not pro:
        raise Exception("Tushare Pro API未初始化")
    
    try:
        # 转换日期格式为YYYYMMDD
        start_date_ts = start_date.replace('-', '')
        end_date_ts = end_date.replace('-', '')
        
        # 获取股票基本行情数据
        stock_data = ts.pro_bar(ts_code=ts_code, start_date=start_date_ts, end_date=end_date_ts, adj='qfq')
        
        if stock_data.empty:
            raise Exception(f"未找到股票 {ts_code} 的历史数据")
        
        # 获取每日基本面指标（包含PE_TTM）
        basic_data = pro.daily_basic(ts_code=ts_code, start_date=start_date_ts, end_date=end_date_ts, 
                                   fields='ts_code,trade_date,pe_ttm,pb,ps_ttm')
        
        # 获取财务指标数据（包含ROE）
        # 由于财务数据是季度数据，我们需要获取最近的财务数据
        fina_data = pro.fina_indicator(ts_code=ts_code, start_date=start_date_ts, end_date=end_date_ts,
                                     fields='ts_code,end_date,roe')
        
        # 合并数据
        if not basic_data.empty:
            merged_data = pd.merge(stock_data, basic_data, on=['ts_code', 'trade_date'], how='left')
        else:
            merged_data = stock_data
            merged_data['pe_ttm'] = None
        
        # 处理ROE数据（季度数据需要前向填充）
        if not fina_data.empty:
            # 将财务数据的end_date转换为trade_date格式
            fina_data['trade_date'] = fina_data['end_date']
            fina_data = fina_data.drop('end_date', axis=1)
            
            # 合并ROE数据
            merged_data = pd.merge(merged_data, fina_data, on=['ts_code', 'trade_date'], how='left')
            
            # 前向填充ROE数据（因为ROE是季度数据）
            merged_data['roe'] = merged_data['roe'].fillna(method='ffill')
        else:
            merged_data['roe'] = None
        
        # 按日期排序
        merged_data = merged_data.sort_values('trade_date')
        
        return merged_data
        
    except Exception as e:
        logger.error(f"Tushare Pro获取数据失败: {e}")
        raise e

@app.get("/api/value_line_report/{stock_code}")
async def get_value_line_report(stock_code: str):
    """
    获取Value Line风格的深度研报数据
    """
    if not vl_service:
        raise HTTPException(status_code=500, detail="服务未初始化 (Token缺失)")
    
    try:
        logger.info(f"生成研报: {stock_code}")
        data = vl_service.get_report_data(stock_code)
        return data
    except Exception as e:
        logger.error(f"研报生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class StockRequest(BaseModel):
    stock_code: str
    start_date: str
    end_date: str

class StockResponse(BaseModel):
    stock_name: str
    stock_code: str
    dates: list
    prices: list
    pe_ratios: list
    roe_ratios: list
    pb_ratios: list
    error: Optional[str] = None

@app.get("/")
async def read_root():
    """返回主页面"""
    return FileResponse('index.html')

@app.post("/api/stock_data", response_model=StockResponse)
async def get_stock_data(request: StockRequest):
    """
    获取股票历史数据和市盈率数据 - 使用Tushare Pro API
    """
    try:
        stock_code = request.stock_code.strip()
        start_date = request.start_date
        end_date = request.end_date
        
        logger.info(f"获取股票数据: {stock_code}, {start_date} 到 {end_date}")
        
        # 验证股票代码格式
        if len(stock_code) != 6 or not stock_code.isdigit():
            raise HTTPException(status_code=400, detail="股票代码格式错误，请输入6位数字")
        
        # 验证日期格式
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误")
        
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="开始日期必须早于结束日期")
        
        # 转换为Tushare格式的股票代码
        ts_code = convert_to_ts_code(stock_code)
        logger.info(f"转换后的TS代码: {ts_code}")
        
        # 获取股票名称
        stock_name = f"股票{stock_code}"
        try:
            if pro:
                # 使用Tushare Pro获取股票基本信息
                stock_basic = pro.stock_basic(ts_code=ts_code, fields='ts_code,name')
                if not stock_basic.empty:
                    stock_name = stock_basic['name'].iloc[0]
                    logger.info(f"✅ 获取股票名称: {stock_name}")
        except Exception as e:
            logger.warning(f"获取股票基本信息失败: {e}")
        
        # 获取股票历史数据和市盈率数据
        if not pro:
            raise HTTPException(status_code=500, detail="Tushare Pro未配置，无法获取数据")
        
        try:
            stock_data = get_stock_data_tushare(ts_code, start_date, end_date)
            if stock_data.empty:
                raise HTTPException(status_code=404, detail="未找到该股票的历史数据")
            logger.info(f"✅ 使用Tushare Pro获取到{len(stock_data)}条数据")
        except Exception as e:
            logger.error(f"Tushare Pro获取数据失败: {e}")
            raise HTTPException(status_code=500, detail=f"获取股票数据失败: {str(e)}")
        
        # 数据处理和准备返回
        
        # Tushare Pro数据格式：trade_date, close, pe_ttm
        stock_data['trade_date'] = pd.to_datetime(stock_data['trade_date'])
        stock_data = stock_data.sort_values('trade_date')
        
        dates = stock_data['trade_date'].dt.strftime('%Y-%m-%d').tolist()
        prices = stock_data['close'].tolist()
        
        # 处理市盈率数据
        pe_ratios = []
        for _, row in stock_data.iterrows():
            pe_value = row.get('pe_ttm', 20.0)
            if pd.isna(pe_value) or pe_value <= 0 or pe_value > 1000:
                pe_value = 20.0  # 默认值
            pe_ratios.append(float(pe_value))
        
        # 处理ROE数据
        roe_ratios = []
        for _, row in stock_data.iterrows():
            roe_value = row.get('roe', 10.0)
            if pd.isna(roe_value) or roe_value < -100 or roe_value > 100:
                roe_value = 10.0  # 默认值10%
            roe_ratios.append(float(roe_value))

        # 处理PB数据
        pb_ratios = []
        for _, row in stock_data.iterrows():
            pb_value = row.get('pb', 1.0)
            if pd.isna(pb_value):
                pb_value = 1.0  # 默认值
            pb_ratios.append(float(pb_value))
        
        logger.info(f"✅ 使用Tushare Pro数据，共{len(stock_data)}条记录")
        logger.info(f"✅ 市盈率范围: {min(pe_ratios):.2f} - {max(pe_ratios):.2f}")
        logger.info(f"✅ ROE范围: {min(roe_ratios):.2f}% - {max(roe_ratios):.2f}%")
        logger.info(f"✅ PB范围: {min(pb_ratios):.2f} - {max(pb_ratios):.2f}")
        
        # 数据验证
        if len(dates) == 0:
            raise HTTPException(status_code=404, detail="指定时间范围内没有交易数据")
        
        # 返回数据
        return StockResponse(
            stock_name=stock_name,
            stock_code=stock_code,
            dates=dates,
            prices=prices,
            pe_ratios=pe_ratios,
            roe_ratios=roe_ratios,
            pb_ratios=pb_ratios
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票数据时发生未知错误: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/api/stock_search/{keyword}")
async def search_stocks(keyword: str):
    """
    搜索股票代码和名称
    """
    try:
        if not pro:
            raise HTTPException(status_code=500, detail="Tushare Pro未配置")
        
        # 获取A股股票列表
        stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
        
        # 搜索匹配的股票
        if keyword.isdigit():
            # 如果是数字，按代码搜索
            results = stock_list[stock_list['symbol'].str.contains(keyword, na=False)]
        else:
            # 如果是文字，按名称搜索
            results = stock_list[stock_list['name'].str.contains(keyword, na=False)]
        
        # 限制返回结果数量
        results = results.head(10)
        
        return {
            "results": [
                {"code": row['symbol'], "name": row['name']} 
                for _, row in results.iterrows()
            ]
        }
        
    except Exception as e:
        logger.error(f"搜索股票时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    """
    健康检查接口
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("🚀 启动A股股票分析服务...")
    print("📊 访问 http://localhost:8000 查看股票分析工具")
    print("📖 API文档: http://localhost:8000/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )