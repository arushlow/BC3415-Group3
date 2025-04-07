import json
import logging
import sys
from datetime import datetime

import yfinance as yf
from mcp.server.fastmcp import FastMCP

# Configure logging to write to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("finance-mcp")

# Initialize FastMCP server
mcp = FastMCP("finance")


@mcp.tool()
async def get_income_statements(
    ticker: str,
    period: str = "yearly",
    limit: int = 4,
) -> str:
    """Get income statements for a company.

    Args:
        ticker: Ticker symbol of the company (e.g. AAPL, GOOGL)
        period: Period of the income statement (yearly or quarterly or trailing, default: yearly)
        limit: Number of income statements to return (default: 4)
    """
    try:
        # Fetch data
        data = yf.Ticker(ticker).get_income_stmt(freq=period, pretty=True, as_dict=True)

        # Check if data is found
        if not data:
            return "Unable to fetch income statements or no income statements found."

        # Check if limit is specified and filter the data
        if limit and limit < len(data):
            sorted_dates = sorted(data.keys(), reverse=True)
            limited_data = {date: data[date] for date in sorted_dates[:limit]}
            data = limited_data

        # Stringify the income statements
        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Error fetching income statements for {ticker}: {str(e)}")
        return f"Error fetching income statements for {ticker}"


@mcp.tool()
async def get_balance_sheets(
    ticker: str,
    period: str = "annual",
    limit: int = 4,
) -> str:
    """Get balance sheets for a company.

    Args:
        ticker: Ticker symbol of the company (e.g. AAPL, GOOGL)
        period: Period of the balance sheet (yearly or quarterly, default: yearly)
        limit: Number of balance sheets to return (default: 4)
    """
    try:
        # Fetch data
        data = yf.Ticker(ticker).get_balance_sheet(
            freq=period, pretty=True, as_dict=True
        )

        # Check if data is found
        if not data:
            return "Unable to fetch balance sheets or no balance sheets found."

        # Check if limit is specified and filter the data
        if limit and limit < len(data):
            sorted_dates = sorted(data.keys(), reverse=True)
            limited_data = {date: data[date] for date in sorted_dates[:limit]}
            data = limited_data

        # Stringify the balance sheets
        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Error fetching balance sheets for {ticker}: {str(e)}")
        return f"Error fetching balance sheets for {ticker}"


@mcp.tool()
async def get_cash_flow_statements(
    ticker: str,
    period: str = "annual",
    limit: int = 4,
) -> str:
    """Get cash flow statements for a company.

    Args:
        ticker: Ticker symbol of the company (e.g. AAPL, GOOGL)
        period: Period of the cash flow statement (yearly or quarterly, default: yearly)
        limit: Number of cash flow statements to return (default: 4)
    """
    try:
        # Fetch data
        data = yf.Ticker(ticker).get_cashflow(freq=period, pretty=True, as_dict=True)

        # Check if data is found
        if not data:
            return (
                "Unable to fetch cash flow statements or no cash flow statements found."
            )

        # Check if limit is specified and filter the data
        if limit and limit < len(data):
            sorted_dates = sorted(data.keys(), reverse=True)
            limited_data = {date: data[date] for date in sorted_dates[:limit]}
            data = limited_data

        # Stringify the cash flow statements
        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Error fetching cash flow statements for {ticker}: {str(e)}")
        return f"Error fetching cash flow statements for {ticker}"


@mcp.tool()
async def get_current_stock_price(ticker: str) -> str:
    """Get the current / latest price of a company.

    Args:
        ticker: Ticker symbol of the company (e.g. AAPL, GOOGL)
    """
    try:
        # Fetch stock data
        stock = yf.Ticker(ticker).get_fast_info()

        # Fetch the latest stock price using fast_info
        price_data = {
            "symbol": ticker,
            "currentPrice": stock["lastPrice"],
            "dayHigh": stock["dayHigh"],
            "dayLow": stock["dayLow"],
            "previousClose": stock["previousClose"],
            "open": stock["open"],
            "volume": stock["lastVolume"],
        }

        return json.dumps(price_data, indent=2)
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {str(e)}")
        return f"Error fetching price data for {ticker}"


@mcp.tool()
async def get_historical_stock_prices(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> str:
    """Gets historical stock prices for a company.

    Args:
        ticker: Ticker symbol of the company (e.g. AAPL, GOOGL)
        period: Period of the price data (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max)
        interval: Interval of the price data (1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo)
    """
    try:
        # Fetch data
        data = yf.Ticker(ticker).history(period=period, interval=interval)

        # Check if data is found
        if data.empty:
            return "Unable to fetch prices or no prices found."

        # Extract the prices
        result = []
        for date, row in data.iterrows():
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"],
            })

        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error fetching historical prices for {ticker}: {str(e)}")
        return f"Error fetching historical prices for {ticker}"


@mcp.tool()
async def get_company_news(ticker: str) -> str:
    """Get news for a company.

    Args:
        ticker: Ticker symbol of the company (e.g. AAPL, GOOGL)
    """
    try:
        # Fetch data
        data = yf.Ticker(ticker).get_news()

        # Check if data is found
        if not data:
            return "Unable to fetch news or no news found."
        
        news = []
        for item in data:
            news_item = {
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "publishTime": datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                "type": item.get("type", ""),
                "relatedTickers": item.get("relatedTickers", [])
            }
            news.append(news_item)

        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {str(e)}")
        return f"Error fetching news for {ticker}"


if __name__ == "__main__":
    # Log server startup
    logger.info("Starting Finance MCP Server...")

    # Initialize and run the server
    mcp.run(transport="stdio")

    # This line won't be reached during normal operation
    logger.info("Server stopped")
