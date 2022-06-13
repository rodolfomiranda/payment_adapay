# ADA-Pay payment acquirer for Odoo

<p align="center">
    <img 
        width="240" 
        height="48" 
        src="https://adapay.finance/images/pay-with-ada.svg" alt="adapay" 
    />
</p>

An implementation of the [Odoo Payment Acquirer](https://www.odoo.com/documentation/user/14.0/general/payment_acquirers/payment_acquirers.html) module for ADA-Pay payments. 
Configure you ADA-Pay account [here](https://docs.adapay.finance/docs/introduction/getting-started)


## Operation

The ADA-Pay acquirer will convert the actual amount in the specific currency to an ADA amount (using CoinMarketCap API) and will create the payment-request using the ADA-Pay API, then will follow the payment acquirers flow.

## Pre-requisites

* An ADA-Pay API Key from your account [see documentation](https://docs.adapay.finance/docs/introduction/integration) or [getting started](https://docs.adapay.finance/docs/introduction/getting-started)
* Register for CoinMarketCap to obtain the API Key from your account. You can read how in [authentication documentation](https://coinmarketcap.com/api/documentation/v1/#section/Authentication)
* Set the webhook url from your odoo in your ADA-Pay `Dashboard -> Integrations tools -> Payment Settings` section, to get live events in your Odoo. The webhook url is `https://odoo-base-url/payment/adapay/payment-events`.

## Configuration

Once the module is installed you can run the server as normal and follow [these](https://www.odoo.com/documentation/user/14.0/general/payment_acquirers/payment_acquirers.html#configuration) instructions for basic configuring AdaPay on your e-commerce site.
Then you need to set several fields before activating the acquirer. This fields are required:

* `Credentials` section
    * `AdaPay APIKEY`: set your ADA-Pay API key.
    * `Payment Request expiration (minutes)`: it's recommended to set the default value. You can check the available minutes span in your ADA-Pay account, in `Dashboard -> Settings -> Payment expiration time`.

* `Configuration` section
    * `Conversion provider`: currently only CoinMarket provider is supported.
    * `Api-Key`: your CoinMarket API Key.

### WebHook

You can enable the using of webhook in the `Credentials` section.
If the field `Use WebHook` is activated, you will receive live notifications from ADA-Pay in the `https://odoo-base-url/payment/adapay/payment-events` endpoint, every time the payment change its status.
Otherwise the module will use the ADA-Pay API to update the payment status every time the client needs (in payment processing page) and there is also a scheduled action to update often the payment using the ADA-Pay API in background.

* Advanced: You can configure the frecuency, disable the action, etc in `Scheduled Actions` menu, looking for the `Update payments status from AdaPay ` item.


---
This module was tested in Odoo 14