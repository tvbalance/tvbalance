# tvbalance-client

Async Python client for the [TVBalance](https://github.com/tvbalance/tvbalance) Engine API. It is the library behind
the TVBalance Home Assistant integration, and it can be used on its own.

```python
import aiohttp
from tvbalance_client import TVBalanceClient

async with aiohttp.ClientSession() as session:
    client = TVBalanceClient("http://engine.local:8765", "tvb_...", session=session)
    for tv in await client.tvs():
        print(tv.name, tv.status)
```

Create the API token in the Engine web UI under **Settings → API tokens**.

## HTTPS with the Engine's local CA

The Engine can serve HTTPS with a certificate from its own local CA. Fetch the CA once, let the user
confirm its fingerprint, then pin it:

```python
from tvbalance_client import ca_fingerprint, fetch_ca_certificate, ssl_context_for

pem = await fetch_ca_certificate("https://engine.local:8766")
print(ca_fingerprint(pem))  # compare with Settings → Secure connection
client = TVBalanceClient("https://engine.local:8766", "tvb_...", ssl_context=ssl_context_for(pem))
```

A certificate that does not match raises `CertificateError`.

Licensed under Apache-2.0.
