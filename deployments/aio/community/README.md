# Pi-Plane All-In-One (AIO) Docker Image

The Pi-Plane All-In-One Docker image packages all Pi-Plane services into a single container for easy deployment and testing. This image includes web interface, API server, background workers, live server, and more.

## What's Included

The AIO image contains the following services:

- **Web App**: Main Pi-Plane web interface, served as static files by the proxy
- **Space** (Port 3002): Public project spaces
- **Admin**: Administrative interface (god mode), served as static files by the proxy
- **API Server** (Port 3004): Backend API
- **Live Server** (Port 3005): Real-time collaboration
- **Proxy** (Port 80, 443): Caddy reverse proxy
- **Worker & Beat**: Background task processing

## Prerequisites

### Required External Services

The AIO image requires these external services to be running:

- **PostgreSQL Database**: For data storage
- **Redis**: For caching and session management
- **RabbitMQ**: For message queuing
- **S3-Compatible Storage**: For file uploads (AWS S3, Google Cloud Storage or MinIO; for Google Cloud Storage see the [Docker guide](../../cli/community/README.md#using-your-own-object-storage-aws-s3-google-cloud-storage))

### Required Environment Variables

You must provide these environment variables:

#### Core Configuration

- `DOMAIN_NAME`: Your domain name or IP address
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `AMQP_URL`: RabbitMQ connection string

#### Storage Configuration

- `AWS_REGION`: AWS region (e.g., us-east-1)
- `AWS_ACCESS_KEY_ID`: S3 access key
- `AWS_SECRET_ACCESS_KEY`: S3 secret key
- `AWS_S3_BUCKET_NAME`: S3 bucket name
- `AWS_S3_ENDPOINT_URL`: S3 endpoint (optional, defaults to AWS)

## Image

The image is published to the GitHub Container Registry as `ghcr.io/osm-piatnica/pi-plane` (`linux/amd64` and `linux/arm64`). Each release is tagged with its exact version (`MAJOR.MINOR.PATCH`, e.g. `2.1.0`; releases before 2.0.0 were `<upstream Plane version>-pi.<n>`) and `latest`; use a version tag to pin a release.

## Quick Start

### Basic Usage

```bash
docker run --name pi-plane-aio --rm -it \
    -p 80:80 \
    -e DOMAIN_NAME=your-domain.com \
    -e DATABASE_URL=postgresql://user:pass@host:port/database \
    -e REDIS_URL=redis://host:port \
    -e AMQP_URL=amqp://user:pass@host:port/vhost \
    -e AWS_REGION=us-east-1 \
    -e AWS_ACCESS_KEY_ID=your-access-key \
    -e AWS_SECRET_ACCESS_KEY=your-secret-key \
    -e AWS_S3_BUCKET_NAME=your-bucket \
    -e SECRET_KEY=your-unique-secret-key \
    -e LIVE_SERVER_SECRET_KEY=your-unique-live-server-secret \
    ghcr.io/osm-piatnica/pi-plane:latest
```

### Example with IP Address

```bash
MYIP=192.168.68.169
docker run --name myaio --rm -it \
    -p 80:80 \
    -e DOMAIN_NAME=${MYIP} \
    -e DATABASE_URL=postgresql://plane:plane@${MYIP}:15432/plane \
    -e REDIS_URL=redis://${MYIP}:16379 \
    -e AMQP_URL=amqp://plane:plane@${MYIP}:15673/plane \
    -e AWS_REGION=us-east-1 \
    -e AWS_ACCESS_KEY_ID=your-access-key \
    -e AWS_SECRET_ACCESS_KEY=your-secret-key \
    -e AWS_S3_BUCKET_NAME=plane-app \
    -e AWS_S3_ENDPOINT_URL=http://${MYIP}:19000 \
    -e SECRET_KEY=your-unique-secret-key \
    -e LIVE_SERVER_SECRET_KEY=your-unique-live-server-secret \
    -e FILE_SIZE_LIMIT=10485760 \
    ghcr.io/osm-piatnica/pi-plane:latest
```

## Configuration Options

### Optional Environment Variables

#### Network & Protocol

- `SITE_ADDRESS`: Server bind address (default: `:80`)
- `APP_PROTOCOL`: `http` or `https` (default: `http`)
- `APP_PORT`: public port, when the container is published on a port other than 80/443 (e.g. `-p 8080:80 -e APP_PORT=8080`). It is added to the web URL and the allowed CORS origins; `DOMAIN_NAME` itself must be a bare domain or IP address.

- `TRUSTED_PROXIES` and `NUM_PROXIES`: how the client IP is determined for rate limiting; pass them with `-e`. The proxy trusts forwarded headers only from private addresses by default (`private_ranges`); behind a CDN or a load balancer with a public address, list its ranges. Before 2.1.0 the default was `0.0.0.0/0`, which let any client spoof `X-Forwarded-For`; see "Client IP and rate limiting behind proxies" in the [Docker Compose guide](../../cli/community/README.md).

#### Security & Secrets

- `SECRET_KEY` (required): Django secret key. It also encrypts saved instance settings, so keep the same value across restarts and container recreation. No default is provided and none is generated.
- `LIVE_SERVER_SECRET_KEY` (required): Live server secret. No default is provided and none is generated.

Set both to unique, private values, either in `plane.env` (`variables.env`) or as environment variables. The container exits at startup if either is empty or still set to a default/placeholder value.

In Plane v1.4.0 to v1.4.2 a container started without `SECRET_KEY` received a generated key that changed on every recreation. When upgrading such a container, read the current key from the running container's `/app/plane.env` and pass it as `SECRET_KEY`.

- `REDIS_SSL_CERT_REQS`: For a `rediss://` `REDIS_URL`, the Redis server certificate and hostname are verified by default (`required`). Set it to `none` to skip verification.
- `REDIS_SSL_CA_CERTS`: Path inside the container to a CA bundle, for a Redis server whose certificate is issued by a private CA. Mount the file with `-v`, for example `-v /path/to/redis-ca.pem:/certs/redis-ca.pem:ro -e REDIS_SSL_CA_CERTS=/certs/redis-ca.pem`.

#### File Handling

- `FILE_SIZE_LIMIT`: Maximum file upload size in bytes until the instance administrator sets one on the General page of the admin app (default: `5242880` = 5 MB)
- `FILE_SIZE_LIMIT_MAX`: The most the administrator can set it to, and the largest request body the proxy accepts, in bytes (default: `104857600` = 100 MB). Keep it at least as large as `FILE_SIZE_LIMIT`

#### API Configuration

- `API_KEY_RATE_LIMIT`: API key rate limit (default: `60/minute`)
- `AUTHENTICATION_RATE_LIMIT`: per-IP throttle for sign-in and one-time-code endpoints (default: `1000/minute`, sized for many users behind one IP)
- `RATE_LIMIT_PER_IP_PER_MIN`: per-client-IP request limit enforced by the Caddy proxy (default: `50000`)
- `ANON_RATE_LIMIT`: per-IP limit on logged-out requests such as public Spaces boards; users behind one IP share it (default: `180/minute`)
- `ASSET_DUPLICATE_RATE_LIMIT`: per-asset limit on duplicating an asset when pasting images in the editor, counted across all users (default: `60/minute`)

## Port Mapping

The following ports are exposed:

- `80`: Main web interface (HTTP)
- `443`: HTTPS (if SSL configured)

## Volume Mounts

### Recommended Persistent Volumes

```bash
-v /path/to/logs:/app/logs \
-v /path/to/data:/app/data
```

## Building the Image

To build the AIO image yourself:

```bash
cd deployments/aio/community
IMAGE_NAME=my-pi-plane-aio ./build.sh --release=2.1.0
```

`build.sh` does not build the image itself: it prepares the `dist/` folder the Dockerfile needs and prints the `docker build` command to run next.

Available build options:

- `--release`: Pi-Plane version to build (required). The build pulls that release's component images, so use a release published from the same code as your checkout
- `--image-name`: Custom image name (default: `ghcr.io/osm-piatnica/pi-plane`)

## Troubleshooting

### Logs

All service logs are available in `/app/logs/`:

- Access logs: `/app/logs/access/`
- Error logs: `/app/logs/error/`

### Health Checks

The container runs multiple services managed by Supervisor. The container's output shows the state of each one:

```bash
docker logs <container-name> 2>&1 | grep -E "entered RUNNING|FATAL|exited"
```

The `migrator` exits with status 0 once the database migrations finish; this takes a few minutes on the first start, and the API (and `/api/` requests, which answer 502 meanwhile) only comes up after that.

### Common Issues

1. **Database Connection Failed**: Ensure PostgreSQL is accessible and credentials are correct
2. **Redis Connection Failed**: Verify Redis server is running and URL is correct
3. **File Upload Issues**: Check S3 credentials and bucket permissions

### Environment Validation

The container will validate required environment variables on startup and display helpful error messages if any are missing.

## Production Considerations

- Use proper SSL certificates for HTTPS
- Configure proper backup strategies for data
- Monitor resource usage and scale accordingly
- Use external load balancer for high availability
- Regularly update to latest versions
- Secure your environment variables and secrets

## Support

For issues and support, open an issue at [OSM-Piatnica/pi-plane](https://github.com/OSM-Piatnica/pi-plane/issues). Pi-Plane is a fork of [Plane](https://github.com/makeplane/plane); upstream documentation at [docs.plane.so](https://docs.plane.so/) still applies to features inherited from it.
