# -*- coding: utf-8 -*-
import json
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentProcessing
_logger = logging.getLogger(__name__)


class AdapayController(PaymentProcessing):
    _webhook_url = '/payment/adapay/payment-events'
    _accept_url = '/payment/adapay/accept'

    @http.route([
        '/payment/adapay/accept'
    ], type='http', auth='public', csrf=False)
    def adapay_form_feedback(self, **post):
        _logger.info('adapay: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        rr = request.env['payment.transaction'].sudo().form_feedback(post, 'adapay')
        return werkzeug.utils.redirect("/payment/adapay/validate")

    @http.route(['/payment/adapay/validate'], type="http", auth="public", website=True, sitemap=False)
    def payment_adapay_validate(self, **kwargs):
        # When the customer is redirect to this website page,
        # we retrieve the payment transaction list from his session
        tx_ids_list = self.get_payment_transaction_ids()
        payment_transaction_ids = request.env['payment.transaction'].sudo().browse(tx_ids_list).exists()
        render_ctx = {
            'payment_tx_ids': payment_transaction_ids.ids,
        }
        return request.render("payment.payment_process_page", render_ctx)

    @http.route('/payment/adapay/payment-events', type='json', auth='public', csrf=False)
    def adapay_webhook(self, **kwargs):
        """Handle ADA-Pay live events notifications"""
        data = json.loads(request.httprequest.data)
        if request.env.ref("payment_adapay.payment_acquirer_adapay").adapay_use_webhook:
            request.env['payment.transaction'].sudo()._handle_adapay_webhook(data)
            return 'OK'
