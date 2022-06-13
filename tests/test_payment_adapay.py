# -*- coding: utf-8 -*-

from odoo import fields
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_paypal.controllers.main import PaypalController
from werkzeug import urls

from odoo.tools import mute_logger
from odoo.tests import tagged
from lxml import objectify

from unittest import mock
from odoo.addons.payment_adapay.connectors.conversion_providers.coinmarket import CoinMarketConversion
from odoo.addons.payment_adapay.connectors.adapay import AdaPayMerchantApi


coinmarket_conversion_response = {
    'price': 1.9573906200919156,
    'last_updated': '2022-05-01T17:14:00.000Z',
    'unit_price': 0.5108842301252275,
}

adapay_api_create_payment_response = {
    'uuid': 'test_uuid0'
}

adapay_api_get_by_uuid_response = {
    "uuid": "test_uuid0",
    "amount": "100000000",
    "status": "new",
    "subStatus": "",
    "address": "addr_test1fake",
    "expirationDate": "2022-05-03T16:29:11.000Z",
    "description": "test_ref_ada_1",
    "name": "test_ref_ada_1",
    "orderId": "test_ref_ada_1",
    "returnUrl": None,
    "addressForRefund": None,
    "email": "test@test.net",
    "companyName": "fake",
    "logoUrl": "default",
    "confirmedAmount": "0",
    "pendingAmount": "0",
    "createTime": "2022-05-03T16:14:11.000Z",
    "updateTime": "2022-05-03T16:33:55.000Z",
    "transactions": []
}


