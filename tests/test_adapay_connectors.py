# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
from odoo.tests import tagged
from odoo.addons.payment_adapay.connectors.adapay import get_adapay_api, AdaPayUrl
from requests import Session


@tagged('post_install', '-at_install', 'adapay', '-standard')
class AdapayConnectorTest(unittest.TestCase):
    def setUp(self):
        self.api_key = "API_KEY"

    def test_adapay_get_adapay_api_productive_url(self):
        adapay_api = get_adapay_api(self.api_key)
        self.assertEqual(adapay_api.base_url, AdaPayUrl.url_production.value)

    def test_adapay_get_adapay_api_sandbox_url(self):
        adapay_api = get_adapay_api(self.api_key, sandbox=True)
        self.assertEqual(adapay_api.base_url, AdaPayUrl.url_sandbox.value)

    @patch.object(Session, 'put')
    def test_adapay_adapay_api_create_payment(self, session_mock):
        adapay_api = get_adapay_api(self.api_key)
        adapay_api.create_payment(10.22, 15, "test@test.com", "description", "name", "order_id", None)
        session_mock.assert_called_with(
            'https://api.adapay.finance/payment-request',
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            json={'amount': 10220000,
                'description': 'description',
                'name': 'name',
                'orderId': 'order_id',
                'paymentRequestExpirationTime': 15,
                'receiptEmail': 'test@test.com'})

    @patch.object(Session, 'post')
    def test_adapay_adapay_get_payment(self, session_mock):
        adapay_api = get_adapay_api(self.api_key)
        adapay_api.get_payment()
        session_mock.assert_called_with(
            'https://api.adapay.finance/payment-request/find',
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            json={})

    @patch.object(Session, 'post')
    def test_adapay_adapay_get_payment_by_uuid(self, session_mock):
        adapay_api = get_adapay_api(self.api_key)
        adapay_api.get_payment_by_uuid("test_uuid")
        session_mock.assert_called_with(
            'https://api.adapay.finance/payment-request/get-by-uuid',
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            json={'uuid': 'test_uuid'})
