from .conversion_providers.coinmarket import get_coinmarket

COINMARKET_PROVIDER = "coinmarket"
providers = {
    COINMARKET_PROVIDER: get_coinmarket,
}


def get_conversion_provider(provider, api_key=None, sandbox=False, **kwargs):
    return providers[provider](api_key=api_key, sandbox=sandbox, **kwargs)
