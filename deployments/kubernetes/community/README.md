# Kubernetes: Pi-Plane

Pi-Plane does not publish a Helm chart. The upstream [Plane Community chart](https://artifacthub.io/packages/helm/makeplane/plane-ce) deploys upstream `makeplane` images, not Pi-Plane.

To run Pi-Plane on Kubernetes, use the Pi-Plane images from the GitHub Container Registry (`ghcr.io/osm-piatnica/pi-plane-*`, listed in the [CLI deployment guide](../../cli/community/README.md#container-images-and-versions)) with your own manifests, or override the chart's image repositories and tags to point at them.
