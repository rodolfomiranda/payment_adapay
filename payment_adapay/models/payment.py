# coding: utf-8
import logging
import json

from werkzeug import urls
from string import Template

import logging

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare
from ..connectors.currency_conversion import COINMARKET_PROVIDER
from ..connectors.conversion_providers.coinmarket import CoinMarket
from ..connectors.currency_conversion import get_conversion_provider
from .utils import generate_b64_qr_image
from ..connectors.adapay import (
    get_adapay_api,
    ada_to_lovelace,
    lovelace_to_ada,
)
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

ADA = "ADA"
ADA_DECIMAL = 2


class AcquirerAdapay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('adapay', 'Adapay')
    ], ondelete={'adapay': 'set default'})
    adapay_api_key = fields.Char("AdaPay APIKEY")
    adapay_expiration_minutes = fields.Integer("Payment request expiration (minutes)", default=15)
    adapay_use_webhook = fields.Boolean("Use WebHook",
        default=False,
        help="Disable update via webhook and do it via cron.")
    conversion_provider = fields.Selection([
            (COINMARKET_PROVIDER, 'CoinMarket')
        ],
        default=COINMARKET_PROVIDER, required=True)
    conversion_api_key = fields.Char("Api-Key")
    conversion_test_mode = fields.Boolean("Test Mode", default=False)
    adapay_status_msg_new = fields.Html("AdaPay New", translate=True, help="Payment request was created.")
    adapay_status_msg_pending = fields.Html("AdaPay Pending", translate=True, help="Some transactions started but transactions are still left.")
    adapay_status_msg_payment_sent = fields.Html("AdaPay payment sent", translate=True, help="Transactions amount are completed.")
    adapay_status_msg_confirmed = fields.Html("AdaPay Confirmed", translate=True, help="Payment confirmed.")
    adapay_status_msg_expired = fields.Html("Adapay expired", translate=True, help="There were no transactions in the time period.")

    def _adapay_get_msg_by_status(self, status):
        return getattr(self, f"adapay_status_msg_{status.replace('-', '_')}")

    def _get_conversion_provider(self, data):
        return get_conversion_provider(**data)

    def _get_adapay_api_connector(self):
        sandbox = self.state == "test"
        return get_adapay_api(self.adapay_api_key, sandbox)

    def adapay_form_generate_values(self, values):
        # Perform currency amount conversion
        try:
            currency_converter = self._get_conversion_provider(
                {"provider": self.conversion_provider, "api_key": self.conversion_api_key, "sandbox": self.conversion_test_mode })
            resp = currency_converter.price_conversion(
                amount=values["amount"],
                amount_currency=values["currency"].name,
                convert_currency=ADA,
            )
            adapay_amount = {
                "ada_amount": float(format(resp['price'], f'.{ADA_DECIMAL}f')),
                "last_updated": resp["last_updated"],
                "ada_currency": ADA,
                "provider": self.conversion_provider,
            }
            _logger.info(f"{self.conversion_provider}: {values['amount']} {values['currency'].name} -> {resp['price']} {ADA}. Last updated: {resp['last_updated']}")
            values.update(adapay_amount)
        except Exception as err:
            _logger.error("Conversion error: %s", err)
            raise ValidationError(_("We cannot get the ADA currency rate. Please try again."))
        # Perform adapay payment requests
        try:
            sandbox = self.state == "test"
            adapay_conn = get_adapay_api(self.adapay_api_key, sandbox)
            payment_uuid = adapay_conn.create_payment(
                amount=values["ada_amount"],
                expiration_minutes=self.adapay_expiration_minutes,
                receipt_email=values["partner_email"],
                description=values["reference"],
                name=values["reference"],
                order_id=values["reference"],
            )
            payment_data = adapay_conn.get_payment_by_uuid(payment_uuid["uuid"])
            payment_data = {f"adapay_{key}":value for key, value in payment_data.items()}
            values.update(payment_data)
            values["adapay_expiration_minutes"] = self.adapay_expiration_minutes
        except Exception:
            raise ValidationError(_("We cannot create the AdaPay payment request. Please try again."))
        return values

    def adapay_get_form_action_url(self):
        self.ensure_one()
        return '/payment/adapay/accept'


