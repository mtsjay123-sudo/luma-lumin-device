# Grocery shopping integration

Luma's `GroceryService` creates a real Instacart shopping-list page from the
reviewed product names, quantities and units. It can also retrieve nearby retailer
organizations using a postal code. The integration has been checked with mock
HTTP responses; no live lists, carts, payments or orders were created in tests.

The shopping-list API returns `products_link_url`. It does **not** return a cart
ID, order ID, matched product details, prices, inventory, or a selected retailer.
The connector preserves that URL as its actual provider reference. Its
`local_receipt_id` is an application fingerprint, never a claimed Instacart ID.
Item details in the Luma receipt are the requested list, awaiting merchant
matching and review. [Official list API](https://docs.instacart.com/developer_platform_api/api/products/create_shopping_list_page)

Configure private credentials, then restart Luma:

```dotenv
INSTACART_API_KEY=
INSTACART_ENVIRONMENT=production
```

Obtain the appropriate key through Instacart Developer Platform. Development
keys use `INSTACART_ENVIRONMENT=development`; these call the official development
host and are labeled development in returned results. Production credentials
use `https://connect.instacart.com`. Never put API keys in the browser or commit
them to Git. [API hosts and authentication](https://docs.instacart.com/developer_platform_api/api/overview)

The runtime interface is:

```python
groceries = GroceryService(env=providers.env, request=providers.request)
groceries.nearby({"postal_code": "27514", "country_code": "US"})
groceries.create_list({
    "title": "Breakfast groceries",
    "items": [
        {"name": "eggs", "quantity": 12, "unit": "each"},
        {"name": "whole milk", "quantity": 1, "unit": "gallon"},
    ],
})
```

`validate_list(args)` can validate and normalize the list for a local preview
without credentials or network access. Structured input requires explicit item
names, numeric quantities and supported units; quantities are not inferred from
chat text by this module. The `UNITS` constant provides the supported UI choices.
The request uses the current `line_item_measurements` structure rather than
deprecated top-level item quantity fields. Lists contain 1–50 items and request
seven days of link validity. The reported expiry is calculated from that
requested lifetime, because the API does not return an expiry timestamp.

Identical lists reuse their returned URL while the process is running, as
Instacart recommends. Luma's runtime should also retain its encrypted action
result and reuse the saved URL across restarts. Concurrent matching requests are
coalesced. A timeout or malformed success never triggers an automatic retry;
the connector remembers uncertainty for that list until restart. The runtime's
durable action record remains the source for reviewing uncertain requests.

For Food Lion, the nearby-retailer response can verify whether Instacart lists
Food Lion for the entered postal code. A retailer key describes an organization,
not a confirmed physical store, stock count or delivery slot. The shopping-list
endpoint has no documented retailer-selection field, so Luma does not claim to
force a Food Lion cart. [Nearby retailer API](https://docs.instacart.com/developer_platform_api/api/retailers/get_nearby_retailers/)

Open the generated list, choose an available retailer such as Food Lion, review
the matched products, add them to the cart, and finish checkout. The merchant
handles sign-in, delivery address, substitutions, taxes, service fees, delivery
windows and saved payment methods. Raw card numbers, CVCs and passwords are
rejected by the Luma adapter. The app never labels search snippets as live price
quotes or claims the cheapest final basket. [Instacart shopping-list workflow](https://docs.instacart.com/developer_platform_api/guide/concepts/shopping_list/)

Food Lion documents home delivery powered by Instacart and its own To Go
website/app checkout. Current serviceability must be checked for the user's
address. The direct store entry is [Food Lion](https://foodlion.com/); the
connector does not invent a product-search URL or scrape private checkout
endpoints. [Food Lion's delivery description](https://newsroom.foodlion.com/news-releases/news-release-details/commitment-convenience-food-lion-expands-home-delivery-three)

To place grocery orders directly from Luma in a later release, the remaining
requirement is supported transactional access and an approved integration with
the retailer/fulfillment provider. Instacart Connect fulfillment and order APIs
are for retailer partners; an ordinary Developer Platform list key does not
grant those operations. That implementation would need authenticated customer
linking, exact store/SKU selection, a current full-price quote, fulfillment-slot
selection, tokenized payment handled by the payment provider, explicit final
approval, an actual order receipt, and cancellation/status support. No generic
HTTP automation can substitute for that access. [Instacart Connect scope](https://docs.instacart.com/connect)

Run deterministic adapter checks:

```sh
.venv/bin/python -m unittest discover -s tests -p test_commerce.py -v
```
