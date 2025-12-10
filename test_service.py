import os
import sys
import logging
import json
from services import ValueLineService

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_service():
    # Get token from env or hardcode (user should have set it in app.py)
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        # Try to read from app.py if not in env
        try:
            with open('app.py', 'r', encoding='utf-8') as f:
                content = f.read()
                if "TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '" in content:
                    start = content.find("TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '") + 44
                    end = content.find("')", start)
                    token = content[start:end]
                    print(f"Found token in app.py: {token[:5]}***")
        except:
            pass
            
    if not token or token == 'your_tushare_token_here':
        print("Please set TUSHARE_TOKEN env var or update app.py")
        return

    service = ValueLineService(token)
    
    # Test with Ping An Bank
    stock_code = '000001.SZ' 
    print(f"Fetching report for {stock_code}...")
    
    try:
        data = service.get_report_data(stock_code)
        
        # Output summary
        print("\n=== Meta ===")
        print(json.dumps(data['meta'], indent=2, ensure_ascii=False))
        
        print("\n=== Top Metrics ===")
        print(json.dumps(data['top_metrics'], indent=2))
        
        print("\n=== Statistical Array (First 2 years) ===")
        print(json.dumps(data['statistical_array']['annual_data'][:2], indent=2))

        print("\n=== Growth Rates ===")
        print(json.dumps(data.get('growth_rates'), indent=2))
        
        print("\n=== Capital Structure ===")
        print(json.dumps(data['capital_structure'], indent=2))
        
        print("\n=== Quarterly Data (First 2) ===")
        print(json.dumps(data['quarterly_array'].get('quarters', [])[:2], indent=2))
        
        print("\nSuccess!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_service()
