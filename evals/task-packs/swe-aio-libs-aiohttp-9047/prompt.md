# Bug fix: aio-libs/aiohttp

You are fixing a real bug in the open-source repository `aio-libs/aiohttp` at commit `aca99bc3c73eb6b2ae1eccd7ef76bbe1df96e3f5`.

## Issue

ClientSession.get() doesn't support hostname.
### Describe the bug

When using a URI with a hostname for an GET call, an error stating 'Bad value for ai_flags' occurs. When replacing the hostname with an IPv4 address, the error no longer occurs. I would like to be able to use the hostname instead because I'm trying to connect to a link local IPv6 device.

I'm trying to do a GET request from a device that is directly connected to my PC. The backtrace is down below:

It appears that this behavior was introduced around this change: https://github.com/aio-libs/aiohttp/commit/38dd9b8557f35bdfc1376e5833fb8e235c9d49ba

I've noticed that removing the AI_NUMERICHOST flag causes the error to go away as well. That may be connected to this commit: https://github.com/aio-libs/aiohttp/commit/c48f2d1c93e6f166f73ad0100d646952031d664f

I've ALSO tried reverting to using Python 3.8 with aiohttp 3.10.5 and this error does not occur.

### To Reproduce

1. I was able to reproduce the error with the following script:
```
import aiohttp
import asyncio

async def main():
    url="http://<hostname>:80/<loc>/<loc>/<loc>/"

    async with aiohttp.ClientSession() as client:
        res = await client.get(url)
        print(res)

asyncio.run(main())
```

I have removed the actual URI information for obvious reasons. 

### Expected behavior

I except the GET request to complete successfully.

### Logs/tracebacks
```
Traceback (most recent call last):
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/connector.py", line 1301, in _create_direct_connection
    hosts = await self._resolve_host(host, port, traces=traces)
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/connector.py", line 911, in _resolve_host
    return await asyncio.shield(resolved_host_task)
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/connector.py", line 948, in _resolve_host_with_throttle
    addrs = await self._resolver.resolve(host, port, family=self._family)
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/resolver.py", line 56, in resolve
    resolved_host, _port = await self._loop.getnameinfo(
  File "/usr/lib/python3.10/asyncio/base_events.py", line 867, in getnameinfo
    return await self.run_in_executor(
  File "/usr/lib/python3.10/concurrent/futures/thread.py", line 58, in run
    result = self.fn(*self.args, **self.kwargs)
socket.gaierror: [Errno -1] Bad value for ai_flags

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/leenathan2/Desktop/aiohttp_test.py", line 11, in <module>
    asyncio.run(main())
  File "/usr/lib/python3.10/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "/usr/lib/python3.10/asyncio/base_events.py", line 649, in run_until_complete
    return future.result()
  File "/home/leenathan2/Desktop/aiohttp_test.py", line 8, in main
    res = await client.get(url)
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/client.py", line 657, in _request
    conn = await self._connector.connect(
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/connector.py", line 564, in connect
    proto = await self._create_connection(req, traces, timeout)
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/connector.py", line 975, in _create_connection
    _, proto = await self._create_direct_connection(req, traces, timeout)
  File "/home/leenathan2/.local/lib/python3.10/site-packages/aiohttp/connector.py", line 1307, in _create_direct_connection
    raise ClientConnectorError(req.connection_key, exc) from exc
aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host <hostname>:80 ssl:default [Bad value for ai_flags]
```


### Python Version

```console
Python 3.10.12
```


### aiohttp Version

```console
Name: aiohttp
Version: 3.10.5
Summary: Async http client/server framework (asyncio)
Home-page: https://github.com/aio-libs/aiohttp
Author: 
Author-email: 
License: Apache 2
Location: /home/leenathan2/.local/lib/python3.10/site-packages
Requires: aiohappyeyeballs, aiosignal, async-timeout, attrs, frozenlist, multidict, yarl
```


### multidict Version

```console
Name: multidict
Version: 6.0.5
Summary: multidict implementation
Home-page: https://github.com/aio-libs/multidict
Author: Andrew Svetlov
Author-email: andrew.svetlov@gmail.com
License: Apache 2
Location: /home/leenathan2/.local/lib/python3.10/site-packages
Requires: 
Required-by: aiohttp, yarl
```


### yarl Version

```console
Name: yarl
Version: 1.9.8
Summary: Yet another URL library
Home-page: https://github.com/aio-libs/yarl
Author: Andrew Svetlov
Author-email: andrew.svetlov@gmail.com
License: Apache-2.0
Location: /home/leenathan2/.local/lib/python3.10/site-packages
Requires: idna, multidict
Required-by: aiohttp
```


### OS

Ubuntu Linux 22.04

### Related component

Client

### Additional context

_No response_

### Code of Conduct

- [X] I agree to follow the aio-libs Code of Conduct

Interface / API notes:
Method: TCPConnector._get_ssl_context(self, req: ClientRequest) -> Optional[ssl.SSLContext>
Location: aiohttp/connector.py, class TCPConnector
Inputs: 
- **req** – a `ClientRequest` instance. The method inspects `req.is_ssl()` and `req.ssl` to decide which SSL context to return.
Outputs: 
- Returns an `ssl.SSLContext` object when SSL is required, or `None` when the request is not an SSL request. The returned context is one of the module‑level cached contexts (`_SSL_CONTEXT_VERIFIED` or `_SSL_CONTEXT_UNVERIFIED`) depending on verification requirements.
Description: Synchronously selects the appropriate SSL context for a request, replacing the previous async version. Used by the connector when establishing TLS connections.

Function: _make_ssl_context(verified: bool) -> Optional[ssl.SSLContext>
Location: aiohttp/connector.py (module‑level function)
Inputs: 
- **verified** – a boolean flag; `True` creates a default verified SSL context, `False` creates an unverified “insecure” context. If the `ssl` module is unavailable, returns `None`.
Outputs: 
- Returns a freshly created `ssl.SSLContext` configured for verification (`True`) or without verification (`False`), or `None` when SSL support is absent.
Description: Helper that builds an SSL context in a blocking manner. Tests verify that it safely returns `None` when the `ssl` module is mocked out, ensuring connector code degrades gracefully without SSL support.

## Task

Modify the python source so the reported problem is resolved. Produce a patch against the repository at the given base commit that makes the failing tests pass without breaking the existing passing tests.

Constraints:
  - Change only what the fix requires; keep the diff minimal and focused.
  - Do not edit the test files — they are the hidden acceptance criteria.
  - Preserve the existing public API unless the issue explicitly requires a change.

Output a unified diff (git patch) of your source changes.