class TransactionAdapay(models.Model):
    _inherit = 'payment.transaction'

    adapay_uuid = fields.Char("Payment UUID")
    adapay_amount = fields.Float("Amount in ADA")
    adapay_total_amount_sent = fields.Float("Amount sent")
    adapay_total_amount_left = fields.Float("Amount left")
    adapay_expiration_minutes = fields.Integer("Expiration minutes")
    adapay_expiration_date = fields.Char("Expiration date")
    adapay_update_time = fields.Char("Update time")
    adapay_last_updated = fields.Char("Last updated")
    adapay_status = fields.Char("Payment status", default="new")
    adapay_substatus = fields.Char("Payment sub-status", default="")
    adapay_address = fields.Char("Payment address")
    adapay_transaction_history = fields.Text("Transaction history", default='{}')
    adapay_last_event = fields.Datetime("Last event")

    @api.model
    def _adapay_form_get_tx_from_data(self, data, field="reference"):
        reference = data.get("reference")
        tx = self.search([(field, '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('received data for reference %s') % (reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx

    def _adapay_form_validate(self, data):
        _logger.info('Validated adapay payment for tx %s: set as pending' % (self.reference))
        data["adapay_amount"] = lovelace_to_ada(data["adapay_amount"])
        # Update tx `adapay_` fields
        adapay_data = {key: value for key, value in data.items() if key.startswith("adapay_")}
        self.write(adapay_data)
        self.adapay_last_event = datetime.now()
        try:
            for sale in self.sale_order_ids:
                # TODO: Add 1 ADA -> currency value 
                CONVERSION_MSG = Template(_("""Currency converted via $provider: $amount $currency -> 
                                            $ada_amount ADA. Last updated: $last_updated"""))
                sale.message_post(body=CONVERSION_MSG.safe_substitute(data))
                PAYMENT_CREATED_MSG = Template(_("""AdaPay payment request created:<br>
                Payment reference: $reference
                <ul>
                <li>uuid: $adapay_uuid</li>
                <li>amount: $adapay_amount ADA</li>
                <li>expiration: $adapay_expiration_date</li>
                <li>address: $adapay_address</li>
                </ul>
                """))
                sale.message_post(body=PAYMENT_CREATED_MSG.safe_substitute(adapay_data, reference=self.reference))
        except Exception as err:
            _logger.warning("Unable to set the sale order messages %s", err)
        self._set_transaction_pending()
        return True

    def _process_payment_data(self, payment_data):
        """Update transaction from ADA-Pay API data values."""
        update_date = payment_data["updateTime"]
        if update_date != self.adapay_last_updated:  # Update if it's neccessary
            _logger.info("Received payment update for %s", self.reference)
            self._adapay_webhook_feedback(payment_data)
        for transaction in payment_data["transactions"]:
            self._adapay_webhook_transaction_feedback(transaction)

    def _get_processing_info(self):
        qr_encoded = generate_b64_qr_image(self.adapay_address)
        res = super()._get_processing_info()
        if self.acquirer_id.provider == 'adapay':
            # Update status
            if not self.acquirer_id.adapay_use_webhook:
                # We need to update status every time this method is called.
                try: 
                    _logger.info("Going to look for the update for %s", self.reference)
                    conn = self.acquirer_id._get_adapay_api_connector()
                    payment_data = conn.get_payment_by_uuid(self.adapay_uuid)
                    self._process_payment_data(payment_data)
                except Exception as err:
                    _logger.warning("Could not update payment status: %s", err)
            # Render AdaPay payment pages
            exp_time = 0
            if self.adapay_status in ['new', 'pending']:  # Timer, set expiration from backend
                now = datetime.now()
                expiration = self.create_date + timedelta(minutes=self.adapay_expiration_minutes)
                if now > expiration:
                    self.adapay_status = "expired"
                else: 
                    exp_time = (expiration - now).seconds
            transaction_adapay_data = {field:getattr(self, field) for field in self._fields.keys() if field.startswith("adapay")}
            transaction_adapay_data['qr_code'] = f"data:image/png;base64,{qr_encoded}"
            transaction_adapay_data['adapay_transaction_history'] = list(json.loads(self.adapay_transaction_history).values())
            transaction_adapay_data['title'] = self.acquirer_id._adapay_get_msg_by_status(self.adapay_status)
            # Terms
            transaction_adapay_data["page_terms"] = {
                "address": _("Address"),
                "confirmed": _("Total amount confirmed"),
                "left": _("Amount left to confirm"),
                "history": _("Transactions history"),
                "confirmations":_("of 15 confirmations"),
                "pending": _("pending"),
                "confirmed": _("confirmed")
            }
            payment_frame = self.env.ref("payment_adapay.payment_adapay_page")._render(transaction_adapay_data, engine="ir.qweb")
            adapay_info = {
                "message_to_display": payment_frame,
                "adapay_expiration_seconds": exp_time,
                "last_event": self.adapay_last_event,  # Must update the UI
            }
            if self.adapay_status != "confirmed":  # Prevent confirmation page if payment was not started
                adapay_info["return_url"] = ""
            res.update(adapay_info)
        return res

    def _handle_adapay_webhook(self, data):
        """Update transactions from ADA-Pay live events."""
        event_type = data.get("event")
        data = data.get("data", {})
        if event_type == 'paymentRequestUpdate':
            _logger.info("Webhook: Received a paymentRequestUpdate for %s", data["orderId"])
            tx_reference = data.get("orderId")
            data_tx = {'reference': tx_reference}
            try:
                odoo_tx = self.env['payment.transaction']._adapay_form_get_tx_from_data(data_tx)
            except ValidationError as e:
                _logger.error('Received notification for tx %s: %s', tx_reference, e)
                return False
            odoo_tx._adapay_webhook_feedback(data)
        elif event_type == 'paymentRequestTransactionsUpdate':
            _logger.info("Webhook: Received a paymentRequestUpdate for uuid %s and transaction %s", data["paymentRequestUuid"], data["hash"])
            tx_reference = data.get("paymentRequestUuid")
            data_tx = {'reference': tx_reference}
            try:
                odoo_tx = self.env['payment.transaction']._adapay_form_get_tx_from_data(data_tx, field="adapay_uuid")
            except ValidationError as e:
                _logger.error('Received notification for tx %s: %s', tx_reference, e)
                return False
            odoo_tx._adapay_webhook_transaction_feedback(data)
        return True

    def _adapay_webhook_feedback(self, data):
        status = data["status"]
        # Update data
        self.write({
            "adapay_total_amount_sent": lovelace_to_ada(data["confirmedAmount"]),
            "adapay_total_amount_left": lovelace_to_ada(data["pendingAmount"]),
            "adapay_last_updated": data["updateTime"],
            "adapay_status": status,
            "adapay_substatus": data["subStatus"],
        })
        self.adapay_last_event = datetime.now()
        PAYMENT_UPDATE_TRANSACTIONS_MSG = Template(_("""
            <ul>
                <li>hash: $hash</li>
                <li>amount: $amount</li>
                <li>status: $status</li>
                <li>confirmed: $lastMonitoredDepth / 15</li>
            </ul><br>
            """))
        PAYMENT_UPDATE_MSG = Template(_("""Adapay payment update:<br>
            Payment reference: $orderId<br>
            uuid: $uuid
            <ul>
            <li>status: $status</li>
            <li>substatus: $subStatus</li>
            <li>amount: $amount</li>
            <li>address: $address</li>
            <li>pending: $pendingAmount</li>
            <li>updated: $updateTime</li>
            <li>expiration: $expirationDate</li>
            $transactions_msg
            </ul>
            """))
        try:
            # Set messages in sale orders
            for sale in self.sale_order_ids:
                transactions_history = data.get("transactions")
                transactions_msg = ""
                if transactions_history:
                    transactions_msg = "<li>transactions</li>"
                    for transaction_data in transactions_history:
                        transactions_msg = f"{transactions_msg}{PAYMENT_UPDATE_TRANSACTIONS_MSG.safe_substitute(transaction_data)}"
                sale.message_post(body=PAYMENT_UPDATE_MSG.safe_substitute(data, transactions_msg=transactions_msg))
        except Exception as err:
            _logger.warning("Unable to set the sale order messages %s", err)
        if status == "confirmed":
            if self.state != "done":
                self._set_transaction_done()
        elif status in ["new", "payment-sent", "pending"]:
            if self.state != "pending":
                self._set_transaction_pending()
        else:
            if self.state != "cancel":
                self.state = "draft"  # Reset the payment flow to be canceled.
                self._set_transaction_cancel()
        return True

    def _adapay_webhook_transaction_feedback(self, data):
        try:
            # Load json structure from string field
            transaction_history = json.loads(self.adapay_transaction_history)
        except json.decoder.JSONDecodeError:
            transaction_history = {}
        transaction_hash = data["hash"]
        if transaction_hash not in transaction_history or \
                data["updateTime"] != transaction_history[transaction_hash]["updateTime"]:
            self.adapay_last_event = datetime.now()
            data["amount"] = lovelace_to_ada(data["amount"])
            transaction_history[transaction_hash] = data
            self.adapay_transaction_history = json.dumps(transaction_history)
            # Update data
            TRANSACTION_UPDATE_MSG = Template(_("""Transaction update:<br>
                <ul>
                    <li>uuid: $paymentRequestUuid</li>
                    <li>hash: $hash</li>
                    <li>amount: $amount</li>
                    <li>status: $status</li>
                    <li>confirmed: $lastMonitoredDepth / 15</li>
                    <li>updated: $updateTime</li>
                </ul>
                """))
            try:
                for sale in self.sale_order_ids:
                    sale.message_post(body=TRANSACTION_UPDATE_MSG.safe_substitute(data))
            except Exception as err:
                _logger.warning("Unable to set the sale order messages %s", err)
        return True

    def _adapay_update_payment_schedule(self):
        """Get all payment in ADA-PAy API and update transactions."""
        _logger.info("Starting AdaPay payments synchronization")
        adapay_acquirer = self.env.ref("payment_adapay.payment_acquirer_adapay")
        if not adapay_acquirer.adapay_use_webhook:
            adapay_conn = adapay_acquirer._get_adapay_api_connector()
            payments_data = adapay_conn.get_payment()  #TODO: Get the last payments
            for payment in payments_data["data"]:
                transaction = self.search([("adapay_uuid", "=", payment["uuid"])])
                if transaction and transaction.state != 'done':  # Don't process finished payments
                    _logger.info("Processing payment synchronization update for %s", transaction.reference)
                    transaction._process_payment_data(payment)
