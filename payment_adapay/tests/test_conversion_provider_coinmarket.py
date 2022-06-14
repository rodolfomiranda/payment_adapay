# -*- coding: utf-8 -*-
import unittest
from unittest import mock
from odoo.tests import tagged
from odoo.addons.payment_adapay.connectors.currency_conversion import COINMARKET_PROVIDER, get_conversion_provider
from odoo.addons.payment_adapay.connectors.conversion_providers.coinmarket import CoinMarket
from requests import Session


@tagged('post_install', '-at_install', 'adapay', '-standard')
class CurrencyConversionCoinmarketTest(unittest.TestCase):
    def setUp(self):
        self.api_key = "API_KEY"
        self.provider = COINMARKET_PROVIDER

    def test_conversion_provider_api_productive_url(self):
        coinmarket_api = get_conversion_provider(self.provider, self.api_key)
        self.assertEqual(coinmarket_api.base_url, CoinMarket.url_production.value)

    def test_conversion_provider_api_sandbox_url(self):
        coinmarket_api = get_conversion_provider(self.provider, self.api_key, sandbox=True)
        self.assertEqual(coinmarket_api.base_url, CoinMarket.url_sandbox.value)

    @mock.patch.object(Session, 'get')
    def test_conversion_provider_amount_conversion(self, session_mock):
        iso_code_to_id_response = {
            "data": [
                {
                    "id": 2010,
                    "name": "Cardano",
                    "symbol": "ADA",
                    "slug": "cardano",
                    "rank": 8,
                    "is_active": 1,
                    "first_historical_data": "2017-10-01T20:34:01.000Z",
                    "last_historical_data": "2022-05-01T16:09:00.000Z",
                    "platform": None
                },
                {
                    "id": 2781,
                    "name": "United States Dollar",
                    "symbol": "USD",
                    "slug": "united-states-dollar",
                    "rank": None,
                    "is_active": 0,
                    "first_historical_data": "2018-09-20T15:44:19.000Z",
                    "last_historical_data": "2022-05-01T16:09:06.000Z",
                    "platform": None
                }
            ]
        }
        conversion_result_response_data = {
            "data": {
                "id": 2781,
                "symbol": "USD",
                "name": "United States Dollar",
                "amount": 1,
                "last_updated": "2022-05-01T17:14:10.000Z",
                "quote": {
                    "2010": {
                        "price": 1.9573906200919156,
                        "last_updated": "2022-05-01T17:14:00.000Z"
                    }
                }
            }
        }
        # Mock api call responses
        session_mock.side_effect = [
            mock.Mock(json=mock.Mock(return_value=iso_code_to_id_response)),  # ISO Code to coinmarket id call
            mock.Mock(json=mock.Mock(return_value=conversion_result_response_data)),  # Amount conversion call
        ]
        
        coinmarket_api = get_conversion_provider(self.provider, self.api_key)
        conversion_data = coinmarket_api.price_conversion('USD', 'ADA', 1)
        # Check requests calls
        self.assertEqual(session_mock.call_count, 2)
        self.assertEqual(session_mock.mock_calls, [
            mock.call('https://pro-api.coinmarketcap.com/v1/cryptocurrency/map',
                params={'symbol': 'USD,ADA'}, headers={'X-CMC_PRO_API_KEY': 'API_KEY'}),
            mock.call('https://pro-api.coinmarketcap.com/v2/tools/price-conversion',
                params={'amount': 1, 'id': 2781, 'convert_id': 2010}, headers={'X-CMC_PRO_API_KEY': 'API_KEY'})
            ]
        )
        # Check result
        self.assertEqual(
            conversion_data,
            {
                'price': 1.9573906200919156,
                'last_updated': '2022-05-01T17:14:00.000Z',
                'unit_price': 0.5108842301252275,
            }
        )
