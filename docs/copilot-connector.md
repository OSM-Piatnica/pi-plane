<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Microsoft 365 Copilot connector

The `copilot-connector` service copies the work items of one workspace into Microsoft Graph, so people can ask Microsoft 365 Copilot about them ("what is assigned to me in project X", "what is the status of …"). Each work item carries a list of who may see it, and Copilot answers each person only from the work items they may see.

The code is in `apps/copilot-connector`; the image is `ghcr.io/osm-piatnica/pi-plane-copilot-connector`, published with the other images.

## What it does

Every `COPILOT_SYNC_INTERVAL_MINUTES` (30 by default) it:

1. checks the connection and its schema in Microsoft Graph, and creates or updates them when they are missing or older than the code (the first time this takes 5–15 minutes);
2. reads every project of the workspace through the public API, with a [bot token](bot-tokens.md);
3. sends the work items that changed since the last run: title, description, state, priority, assignees, author, project, dates and a link to the work item. Once a day it sends everything again;
4. removes from Copilot the work items that were deleted in Plane, or whose project was deleted. If an unusually large share would disappear at once, it removes nothing and logs a warning instead.

A failed run (for example a Microsoft outage) is logged and retried on the next one; the service keeps running. Two runs never overlap. The state (which work items were sent, as ids and hashes) is kept in the `copilot_connector_data` volume.

The service calls the API inside the stack (`http://api:8000`), so it needs no certificate and no access through the proxy. Links in Copilot use `WEB_URL`.

## Who sees what

`COPILOT_ACL_TYPE`:

| Value | A work item is visible to |
| --- | --- |
| `precise` (default) | the people assigned to it, directly or through an assigned group. A work item nobody is assigned to is visible to the **project lead**; in a project without a lead, to nobody (it is not sent). |
| `project` | every member of the project, as in Plane |
| `everyone` | everybody in the company |

In every mode the rules of Plane still apply: only active members of the project, a guest only what Plane shows them (without *Guests can view all work items*, only what they created), never a bot. A person is matched to their Microsoft 365 account by email address, so the address in Plane must be their sign-in name (UPN) in Entra ID; the log lists the people it could not match. Copilot does not say "you have no access": work items a person may not see are simply not among their results.

## Turning it on

1. **Entra ID app.** Register an app with the application permissions `ExternalConnection.ReadWrite.OwnedBy`, `ExternalItem.ReadWrite.OwnedBy` and `User.Read.All`, grant admin consent, and create a client secret.
2. **Bot token.** In God Mode → Bot tokens, create a token for the workspace ([bot tokens](bot-tokens.md)).
3. **plane.env** on the server (next to `compose.yaml`; never commit it):

   ```
   COPILOT_CONNECTOR_REPLICAS=1
   COPILOT_AZURE_TENANT_ID=<tenant id>
   COPILOT_AZURE_CLIENT_ID=<app id>
   COPILOT_AZURE_CLIENT_SECRET=<client secret>
   COPILOT_PLANE_WORKSPACE_SLUG=<workspace slug>
   COPILOT_PLANE_API_TOKEN=<bot token>
   COPILOT_ACL_TYPE=precise
   COPILOT_SYNC_INTERVAL_MINUTES=30
   ```

   Restart the stack (`./swarm.sh restart`, or `docker stack deploy` again).
4. **Microsoft 365 admin center.** Once the connection shows up as ready (Search & intelligence → Data sources), make sure it is included in **Search & intelligence → Customizations → Verticals → All → Manage connector results**, so Copilot uses it.

The server needs outbound HTTPS to `login.microsoftonline.com` and `graph.microsoft.com`.

## Other settings

| Key | Meaning | Default |
| --- | --- | --- |
| `COPILOT_GRAPH_CONNECTION_ID` | Id of the connection in Microsoft Graph (lowercase letters and digits) | `piplaneconnector` |
| `COPILOT_GRAPH_CONNECTION_NAME` | Its name in the Microsoft 365 admin center | `Pi-Plane Graph Connector` |
| `COPILOT_ICON_URL` | Icon next to the results in Copilot | the instance's own icon |
| `COPILOT_PLANE_API_URL` | Where the API is called | `http://api:8000` |

## Checking on it

```
docker service logs -f plane_copilot-connector        # Swarm
docker compose logs -f copilot-connector             # Docker Compose
```

Each run ends with `=== przebieg zakonczony, kod 0 ===` (1 when something failed: the lines above say what). To send everything again right away, or to allow a large deletion that the run refused:

```
docker exec -it <container> python sync_service.py --full
docker exec -it <container> python sync_service.py --allow-mass-delete
```

`python plane_graph_diag.py --user <email> --from-plane --limit 3` in the same container shows what Graph holds for a few work items and whether the person is on their access list.

## The MCP server

`apps/copilot-connector/plane_mcp_server.py` answers the same questions live, without copying data, for Copilot agents and other MCP clients. It is not part of the stack yet: it needs a public HTTPS address and Entra ID sign-in. Its settings are described at the top of the file.