class AdapayCommon(PaymentAcquirerCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.adapay = cls.env.ref('payment_adapay.payment_acquirer_adapay')

        cls.adapay.write({
            'adapay_api_key': 'API_KEY',
            'adapay_expiration_minutes': 15,
            'state': 'test',
            'adapay_use_webhook': True,
        })
        # override defaults for helpers
        cls.acquirer = cls.adapay


@tagged('post_install', '-at_install', 'adapay', '-standard')
class AdapayTest(AdapayCommon):
    #Mock conversion and adapay api responses
    @mock.patch.object(CoinMarketConversion, 'price_conversion', return_value=coinmarket_conversion_response)
    @mock.patch.object(AdaPayMerchantApi, 'create_payment', return_value=adapay_api_create_payment_response)
    @mock.patch.object(AdaPayMerchantApi, 'get_payment_by_uuid', return_value=adapay_api_get_by_uuid_response)
    @mute_logger('odoo.addons.payment_adapay.models.payment')
    def test_payment_adapay_form_render(self, *_):
        self.assertEqual(self.adapay.state, 'test')

        res = self.adapay.render(  # Payment button, Adapay payment creation
            'test_ref_ada_1', 100, self.currency_euro.id,
            values=self.buyer_values).decode()

        # check form result
        tree = objectify.fromstring(f"<div>{res}</div>")
        expected_post_form_values = {
            'data_set': None,
            'reference': 'test_ref_ada_1',
            'amount': '100.0',
            'currency_id': '1',
            'currency': 'EUR',
            'currency_code': 'EUR',
            'partner_id': None,
            'partner_email': 'norbert.buyer@example.com',
            'partner_lang': 'en_US',
            'ada_amount': '1.96',
            'last_updated': '2022-05-01T17:14:00.000Z',
            'ada_currency': 'ADA',
            'provider': 'coinmarket',
            'adapay_uuid': 'test_uuid0',
            'adapay_amount': '100000000',
            'adapay_total_amount_sent': '0',
            'adapay_total_amount_left': '0',
            'adapay_expiration_date': '2022-05-03T16:29:11.000Z',
            'adapay_update_time': '2022-05-03T16:33:55.000Z',
            'adapay_last_updated': '2022-05-03T16:33:55.000Z',
            'adapay_expiration_minutes': '15',
            'adapay_status': 'new',
            'adapay_address': 'addr_test1fake',
        }
        self.assertEqual(
            expected_post_form_values,
            {input.get("name"):input.get("value") for input in tree.iterchildren()}
        )

    @mute_logger('odoo.addons.payment_adapay.models.payment')
    def test_adapay_form_validate_and_update_via_webhook(self):
        self.assertEqual(self.adapay.state, 'test')

        # data posted to internal form
        post_form_values = {
            'reference': 'test_ref_ada_1',
            'amount': '100.0',
            'currency_id': '1',
            'currency': 'EUR',
            'currency_code': 'EUR',
            'partner_id': None,
            'partner_email': 'norbert.buyer@example.com',
            'partner_lang': 'en_US',
            'ada_amount': '1.96',
            'last_updated': '2022-05-01T17:14:00.000Z',
            'ada_currency': 'ADA',
            'provider': 'coinmarket',
            'adapay_uuid': 'test_uuid0',
            'adapay_amount': '100000000',
            'adapay_total_amount_sent': '0',
            'adapay_total_amount_left': '0',
            'adapay_expiration_date': '2022-05-03T16:29:11.000Z',
            'adapay_update_time': '2022-05-03T16:33:55.000Z',
            'adapay_last_updated': '2022-05-03T16:33:55.000Z',
            'adapay_expiration_minutes': '15',
            'adapay_status': 'new',
            'adapay_address': 'addr_test1fake',
        }

        # Should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(post_form_values, 'adapay')

        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 100,
            'acquirer_id': self.adapay.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_ada_1',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # Do feedback
        tx.form_feedback(post_form_values, 'adapay')
        # Check main data after feedback
        self.assertEqual(tx.state, 'pending')
        self.assertEqual(tx.adapay_status, 'new')
        self.assertEqual(tx.adapay_address, 'addr_test1fake')
        self.assertEqual(tx.adapay_uuid, 'test_uuid0')
        self.assertEqual(tx.adapay_amount, 100.0)

        # Update via webhook -> adapay confirmed status
        adapay_payment_data = adapay_api_get_by_uuid_response.copy()
        adapay_payment_data['status'] = 'confirmed'
        adapay_webhook_data = {'event': 'paymentRequestUpdate', 'data': adapay_payment_data}
        tx._handle_adapay_webhook(adapay_webhook_data)
        # Check done status
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_adapay.models.payment')
    def test_adapay_payment_page(self):
        self.assertEqual(self.adapay.state, 'test')

        # Create TX with main data
        tx = self.env['payment.transaction'].create({
            'amount': 100,
            'acquirer_id': self.adapay.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_ada_1',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id,
            'state': 'pending',
            'adapay_status': 'new',
            'adapay_address': 'addr_test1fake',
            'adapay_uuid': 'test_uuid0',
            'adapay_amount': 100.0,
            'adapay_expiration_minutes': 1,
            })

        # Update via webhook -> adapay pending status
        adapay_payment_data = adapay_api_get_by_uuid_response.copy()
        adapay_payment_data['status'] = 'pending'
        adapay_payment_data['confirmedAmount'] = 50000000
        adapay_webhook_data = {'event': 'paymentRequestUpdate', 'data': adapay_payment_data}
        tx._handle_adapay_webhook(adapay_webhook_data)

        payment_page = tx._get_processing_info()

        # Check pending status and payment page
        self.assertGreater(payment_page['adapay_expiration_seconds'], 0)
        self.assertGreater(payment_page['last_event'], tx.create_date)
        self.assertIn("50.0 ADA", payment_page['message_to_display'].decode())  # Confirmed Values
        self.assertEqual(tx.adapay_status, 'pending')
        last_event = payment_page['last_event']

        # Update via webhook -> adapay payment-sent status
        adapay_payment_data = adapay_api_get_by_uuid_response.copy()
        adapay_payment_data['status'] = 'payment-sent'
        adapay_payment_data['confirmedAmount'] = 100000000
        adapay_webhook_data = {'event': 'paymentRequestUpdate', 'data': adapay_payment_data}
        tx._handle_adapay_webhook(adapay_webhook_data)

        payment_page = tx._get_processing_info()

        # Check pending status and payment page
        self.assertEqual(payment_page['adapay_expiration_seconds'], 0)  # No more timer
        self.assertGreater(payment_page['last_event'], last_event)
        self.assertIn("100.0 ADA", payment_page['message_to_display'].decode())  # Confirmed Values
        self.assertEqual(tx.adapay_status, 'payment-sent')
