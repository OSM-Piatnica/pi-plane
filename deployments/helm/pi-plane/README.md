<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Pi-Plane Helm chart

Deploys Pi-Plane (the `ghcr.io/osm-piatnica/pi-plane-*` images) on Kubernetes: the web app, the public boards
(`space`), the admin (`admin`, served at `/god-mode`), the collaboration server (`live`), the API with its worker,
scheduler and migration Job, and, if you want them, PostgreSQL, Valkey, RabbitMQ and MinIO.

The chart was written for this fork. Its structure was informed by the Helm charts of
[Hangar](https://github.com/szymczag/hangar) (values schema, Gateway API support, ingress-only network policies)
and [paperplane](https://github.com/inomotech-foss/paperplane) (bundled stores and the same single-host routing
with Ingress or Gateway API), both AGPL-3.0-only; the templates themselves are new and tied to this repository's
compose files and images.

## What you need

- Kubernetes 1.27 or newer and Helm 3.12 or newer (4.x works too);
- an ingress controller (the chart renders an `Ingress`), or a Gateway API implementation (`gateway.enabled`);
- a default `StorageClass` for the bundled stores (or set `*.storage.className`);
- a DNS name for the installation, and TLS in front of it.

The chart does not install cluster infrastructure: no ingress or Gateway controller, cert-manager, CNI or CSI driver.

## Install

```bash
helm install pi-plane ./deployments/helm/pi-plane \
  --namespace plane --create-namespace \
  --set publicUrl=https://plane.example.com \
  --set ingress.className=nginx \
  --set ingress.tls.enabled=true --set ingress.tls.secretName=plane-tls
```

`publicUrl` is the only required value. The defaults give a complete installation for evaluation: every store is
bundled and the credentials are generated. Then open `https://plane.example.com/god-mode/` and create the instance
administrator.

The chart is not published to a registry yet; install it from a checkout of this repository (or `helm package` it).
It deploys the images of the chart's `appVersion` unless you set `image.tag`.

## Routing

One host serves everything, split by path, exactly as the all-in-one proxy does:

| Path                             | Goes to                                                 |
| -------------------------------- | ------------------------------------------------------- |
| `/`                              | `web`                                                   |
| `/spaces`                        | `space` (public boards)                                 |
| `/god-mode`                      | `admin`                                                 |
| `/live`                          | `live` (collaborative editing, WebSockets)              |
| `/api`, `/auth`, `/static`       | `api`                                                   |
| `/<bucket>` (default `/uploads`) | the bundled MinIO, for browser uploads (presigned URLs) |

The same list renders an `Ingress` or, with `gateway.enabled`, `HTTPRoute`s that attach to a Gateway you own (see
`examples/gateway-values.yaml`). Allow request bodies of at least `app.fileSizeLimit` (5 MiB by default) on
whatever sits in front: with `ingress.className: nginx` the chart sets the `proxy-body-size` annotation for you.
The web, space and admin images use addresses relative to the host, so they need no per-installation configuration.

## Credentials

By default the chart creates the Secret `<release>-pi-plane-credentials` with random values (Django `SECRET_KEY`, the
live server key, and the database, RabbitMQ and object storage passwords) on first install and keeps them across
upgrades by reading the Secret back. Notes:

- `helm template` and `helm install --dry-run` cannot read the cluster and print new values each time;
- the Secret is annotated `helm.sh/resource-policy: keep`, so uninstalling the release leaves it (and the data
  volumes) in place. **Back it up**: without `SECRET_KEY` the stored data cannot be read;
- to own the credentials yourself set `secrets.existingSecret`. It needs `SECRET_KEY`, `LIVE_SERVER_SECRET_KEY`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, plus `POSTGRES_PASSWORD` and `RABBITMQ_PASSWORD` when those stores
  are bundled (see `examples/production-values.yaml`).
- to start over after an uninstall, delete the data volumes (`kubectl delete pvc -l app.kubernetes.io/instance=<release>`)
  **and** the credentials Secret together: a new Secret with the old database volume leaves PostgreSQL with the
  previous password and the API cannot connect.

Further secrets (SMTP password, SSO client secrets, ...) go in Secrets of your own and are attached with
`app.envFrom`; plain settings with `app.env`. Both are read into the instance configuration on the first start, after
which God Mode wins (see `apps/api/.env.example`, and `docs/sso.md` for sign-in with Microsoft Entra, Google or
another OpenID Connect provider).

## Production

The bundled stores are single replicas without backups: use them to evaluate. For production switch them off and
give the chart managed services; the connection strings come inline or from a Secret:

```yaml
postgresql: { enabled: false, external: { urlSecret: { name: pi-plane-database, key: url } } }
valkey: { enabled: false, external: { url: "rediss://cache.example.com:6380/0" } }
rabbitmq: { enabled: false, external: { url: "amqps://plane:...@mq.example.com:5671/plane" } }
objectStorage: { region: eu-central-1, bucket: plane-uploads, bundled: { enabled: false } }
```

Percent-encode special characters in passwords inside URLs. For an S3 store other than the bundled MinIO the browser
uploads straight to it through presigned URLs, so `objectStorage.external.endpoint` must be reachable from there
(leave it empty for AWS S3). The complete example is `examples/production-values.yaml`.

Also consider `networkPolicy.enabled` (ingress rules: everything in the release talks to itself, only the public
components accept the ingress controller), the `pdb` of each component, resource requests, and more than one replica
of `api`, `worker`, `web` and `live`. The `beat` scheduler is always exactly one pod.

## Migrations and upgrades

A Job named `<release>-pi-plane-migrator-<revision>` applies the database migrations; the API, the worker and the
scheduler wait for it in their entrypoints. Helm deletes the previous revision's Job when it is no longer in the
manifest. To upgrade, change `image.tag` (or the chart) and run `helm upgrade`; read the release notes for
migrations that need care.

## Security notes

- Every workload uses a dedicated ServiceAccount without a mounted token, and no RBAC is created.
- Application containers drop all capabilities, forbid privilege escalation and use the runtime default seccomp
  profile. The images currently run as root, so `runAsNonRoot` is not set; the bundled stores keep their own entrypoint
  user handling and only forbid privilege escalation.
- Cookie-authenticated writes are only accepted from `publicUrl` and `app.extraCorsOrigins` (`CORS_ALLOWED_ORIGINS`).
- Set `app.numProxies` to the number of reverse proxies in front of the API, or the per-IP throttles see the proxy's
  address instead of the client's.

## Validate a change

```bash
helm lint deployments/helm/pi-plane --strict -f deployments/helm/pi-plane/ci/default-values.yaml
helm template pi-plane deployments/helm/pi-plane -f deployments/helm/pi-plane/ci/gateway-values.yaml | kubeconform -strict -ignore-missing-schemas -summary
```

CI (`.github/workflows/helm.yaml`) lints and renders the chart with every file under `ci/`, validates the output against
the Kubernetes schemas and checks that invalid values are rejected by `values.schema.json`. CI does not install the chart on a cluster. The
default install (bundled stores, Ingress) was run by hand on k3s with Traefik (`ingress.className=traefik`, plain
`http://` `publicUrl`): migrations, routing and the first God Mode sign-in worked. The Gateway API and external-store
values are only linted and rendered.

## Values

`values.yaml` is the reference: every setting is commented there. The groups are `publicUrl`, `image`, `ingress` and
`gateway`, `secrets`, `app` (settings of the API), one block per component (`api`, `worker`, `beat`, `migrator`, `live`,
`web`, `space`, `admin`), the stores (`postgresql`, `valkey`, `rabbitmq`, `objectStorage`), and `networkPolicy`.
`values.schema.json` validates the types and ranges.
