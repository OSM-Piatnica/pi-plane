# Kubernetes: Pi-Plane

Pi-Plane has a Helm chart: [`deployments/helm/pi-plane`](../../helm/pi-plane/README.md). It deploys the Pi-Plane images
from the GitHub Container Registry (`ghcr.io/osm-piatnica/pi-plane-*`, listed in the
[CLI deployment guide](../../cli/community/README.md#container-images-and-versions)), with an Ingress or Gateway API
routes, bundled or external PostgreSQL, Valkey, RabbitMQ and S3-compatible storage, generated or operator-owned
credentials, and optional network policies and disruption budgets.

```bash
helm install pi-plane ./deployments/helm/pi-plane \
  --namespace plane --create-namespace \
  --set publicUrl=https://plane.example.com
```

The chart is installed from a checkout of this repository; it is not published to a registry yet. See its README for
routing, credentials, production settings and upgrades.

The upstream [Plane Community chart](https://artifacthub.io/packages/helm/makeplane/plane-ce) deploys upstream `makeplane`
images, not Pi-Plane, so use this chart instead.
