import json
from enum import Enum
from datetime import date
from urllib.parse import urljoin 
from requests import Session

RATE = 1000000

def lovelace_to_ada(amount):
    return float(amount)/RATE


def ada_to_lovelace(amount):
    return int(float(amount)*RATE)


class AdaPayUrl(Enum):
    # Urls
    url_production = "https://api.adapay.finance"
    url_sandbox = "https://api-sandbox.adapay.finance"
    # Paths
    create_payment_request = "/payment-request"
    get_payment_request = "/payment-request/find"
    get_payment_request_by_uuid = "/payment-request/get-by-uuid"
    create_withdrawal = "/withdrawal/create"
    get_withdrawal = "/withdrawal/find"


class AdaPayMerchantApi:
    """AdaPay API implementation.
    For API details visit https://docs.adapay.finance/docs
    """
    _session = Session()

    def __init__(self, base_url, api_key:str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
            }
        # Set hook to raise when the HTTP code is an error. See https://docs.adapay.finance/docs/errors
        raise_for_status_hook = lambda response, **_: response.raise_for_status()
        self._session.hooks['response'] = raise_for_status_hook

    def _get_url(self, url_path):
        return urljoin(self.base_url, url_path)

    def _filter_optional_values(self, data: dict) -> dict:
        """Filter `None` values from data, let AdaPay API handle default values.

        Args:
            data (dict): Data to be sended through the API.

        Returns:
            dict: Data without the optional data that were not set.
        """
        return {key: value for key, value in data.items() if value is not None}

    def create_payment(self, amount: float, expiration_minutes: int, receipt_email: str, description:str=None, name:str=None, order_id:str=None, return_url:str=None, address_for_refund:str=None) -> dict:
        """Create a new payment request and gets in return a unique identifier

        Args:
            amount (float): The amount for the user to pay, where 1M LOVELACE equal to 1 $ADA
            expiration_minutes (int): The amount of minutes until the payment request is expired
            receipt_email (str): The user's email, to send receipt and payment approvals
            description (str, optional): A description of the payment request. This description is displayed on the payment page and user’s receipt. Defaults to None.
            name (str, optional): The name of the paying user. Defaults to None.
            order_id (str, optional): The order ID in the merchant’s backend. Defaults to None.
            return_url (str, optional): A return url. If provided it will override the default settings. Defaults to None.
            address_for_refund (str, optional): A return address, if provided it will be displayed as the default in the refund field. Defaults to None.

        Returns:
            dict: Api response data. You can find a uuid from which you can get the payment request state

        Raises:
            requests.exceptions.HTTPError: If we made a bad request (a 4XX client error or 5XX server error response).
        """
        data = {
            "amount": ada_to_lovelace(amount), "paymentRequestExpirationTime": expiration_minutes, "receiptEmail": receipt_email,
            "description": description, "name": name, "orderId": order_id, "returnUrl": return_url, "addressForRefund": address_for_refund,
        }
        payment_request_url = self._get_url(AdaPayUrl.create_payment_request.value)
        json_data = self._filter_optional_values(data)
        response = self._session.put(payment_request_url, headers=self.headers, json=json_data)
        return response.json()

    def get_payment(self, uuid:str=None, from_date:date=None, to_date:date=None, page_size:int=None, page_number:int=None) -> dict:
        """Returns payment requests by filters

        Args:
            uuid (str): Unique identifier filter
            from_date (date): From date filter
            to_date (date): To date filter
            page_size (int, optional): Pagination option, define the amount of returned records. Defaults to None.
            page_number (int, optional): Pagination option, define the skip on found records. Defaults to None.

        Returns:
            dict: API response data.

        Raises:
            requests.exceptions.HTTPError: If we made a bad request (a 4XX client error or 5XX server error response).
        """
        data = {"uuid": uuid, "from": str(from_date) if from_date else None, "to": str(to_date) if to_date else None, "pageSize": page_size, "pageNumber": page_number}
        json_data = self._filter_optional_values(data)
        get_payment_url = self._get_url(AdaPayUrl.get_payment_request.value)
        response = self._session.post(get_payment_url, headers=self.headers, json=json_data)
        return response.json()

    def get_payment_by_uuid(self, uuid:str) -> dict:
        """Returns all the data of a payment request by its uuid.

        Args:
            uuid (str): A unique identifier for the payment request.

        Returns:
            dict: API response data.
        """
        data = {"uuid": uuid}
        get_payment_url = self._get_url(AdaPayUrl.get_payment_request_by_uuid.value)
        response = self._session.post(get_payment_url, headers=self.headers, json=data)
        return response.json()

    def create_withdrawal(self, outputs:list, include_fees:bool=None, name:str=None) -> dict:
        """Create withdrawal.

        Args:
            outputs (list): [description]
            include_fees (bool, optional): [description]. Defaults to None.
            name (str, optional): [description]. Defaults to None.

        Returns:
            dict: API response data.

        Raises:
            requests.exceptions.HTTPError: If we made a bad request (a 4XX client error or 5XX server error response).
        """
        data = {"outputs": outputs, "name": name, "includeFees": include_fees}
        json_data = self._filter_optional_values(data)
        create_withdrawal_url = self._get_url(AdaPayUrl.create_withdrawal.value)
        response = self._session.put(create_withdrawal_url, headers=self.headers, json=json_data)
        return response.json()

    def get_withdrawals(self, uuid:str=None, from_date:date=None, to_date:date=None, page_size:int=None, page_number:int=None) -> dict:
        """Returns withdrawal requests by filters

        Args:
            uuid (str): Unique identifier filter
            from_date (date): From date filter
            to_date (date): To date filter
            page_size (int, optional): Pagination option, define the amount of returned records. Defaults to None.
            page_number (int, optional): Pagination option, define the skip on found records. Defaults to None.

        Returns:
            dict: API response data.

        Raises:
            requests.exceptions.HTTPError: If we made a bad request (a 4XX client error or 5XX server error response).
        """
        data = {"uuid": uuid, "from": str(from_date) if from_date else None, "to": str(to_date) if to_date else None, "pageSize": page_size, "pageNumber": page_number}
        json_data = self._filter_optional_values(data)
        get_withdrawal_url = self._get_url(AdaPayUrl.get_withdrawal.value)
        response = self._session.post(get_withdrawal_url, headers=self.headers, json=json_data)
        return response.json()


def get_adapay_api(api_key, sandbox=False):
    """Get an AdaPay API implementation.

    Args:
        api_key (str): The API key is a unique identifier that authenticates requests associated with your account.
        sandbox (bool, optional): Use sandbox or production URL. Defaults to False.

    Returns:
        AdaPayMerchantApi: Implementation instance.
    """
    url = AdaPayUrl.url_sandbox.value if sandbox else AdaPayUrl.url_production.value
    return AdaPayMerchantApi(url, api_key)
