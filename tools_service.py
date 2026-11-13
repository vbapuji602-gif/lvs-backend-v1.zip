"""
Small read-only data tools: live weather and crypto prices.
"""
import httpx

from ..config import BackendConfig


class ToolServiceError(Exception):
    pass


async def get_weather(location: str) -> dict:
    if not BackendConfig.WEATHERAPI_KEY:
        raise ToolServiceError("WEATHERAPI_KEY is not configured on the backend")
    url = "https://api.weatherapi.com/v1/current.json"
    params = {"key": BackendConfig.WEATHERAPI_KEY, "q": location, "aqi": "no"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise ToolServiceError(f"WeatherAPI error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return {
            "location": data.get("location", {}).get("name"),
            "region": data.get("location", {}).get("region"),
            "temp_c": data.get("current", {}).get("temp_c"),
            "condition": data.get("current", {}).get("condition", {}).get("text"),
            "humidity": data.get("current", {}).get("humidity"),
            "wind_kph": data.get("current", {}).get("wind_kph"),
        }


async def get_crypto_price(coin_id: str, vs_currency: str = "usd") -> dict:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": vs_currency, "include_24hr_change": "true"}
    headers = {}
    if BackendConfig.COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = BackendConfig.COINGECKO_API_KEY
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise ToolServiceError(f"CoinGecko error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if coin_id not in data:
            raise ToolServiceError(f"Unknown coin id: {coin_id}")
        return {"coin": coin_id, "currency": vs_currency, **data[coin_id]}
