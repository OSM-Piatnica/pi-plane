<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Copilot connector

Syncs the work items of a Pi-Plane workspace to Microsoft 365 Copilot (a synced Copilot connector in Microsoft Graph). It runs as the `copilot-connector` service of the stack; how to turn it on and who sees what: [docs/copilot-connector.md](../../docs/copilot-connector.md).

| File | |
| --- | --- |
| `scheduler.py` | The service: sets up Graph when needed, then syncs every `COPILOT_SYNC_INTERVAL_MINUTES` |
| `sync_service.py` | One sync run: who may see each work item (ACL), sending, removing deleted work items |
| `graph_connection.py` | Creates or updates the connection and its schema in Microsoft Graph |
| `plane_client.py` | Reads Plane through the public API with a bot token |
| `graph_auth.py`, `graph_users.py` | Microsoft Graph sign-in (client credentials) and email → Entra ID object id |
| `html_text.py` | Descriptions and comments from HTML to plain text |
| `plane_graph_diag.py` | Diagnostics: what Graph holds for given work items and who may see them |
| `plane_mcp_server.py` | MCP server answering live from Plane (not part of the stack yet) |
| `config.py` | Settings from environment variables |

## Running it outside the stack

```
cp .env.example .env              # fill it in; .env holds secrets and is ignored by git
pip install -r requirements.txt   # requirements-mcp.txt for the MCP server
python graph_connection.py        # once: connection and schema
python sync_service.py            # one run; --full sends everything, --allow-mass-delete allows a large deletion
```

Outside the stack the API is called at `PLANE_BASE_URL`. If that server sends an incomplete certificate chain, point `PLANE_SSL_CERT_PATH` to a `.pem` with the intermediate and root certificates.

## Tests

```
pip install -r requirements-test.txt
python -m pytest tests
```

They use made-up settings and never call Plane or Microsoft Graph.
