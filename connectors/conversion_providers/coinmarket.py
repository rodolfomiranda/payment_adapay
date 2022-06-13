from enum import Enum
from datetime import date
from locale import currency
from urllib.parse import urljoin
from requests import Session


class CoinMarket(Enum):
    # Urls
    url_production = "https://pro-api.coinmarketcap.com"
    url_sandbox = "https://sandbox-api.coinmarketcap.com"
    # Sandbox api-key
    sandbox_api_key = "b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c"
    # Paths
    price_convertion = "/v2/tools/price-conversion"
    currency_data = "/v1/cryptocurrency/map"


class CoinMarketConversion:
    """CoinMarket API implementation.
    For API details visit https://coinmarketcap.com/api/documentation/v1/
    """
    _session = Session()

    def __init__(self, base_url, api_key, sandbox):
        self.sandbox = sandbox
        self.base_url = base_url
        self.headers = {
            "X-CMC_PRO_API_KEY": f"{api_key}",
        }
        # HTTP Error See https://coinmarketcap.com/api/documentation/v1/#section/Errors-and-Rate-Limits
        raise_for_status_hook = lambda response, **_: response.raise_for_status()
        self._session.hooks['response'] = raise_for_status_hook

    def _get_url(self, url_path):
        return urljoin(self.base_url, url_path)

    def price_conversion(self, amount_currency, convert_currency, amount):
        """Convert amounts between currencies

        Args:
            amount_currency (str): ISO Format for the amount currency.
            convert_currency (str): ISO Format for the target currency.
            amount (float): Current amount

        Returns:
            dict: Dict with keys `price`, `unit_price`, and `last_updated` for target currency.
        """
        amount_id, convert_id = self._currency_ids(amount_currency, convert_currency)

        response = self._session.get(
            self._get_url(CoinMarket.price_convertion.value),
            params=self._get_params_conversion(amount, amount_id, convert_id),
            headers=self.headers
        ).json()

        # Data structure is diferent between sandbox and production
        quote_data = response[str(convert_id)]["data"] if self.sandbox else response["data"]
        # Conversion data
        conv_data = quote_data["quote"][str(convert_id)]
        conv_data['unit_price'] = float(amount / conv_data["price"])
        return quote_data["quote"][str(convert_id)]  # 'last_updated', price'

    def _get_params_conversion(self, amount, amount_id, convert_id):
        return {"amount": amount, "id": amount_id, "convert_id": convert_id}

    def _currency_ids(self, from_currency: str, to_currency: str):
        """Get id from currencies in ISO format.

        Args:
            from_currency (str):  ISO format for current currency.
            to_currency (str): ISO format for target currency.

        Returns:
            tuple(int, int): id for current currency, if for target currency
        """
        currency_request_data = self._session.get(
            self._get_url(CoinMarket.currency_data.value),
            params={"symbol": f'{from_currency},{to_currency}'},
            headers=self.headers
        ).json()

        currency_coinmarket_data = {
            currency.get('symbol'): currency.get('id')
            for currency in currency_request_data.get('data', [])
            if currency.get('symbol') and currency.get('id') is not None
        }

        return currency_coinmarket_data.get(from_currency), currency_coinmarket_data.get(to_currency)


def get_coinmarket(api_key=None, sandbox=False):
    url = CoinMarket.url_sandbox.value if sandbox else CoinMarket.url_production.value
    if not api_key and sandbox:
        # Use default `api_key` for CoinMaket
        api_key = CoinMarket.sandbox_api_key.value
    return CoinMarketConversion(url, api_key, sandbox)
