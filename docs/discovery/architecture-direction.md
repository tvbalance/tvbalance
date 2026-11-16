# Architecture direction

- **Standalone Engine + Add-on + thin integration.** The Engine runs anywhere as a Docker image. The Home
  Assistant Add-on packages it (Ingress, host network, `/data`). A thin custom integration talks to the Engine
  API through a published client library. This is the pattern used by Frigate and Music Assistant, and it
  also serves Home Assistant Container/Core users who cannot run Add-ons.
- **Native entities, not state injection.** Entities come from a real integration (unique ids, UI-editable,
  services, restore on restart), never from `POST /api/states`.
- **No obfuscation as protection.** The Pro value is convenience, curated data and maintenance, not hidden code.
  License verification is open; the Pro module is a separate closed package.
- **Adapters are packages with declared capabilities.** Discovered through entry points, tested by a shared
  contract suite, labeled stable/beta/experimental. The UI adapts to what each TV supports.
- **Hard timeouts live in the Engine**, wrapped around every adapter call, so no adapter can freeze the loop.
- **Versioned API** (REST plus WebSocket events) described by OpenAPI; clients and TypeScript types are generated from it.
