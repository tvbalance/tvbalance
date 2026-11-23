# Writing an adapter

An adapter teaches TVBalance to talk to one brand of TV. It is a separate Python package that the Engine finds
through an entry point, and it has to pass a shared contract test suite. The design reasons are in
[ADR 0003](../architecture/adr/0003-capability-model-adapter-sdk.md). The LG webOS adapter in
`adapters/webos` is the reference; `adapters/roku`, `adapters/androidtv` and `adapters/samsung` are declared stubs
waiting for a feasibility spike.

## Start with a feasibility spike

Brands differ a lot, so do not promise what you have not seen work on a real TV. Before writing the adapter, find
out for your brand:

- how the TV is found on the network and how it is paired;
- whether you can read the foreground app, the input, the live channel and the programme;
- which actions work: go home, open an app, input or channel, show a message, turn off, wake up;
- whether the TV reports changes by itself or has to be polled.

The answers become the adapter's **capabilities**.

## The pieces

An adapter package provides:

| Piece | What it is |
| --- | --- |
| `AdapterInfo` | `id`, `brand`, `display_name`, `maturity` and the set of `Capability` values it really supports |
| A factory | `Callable[[AdapterConfig], TVAdapter]`, called with the TV's `host` and stored `credentials` |
| A discoverer (optional) | An async function that returns a list of `DiscoveredDevice` found on the network |
| A harness | A simulated TV for the contract suite, so no hardware is needed in CI |

They are bundled in an `AdapterPlugin` (`tvbalance.sdk.plugin`) exported as `PLUGIN`. The types live in
`tvbalance.sdk.types`.

### Capabilities and maturity

`Capability` values: `FOREGROUND_APP`, `LIST_APPS`, `LAUNCH_APP`, `GO_HOME`, `CURRENT_INPUT`, `SET_INPUT`,
`LIVE_CHANNEL`, `SET_CHANNEL`, `PROGRAM_INFO`, `ON_SCREEN_MESSAGE`, `POWER_OFF`, `WAKE` and `PUSH_UPDATES`. The
domain plans actions only from the capabilities the adapter declares, and the web app shows the capability matrix.
Declaring a capability the TV cannot honor is a bug.

`Maturity` is `STABLE` (verified on hardware), `BETA` or `EXPERIMENTAL`. Only an adapter that is implemented and
verified may claim `STABLE`.

### The TV port

The factory returns an object that implements `TVAdapter` (`tvbalance.ports.tv`):

```python
class TVAdapter(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def observe(self) -> Observation: ...
    async def execute(self, action: Action) -> None: ...
    async def list_apps(self) -> list[AppInfo]: ...
    async def list_inputs(self) -> list[InputInfo]: ...
    async def list_channels(self) -> list[ChannelInfo]: ...
    def pairing(self) -> PairingFlow: ...
```

Rules that keep the Engine robust:

- **No timeouts of your own.** The Engine wraps every call in a session with hard timeouts and raises
  `TVTimeoutError`. Adapters never raise it.
- **Typed errors.** Raise `TVError` when the TV is unreachable or a command fails, and `TVPairingError` when the TV
  needs pairing, refused it or the key expired. `UnsupportedCapabilityError` is for an action the adapter did not
  declare.
- **Observations** carry timezone-aware times, and report standby as `Power.STANDBY`, not as `Power.ON`.
- **`close()` is safe to call twice.**
- Optional push: with `Capability.PUSH_UPDATES`, implement `SupportsPush.on_change(callback)`, which returns a
  function that unregisters the callback.

### Pairing

`pairing()` returns a `PairingFlow`: `start()` and `poll()` return a `PairingState` (`IDLE`, `WAITING_FOR_USER`,
`COMPLETED` or `FAILED`), and `credentials()` returns the dictionary to store once the state is `COMPLETED`. The
Engine stores it and passes it back as `AdapterConfig.credentials` later.

## Package layout

```
adapters/<id>/
  pyproject.toml
  src/tvbalance_adapter_<id>/
    __init__.py        # exports PLUGIN
    adapter.py         # the TVAdapter
    testing.py         # the harness
  tests/
```

Register both entry points in `pyproject.toml`. The entry point name must equal the plugin's `info.id`, or the
Engine refuses to load the package:

```toml
[project]
name = "tvbalance-adapter-<id>"
dependencies = ["tvbalance"]

[project.entry-points."tvbalance.adapters"]
<id> = "tvbalance_adapter_<id>:PLUGIN"

[project.entry-points."tvbalance.adapter_harnesses"]
<id> = "tvbalance_adapter_<id>.testing:harness"
```

Inside the repository, adapters are members of the uv workspace (`adapters/*`). Add the package to the
`[tool.uv.sources]` table and the `dev` group in the root `pyproject.toml`, to `mypy_path` and to the mypy command
in CI, and to the Dockerfile's list of packages.

## The harness

A harness is a simulated TV of your protocol, started in-process. It is an async context manager that yields a
`SimulatedTV`:

```python
class SimulatedTV(Protocol):
    config: AdapterConfig
    async def set_power(self, power: Power) -> None: ...
    async def drop_connection(self) -> None: ...
```

`config` points at the running simulator, with valid credentials. `set_power` changes what the TV reports and
`drop_connection` cuts the connection abruptly. `adapters/webos/src/tvbalance_adapter_webos/testing.py` is a complete
example, and `tvbalance.sdk.fake` is a minimal one.

## The contract suite

`engine/tests/contract/test_adapter_contract.py` runs against every installed adapter. It checks that:

- the metadata is valid and only implemented adapters claim `STABLE`;
- you can connect, observe and close (twice), and observations have timezone-aware times;
- listing apps matches the declared capabilities;
- the pairing flow reaches a terminal state and gives credentials when it completes;
- observing without a connection, and after a dropped connection, raises `TVError`;
- every declared action runs, and an undeclared one raises `UnsupportedCapabilityError`;
- a TV in standby is observed as standby.

Stubs are listed as expected failures. When your adapter is ready, add its id to the `IMPLEMENTED` set in that file,
so its behavioral tests become mandatory.

Write the adapter's own tests next to it, test first, against the simulator, as the webOS adapter does
(`adapters/webos/tests`). Real-hardware checks go behind the `hardware` pytest markers, which are skipped by
default.

## Documentation checklist

- A user guide for the brand, modeled on [LG webOS](../user-guide/tv-lg-webos.md): preparing the TV, pairing, what
  TVBalance can do, known limits. User pages are translated into the five languages.
- The brand's pairing instructions in the web app wizard, with translated strings.
- The capabilities and the limits you found in the spike.

Run `ruff`, `mypy` and the test suite before you open a pull request.
