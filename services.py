import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValueLineService:
    def __init__(self, token: str):
        self.token = token
        ts.set_token(token)
        self.pro = ts.pro_api()

    def get_report_data(self, stock_code: str) -> Dict[str, Any]:
        """
        Orchestrator to get all data for the Value Line style report.
        stock_code: Input code (e.g., '000001' or '000001.SZ')
        """
        ts_code = self._ensure_ts_code(stock_code)
        
        # 1. Basic Info & Meta
        meta = self._get_meta_info(ts_code)
        
        # 2. Historical Market Data (Price, PE, PB, etc.) - Last 15 years approx
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365*15)).strftime('%Y%m%d')
        daily_df = self._get_daily_market_data(ts_code, start_date, end_date)
        
        # 3. Financial Statistical Array (Annual Data)
        financials = self._get_annual_financials(ts_code, start_date, end_date)
        
        # 4. Calculate Derived Metrics (CAGR, Per Share, etc.)
        stats_array = self._calculate_statistical_array(financials, daily_df)
        
        # 4b. Calculate Growth Rates (CAGR)
        growth_rates = self._calculate_growth_rates(stats_array)
        
        # 5. Generate Ranks (MVP)
        ranks = self._generate_ranks(ts_code, daily_df, stats_array)

        # 6. Top Metrics Strip
        top_metrics = self._calculate_top_metrics(daily_df, stats_array)
        
        # 7. Quarterly Data (Recent 8-12 quarters)
        quarterly = self._get_quarterly_data(ts_code)

        # 8. Capital Structure (Latest)
        capital_struct = self._get_capital_structure(ts_code)
        
        # 9. Commentary (Placeholder)
        commentary = self._generate_commentary(meta, top_metrics, ranks)

        raw_data = {
            "meta": meta,
            "ranks": ranks,
            "top_metrics": top_metrics,
            "chart": {
                "dates": daily_df['trade_date'].tolist(),
                "price": daily_df['close'].tolist(),
                "pe": daily_df['pe_ttm'].tolist(),
                "pb": daily_df['pb'].tolist(),
                "roe": daily_df.get('roe_ttm', []).tolist() if 'roe_ttm' in daily_df else []
            },
            "statistical_array": stats_array,
            "growth_rates": growth_rates,
            "capital_structure": capital_struct,
            "quarterly_array": quarterly,
            "commentary": commentary
        }
        
        return self._clean_data(raw_data)

    def _clean_data(self, data):
        """Recursively replace NaN/Inf with None for JSON compliance"""
        if isinstance(data, dict):
            return {k: self._clean_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data(v) for v in data]
        elif isinstance(data, float):
            if np.isnan(data) or np.isinf(data):
                return None
            return data
        else:
            return data

    def _ensure_ts_code(self, code: str) -> str:
        if code.endswith('.SZ') or code.endswith('.SH') or code.endswith('.BJ'):
            return code
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith('8') or code.startswith('4'):
            return f"{code}.BJ"
        else:
            return f"{code}.SZ"

    def _get_meta_info(self, ts_code: str) -> Dict:
        """Fetch basic stock info"""
        df = self.pro.stock_basic(ts_code=ts_code, fields='ts_code,symbol,name,fullname,industry,market,list_date')
        if df.empty:
            raise ValueError(f"Stock {ts_code} not found.")
        
        row = df.iloc[0]
        return {
            "ts_code": row['ts_code'],
            "name": row['name'],
            "fullname": row['fullname'],
            "industry": row['industry'],
            "market": row['market'],
            "list_date": row['list_date'],
            "report_date": datetime.now().strftime('%Y-%m-%d')
        }

    def _get_daily_market_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get daily price + valuation metrics (PE, PB)"""
        # Get Price
        df_price = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
        if df_price is None or df_price.empty:
            return pd.DataFrame()
            
        # Get Valuation (PE, PB, turnover)
        df_basic = self.pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date, 
                                        fields='ts_code,trade_date,pe_ttm,pb,dv_ratio,turnover_rate,total_mv')
        
        # Merge
        df_price['trade_date'] = df_price['trade_date'].astype(str)
        if not df_basic.empty:
            df = pd.merge(df_price, df_basic, on=['ts_code', 'trade_date'], how='left')
        else:
            df = df_price
            
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    def _get_annual_financials(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch Income, Balance Sheet, Cash Flow, Fina Indicator for Annual Reports (end_type='4')
        """
        fields_income = 'ts_code,end_date,total_revenue,n_income' 
        fields_bal = 'ts_code,end_date,total_share,total_hldr_eqy_exc_min_int,total_liab,total_assets' 
        fields_cash = 'ts_code,end_date,n_cashflow_act,c_paid_for_fix_assets' 
        fields_fina = 'ts_code,end_date,roe,grossprofit_margin,netprofit_margin' 
        
        def get_sheet(api_func, fields):
            try:
                df = api_func(ts_code=ts_code, start_date=start_date, end_date=end_date, fields=fields)
                if df.empty: return pd.DataFrame()
                df = df[df['end_date'].str.endswith('1231')]
                return df.drop_duplicates(subset=['end_date'])
            except Exception as e:
                logger.warning(f"Error fetching financial sheet: {e}")
                return pd.DataFrame()

        df_inc = get_sheet(self.pro.income, fields_income)
        df_bal = get_sheet(self.pro.balancesheet, fields_bal)
        df_cash = get_sheet(self.pro.cashflow, fields_cash)
        df_fina = get_sheet(self.pro.fina_indicator, fields_fina)

        dfs = [df_inc, df_bal, df_cash, df_fina]
        dfs = [d for d in dfs if not d.empty]
        
        if not dfs:
            return pd.DataFrame()
            
        merged = dfs[0]
        for d in dfs[1:]:
            merged = pd.merge(merged, d, on=['ts_code', 'end_date'], how='outer')
            
        merged = merged.sort_values('end_date').reset_index(drop=True)
        return merged

    def _calculate_statistical_array(self, financials: pd.DataFrame, daily_df: pd.DataFrame) -> Dict:
        """Transform raw financials into the Statistical Array format"""
        if financials.empty:
            return {}

        data = []
        for _, row in financials.iterrows():
            year = row['end_date'][:4]
            shares = row.get('total_share', 0)
            if pd.isna(shares) or shares == 0:
                shares = 1 
                
            sales_ps = row.get('total_revenue', 0) / shares
            eps = row.get('n_income', 0) / shares
            bvps = row.get('total_hldr_eqy_exc_min_int', 0) / shares
            cf_ps = row.get('n_cashflow_act', 0) / shares
            
            roe = row.get('roe', 0)
            net_margin = row.get('netprofit_margin', 0)
            
            year_daily = daily_df[daily_df['trade_date'].str.startswith(year)]
            if not year_daily.empty:
                last_day = year_daily.iloc[-1]
                pe = last_day.get('pe_ttm', 0)
                pb = last_day.get('pb', 0)
            else:
                pe = 0
                pb = 0

            data.append({
                "year": year,
                "sales_per_share": round(sales_ps, 2),
                "eps": round(eps, 2),
                "cash_flow_per_share": round(cf_ps, 2),
                "book_value_per_share": round(bvps, 2),
                "pe_year_end": round(pe, 1) if pe else None,
                "pb_year_end": round(pb, 2) if pb else None,
                "roe": round(roe, 2),
                "net_margin": round(net_margin, 2),
                "shares_outstanding": round(shares / 100000000, 2) 
            })
            
        return {"annual_data": data}

    def _calculate_top_metrics(self, daily_df: pd.DataFrame, stats_array: Dict) -> Dict:
        """Calculate header strip metrics"""
        if daily_df.empty:
            return {}
            
        latest = daily_df.iloc[-1]
        pe_history = daily_df['pe_ttm'].dropna()
        pe_median = pe_history.median() if not pe_history.empty else 0
        
        return {
            "recent_price": latest['close'],
            "pe_ttm": latest['pe_ttm'],
            "pe_10y_median": round(pe_median, 1),
            "div_yield": latest.get('dv_ratio', 0),
            "market_cap": latest.get('total_mv', 0)
        }

    def _generate_ranks(self, ts_code: str, daily_df: pd.DataFrame, stats_array: Dict) -> Dict:
        """MVP Ranks"""
        return {
            "timeliness": 3,
            "safety": 3,
            "technical": 3,
            "beta": 1.00
        }

    def _calculate_growth_rates(self, stats_array: Dict) -> Dict:
        """Calculate 5y and 10y CAGR for Sales, EPS, Div"""
        data = stats_array.get("annual_data", [])
        if not data: return {}
        
        # Sort by year ascending just in case
        data.sort(key=lambda x: x['year'])
        
        def calc_cagr(key, years):
            if len(data) < years + 1: return None
            end_val = data[-1].get(key)
            start_val = data[-(years+1)].get(key)
            
            if not start_val or not end_val or start_val <= 0 or end_val <= 0:
                return None
            
            try:
                cagr = (end_val / start_val) ** (1/years) - 1
                return round(cagr * 100, 2)
            except:
                return None

        return {
            "sales_5y": calc_cagr("sales_per_share", 5),
            "sales_10y": calc_cagr("sales_per_share", 10),
            "eps_5y": calc_cagr("eps", 5),
            "eps_10y": calc_cagr("eps", 10),
            "bvps_5y": calc_cagr("book_value_per_share", 5),
            "bvps_10y": calc_cagr("book_value_per_share", 10)
        }

    def _get_quarterly_data(self, ts_code: str) -> Dict:
        """Get recent quarters data with single-quarter calculation"""
        try:
            # Fetch last 6 periods to ensure we can calc 4-5 quarters
            df = self.pro.income(ts_code=ts_code, period='', limit=8, fields='end_date,report_type,total_revenue,n_income')
            if df.empty: return {}
            
            df['end_date'] = pd.to_datetime(df['end_date'])
            df = df.sort_values('end_date')
            
            quarters = []
            
            # Simple logic: if Q1, take value. If Q2/3/4, subtract prev.
            # Requires that we have the sequence.
            
            for i in range(1, len(df)):
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                
                curr_date = curr['end_date']
                prev_date = prev['end_date']
                
                # Check if same year
                if curr_date.year == prev_date.year:
                    # Check if consecutive quarters (approx 3 months)
                    delta_days = (curr_date - prev_date).days
                    if 80 < delta_days < 100:
                        q_rev = curr['total_revenue'] - prev['total_revenue']
                        q_inc = curr['n_income'] - prev['n_income']
                    else:
                        # Fallback or Q1
                        if curr_date.month == 3:
                             q_rev = curr['total_revenue']
                             q_inc = curr['n_income']
                        else:
                            # Skip if gap is too large (e.g. missing Q2)
                            continue
                else:
                    # New year, likely Q1
                    if curr_date.month == 3:
                        q_rev = curr['total_revenue']
                        q_inc = curr['n_income']
                    else:
                        continue
                
                quarters.append({
                    "date": curr_date.strftime('%Y-%m-%d'),
                    "revenue": round(q_rev / 100000000, 2), # In 100M
                    "eps": round(q_inc / 100000000, 2) # Just showing Net Income in 100M for now as EPS needs shares
                })
                
            # Reverse to show newest first
            return {"quarters": quarters[::-1]}
        except Exception as e:
            logger.warning(f"Quarterly calc error: {e}")
            return {}

    def _get_capital_structure(self, ts_code: str) -> Dict:
        """Latest Balance Sheet Info"""
        try:
            df = self.pro.balancesheet(ts_code=ts_code, limit=1, fields='total_assets,total_liab,total_hldr_eqy_exc_min_int,money_cap,short_loan,long_loan')
            if df.empty: return {}
            row = df.iloc[0]
            
            return {
                "total_assets": row['total_assets'],
                "total_liab": row['total_liab'],
                "equity": row['total_hldr_eqy_exc_min_int'],
                "cash": row['money_cap'],
                "debt": (row.get('short_loan') or 0) + (row.get('long_loan') or 0)
            }
        except:
            return {}

    def _generate_commentary(self, meta, top_metrics, ranks):
        return f"{meta['name']} ({meta['ts_code']}) 属于 {meta['industry']} 行业。当前股价 {top_metrics.get('recent_price')}，PE(TTM) 为 {top_metrics.get('pe_ttm')}。"
