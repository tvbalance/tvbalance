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

Licensed under Apache-2.0.
