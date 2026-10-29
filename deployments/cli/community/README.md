# Self Hosting

In this guide, we will walk you through the process of setting up a self-hosted environment. Self-hosting allows you to have full control over your applications and data. It's a great way to ensure privacy, control, and customization.

We will cover two main options for setting up your self-hosted environment: using a cloud server or using your desktop. For the cloud server, we will use an AWS EC2 instance. For the desktop, we will use Docker to create a local environment.

Let's get started!

## Setting up Docker Environment

<details>
  <summary>Option 1 - Using Cloud Server</summary>
  <p>Best way to start is to create EC2 machine on AWS. It must have minimum of 2vCPU and 4GB RAM.</p>
  <p>Run the below command to install docker engine.</p>

`curl -fsSL https://get.docker.com | sh -`

</details>

---

<details>
  <summary>Option 2 - Using Desktop</summary>

#### For Mac

  <ol>
    <li> Download Docker Desktop for Mac from the <a href="https://hub.docker.com/editions/community/docker-ce-desktop-mac/" target="_blank">Docker Hub</a>. </li>
    <li> Double-click the downloaded `.dmg` file and drag the Docker app icon to the Applications folder. </li>
    <li>Open Docker Desktop from the Applications folder. You might be asked to provide your system password to install additional software.</li>
  </ol>

#### For Windows:

  <ol>
    <li>Download Docker Desktop for Windows from the <a href="https://hub.docker.com/editions/community/docker-ce-desktop-windows/" target="_blank">Docker Hub</a>.</li>
    <li>Run the installer and follow the instructions. You might be asked to enable Hyper-V and "Containers" Windows features.</li>
    <li>Open Docker Desktop. You might be asked to log out and log back in, or restart your machine, for changes to take effect.</li>
  </ol>

After installation, you can verify the installation by opening a terminal (Command Prompt on Windows, Terminal app on Mac) and running the command `docker --version`. This should display the installed version of Docker.

</details>

---

## Installing Pi-Plane

Installing Pi-Plane is a very easy and minimal step process.

### Prerequisite

- Docker installed and running
- OS with bash scripting enabled (Ubuntu, Linux AMI, macos). Windows systems need to have [gitbash](https://git-scm.com/download/win)
- User context used must have access to docker services. In most cases, use sudo su to switch as root user
- `curl` (and `git` for local builds); `jq` and the `busybox` image for the restore script
- Use the terminal (or gitbash) window to run all the future steps

### Downloading Latest Release

```
mkdir plane-selfhost

cd plane-selfhost
```

#### For _Docker Compose_ based setup

```
curl -fsSL -o setup.sh https://github.com/OSM-Piatnica/pi-plane/releases/latest/download/setup.sh

chmod +x setup.sh
```

#### For _Docker Swarm_ based setup

```
curl -fsSL -o setup.sh https://github.com/OSM-Piatnica/pi-plane/releases/latest/download/swarm.sh

chmod +x setup.sh
```

---

### Container images and versions

Pi-Plane publishes multi-architecture (`linux/amd64`, `linux/arm64`) images to the GitHub Container Registry:

| Component    | Image                                 |
| ------------ | ------------------------------------- |
| Web          | `ghcr.io/osm-piatnica/pi-plane-web`   |
| Space        | `ghcr.io/osm-piatnica/pi-plane-space` |
| Admin        | `ghcr.io/osm-piatnica/pi-plane-admin` |
| Live         | `ghcr.io/osm-piatnica/pi-plane-live`  |
| API / worker | `ghcr.io/osm-piatnica/pi-plane-api`   |
| Proxy        | `ghcr.io/osm-piatnica/pi-plane-proxy` |
| All-in-one   | `ghcr.io/osm-piatnica/pi-plane`       |

Versions are plain `MAJOR.MINOR.PATCH` (for example `2.1.0`) from 2.0.0 on. Earlier releases were `<upstream Plane version>-pi.<n>` (for example `1.3.1-pi.5`).

- Each release is published under its exact version tag (e.g. `2.1.0`, without the `v` used by the GitHub release tag) and `latest`. Pre-releases (`-rc`, `-alpha`, `-beta`) get only their version tag.
- `./setup.sh` installs the latest release. Install writes the release it installed into `APP_RELEASE` in `plane.env`, so the installation stays on that version until you choose **Upgrade**; to move to another version by hand, change it there.
- To use a different registry or a local build, set `IMAGE_REPO` in `plane.env` (default `ghcr.io/osm-piatnica/pi-plane`).

---

### Proceed with setup

Above steps will set you ready to install and start Pi-Plane services.

Lets get started by running the `./setup.sh` command.

This will prompt you with the below options.

#### Docker Compose

```bash
Select an Action you want to perform:
   1) Install
   2) Start
   3) Stop
   4) Restart
   5) Upgrade
   6) View Logs
   7) Backup Data
   8) Exit

Action [2]: 1
```

For the 1st time setup, type "1" as action input.

This will create a folder `plane-app` and will download 2 files inside that

- `docker-compose.yaml`
- `plane.env`

The script ends after the install. Run `./setup.sh` again for the next action (for example `2` to start the services).

#### Docker Swarm

```bash
Select an Action you want to perform:
   1) Deploy Stack
   2) Remove Stack
   3) View Stack Status
   4) Redeploy Stack
   5) Upgrade
   6) View Logs
   7) Exit

Action [3]: 1
```

For the 1st time setup, type "1" as action input.

The script asks for a stack name (default `plane`), creates a folder `plane-app`, downloads two files into it, `docker-compose.yml` and `plane.env`, and deploys the stack. It then ends; run `./setup.sh` again for the next action.

---

### Continue with setup - Environment Settings

Before proceeding, we suggest you review the `plane.env` file and set the values.
Below are the most import keys you must refer to. _<span style="color: #fcba03">You can use any text editor to edit this file</span>_.

> `LISTEN_HTTP_PORT` - This is default set to `80`. Make sure the port you choose to use is not preoccupied. (e.g `LISTEN_HTTP_PORT=8080`)

> `WEB_URL` - This is default set to `http://localhost`. Change this to the FQDN you plan to use along with LISTEN_HTTP_PORT (eg. `https://plane.example.com:8080` or `http://[IP-ADDRESS]:8080`)

> `CORS_ALLOWED_ORIGINS` - This is default set to `http://localhost`. Change this to the FQDN you plan to use along with LISTEN_HTTP_PORT (eg. `https://plane.example.com:8080` or `http://[IP-ADDRESS]:8080`)

> `SECRET_KEY` and `LIVE_SERVER_SECRET_KEY` - These ship with the placeholder value `change-this-key-on-deployment`. **Replace both with your own random values before the first start**, e.g. `openssl rand -hex 32` (use a different value for each). The API still starts with the placeholders, but only logs a `SECURITY: SECRET_KEY is set to a known insecure or placeholder value` warning, and anyone who knows the placeholder can forge session data. The all-in-one image refuses to start with placeholder values.

> `ENABLE_SPACE` / `SPACE_REPLICAS` - Space is the public site that shows projects shared on the web. Set `SPACE_REPLICAS=0` (or install with `ENABLE_SPACE=0 ./setup.sh install`) to leave it out: its image is not downloaded, it is not started, `/spaces` answers 404 and projects cannot be shared. See [Sharing a project on the web](../../../docs/web-sharing.md#turning-web-sharing-off-for-the-whole-instance).

There are many other settings you can play with. Configure email in God mode (**Email** under the instance settings), not in `plane.env`: this stack does not pass `EMAIL_*` variables to the API. Email is what lets you invite your teammates onto the platform.

#### Client IP and rate limiting behind proxies

Some endpoints are rate-limited per client IP. Two settings in `plane.env` control how that IP is determined:

- **Pi-Plane directly on the internet behind the bundled proxy:** set `TRUSTED_PROXIES=private_ranges` (or your load balancer's ranges) and `NUM_PROXIES=1`.
- **Behind an additional load balancer or CDN:** add its ranges to `TRUSTED_PROXIES` (space-separated, e.g. `TRUSTED_PROXIES=private_ranges 203.0.113.0/24`) and raise `NUM_PROXIES` by one per extra hop (e.g. `NUM_PROXIES=2`).
- **Behind a CDN or a load balancer with a public address:** put its ranges in `TRUSTED_PROXIES`. The default is `private_ranges`, so the bundled proxy believes `X-Forwarded-For` only from private addresses; a client on the internet cannot choose its own address and get around the per-IP limits. The cost is that behind a public-address proxy every request appears to come from that proxy until you list its ranges.
- **Installations made before 2.1.0** have `TRUSTED_PROXIES=0.0.0.0/0` in `plane.env`, which trusts every peer and lets any client spoof its address; change it as above.

`TRUSTED_PROXIES` is read only by the bundled proxy, `NUM_PROXIES` only by the API, worker and scheduler.

Restart the services after changing these values.

#### Using your own object storage (AWS S3, Google Cloud Storage, Azure Blob Storage)

Files (attachments, images, avatars, covers, exports) go to the bundled `plane-minio` service, which keeps them in a Docker volume. To use an S3 service instead, set these in `plane.env` and restart:

```bash
USE_MINIO=0
AWS_S3_ENDPOINT_URL=          # empty for AWS S3
AWS_REGION=eu-central-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=your-bucket
```

The bundled service can stay; it is then unused. (You can comment it out in `docker-compose.yaml`, but an upgrade downloads a fresh copy of that file.) Browsers upload straight to the bucket, so the bucket needs CORS rules that allow your `WEB_URL` as an origin (methods `GET`, `POST`, `PUT`, `HEAD`). Files already in the bundled storage are not copied; move them yourself.

**Google Cloud Storage** works through its S3-compatible API with an HMAC key. It was tested with attachments uploaded from the browser, avatars, exports, signed downloads, and copying, listing and deleting objects.

1. Create a bucket (uniform access control; public access prevention can stay on).
2. Create a service account and give it, on that bucket, the roles **Storage Object Admin** and **Storage Legacy Bucket Reader** (the second lets the API check at start that the bucket exists).
3. Create an HMAC key for the service account (Cloud Storage → Settings → Interoperability, or `gcloud storage hmac create <service-account-email>`). Keep the secret; Google shows it once.
4. Set the CORS rules, with your `WEB_URL` as the origin, for example `cors.json`:

   ```json
   [
     {
       "origin": ["https://plane.example.com"],
       "method": ["GET", "POST", "PUT", "HEAD"],
       "responseHeader": ["Content-Type", "x-goog-meta-*", "ETag"],
       "maxAgeSeconds": 3600
     }
   ]
   ```

   and `gcloud storage buckets update gs://your-bucket --cors-file=cors.json`.

5. In `plane.env`: `USE_MINIO=0`, `AWS_S3_ENDPOINT_URL=https://storage.googleapis.com`, `AWS_REGION=auto`, `AWS_ACCESS_KEY_ID=<HMAC access id>`, `AWS_SECRET_ACCESS_KEY=<HMAC secret>` and `AWS_S3_BUCKET_NAME=your-bucket`.

Releases up to 2.1.0 cannot write export files to Google Cloud Storage (the export fails with `SignatureDoesNotMatch`); later releases can.

Other S3-compatible services (Ceph, Cloudflare R2, Backblaze B2, Wasabi, and so on) take the same settings. They were not tested here; presigned uploads and CORS are where they differ.

**Azure Blob Storage** is not S3-compatible; it has its own storage mode, selected with `STORAGE_PROVIDER=azure`:

```bash
STORAGE_PROVIDER=azure
USE_MINIO=0
AZURE_STORAGE_ACCOUNT_NAME=your-account
AZURE_STORAGE_ACCOUNT_KEY=...       # or AZURE_STORAGE_CONNECTION_STRING instead of both
AZURE_STORAGE_CONTAINER=uploads     # created at start if it does not exist
```

The container needs CORS rules for your `WEB_URL`, and a file larger than the size announced for its upload is deleted right after the upload. The full guide, including the CORS command, other clouds and what was tested (the Azurite emulator only, not a real Azure account), is [Azure Blob Storage](../../../docs/azure-blob-storage.md). Not available in the all-in-one image.

---

### Continue with setup - Start Server (Docker Compose)

Lets again run the `./setup.sh` command. You will again be prompted with the below options. This time select `2` to start the services

```bash
Select a Action you want to perform:
   1) Install
   2) Start
   3) Stop
   4) Restart
   5) Upgrade
   6) View Logs
   7) Backup Data
   8) Exit

Action [2]: 2
```

Expect something like this.  
![Downloading docker images](images/download.png)

Be patient as it might take sometime based on download speed and system configuration. If all goes well, you must see something like this

![Downloading completed](images/started.png)

This is the confirmation that all images were downloaded and the services are up & running.

You have successfully self hosted Pi-Plane instance. Access the application by going to IP or domain you have configured it (e.g `https://plane.example.com:8080` or `http://[IP-ADDRESS]:8080`)

---

### Stopping the Server / Remove Stack

In case you want to make changes to `plane.env` variables, we suggest you to stop the services before doing that.

#### Docker Compose

Lets again run the `./setup.sh` command. You will again be prompted with the below options. This time select `3` to stop the services

```bash
Select a Action you want to perform:
   1) Install
   2) Start
   3) Stop
   4) Restart
   5) Upgrade
   6) View Logs
   7) Backup Data
   8) Exit

Action [2]: 3
```

If all goes well, you must see something like this

![Stop Services](images/stopped.png)

#### Docker Swarm

Lets again run the `./setup.sh` command. You will again be prompted with the below options. This time select `2` to stop the services

```bash
Select an Action you want to perform:
   1) Deploy Stack
   2) Remove Stack
   3) View Stack Status
   4) Redeploy Stack
   5) Upgrade
   6) View Logs
   7) Exit

Action [3]: 2
```

If all goes well, you will see the confirmation from docker cli

---

### Restarting the Server / Redeploy Stack

In case you want to make changes to `plane.env` variables, without stopping the server or you noticed some abnormalies in services, you can restart the services with `RESTART` / `REDEPLOY` option.

Lets again run the `./setup.sh` command. You will again be prompted with the below options. This time select `4` to restart the services

#### Docker Compose

```bash
Select a Action you want to perform:
   1) Install
   2) Start
   3) Stop
   4) Restart
   5) Upgrade
   6) View Logs
   7) Backup Data
   8) Exit

Action [2]: 4
```

If all goes well, you must see something like this

![Restart Services](images/restart.png)

#### Docker Swarm

```bash
   1) Deploy Stack
   2) Remove Stack
   3) View Stack Status
   4) Redeploy Stack
   5) Upgrade
   6) View Logs
   7) Exit

Action [3]: 4
```

If all goes well, you will see the confirmation from docker cli

---

### Upgrading Pi-Plane Version

It is always advised to keep Pi-Plane up to date with the latest release.

> Download the latest `setup.sh` (see [Downloading Latest Release](#downloading-latest-release)) before upgrading. The upgrade runs your local copy of the script, and newer versions generate or rotate the object-storage (MinIO) credentials in `plane.env`.

Lets again run the `./setup.sh` command. You will again be prompted with the below options. This time select `5` to upgrade the release.

#### Docker Compose

```bash
Select a Action you want to perform:
   1) Install
   2) Start
   3) Stop
   4) Restart
   5) Upgrade
   6) View Logs
   7) Backup Data
   8) Exit

Action [2]: 5
```

By choosing this, it will stop the services and then will download the latest `docker-compose.yaml` and `plane.env`.

You must expect the below message

![Alt text](images/upgrade.png)

The script then ends.

> It is very important for you to validate the `plane.env` for the new changes.

Once done with making changes in `plane.env` file, jump on to `Start Server`

#### Docker Swarm

Lets again run the `./setup.sh` command. You will again be prompted with the below options. This time select `5` to upgrade the release.

```bash
   1) Deploy Stack
   2) Remove Stack
   3) View Stack Status
   4) Redeploy Stack
   5) Upgrade
   6) View Logs
   7) Exit

Action [3]: 5
```

By choosing this, it downloads the latest `docker-compose.yml` and `plane.env` and redeploys the stack, removing the old one on the way. There is no pause to edit `plane.env` in between.

> It is very important for you to validate the `plane.env` for the new changes; if you change it, choose `Redeploy Stack` afterwards.

---

### View Logs

There would a time when you might want to check what is happening inside the API, Worker or any other container.

Lets again run the `./setup.sh` command. You will again be prompted with the below options.

This time select `6` to view logs.

#### Docker Compose

```bash
Select a Action you want to perform:
   1) Install
   2) Start
   3) Stop
   4) Restart
   5) Upgrade
   6) View Logs
   7) Backup Data
   8) Exit

Action [2]: 6
```

#### Docker Swarm

```bash
   1) Deploy Stack
   2) Remove Stack
   3) View Stack Status
   4) Redeploy Stack
   5) Upgrade
   6) View Logs
   7) Exit

Action [3]: 6
```

#### Service Menu Options for Logs

This will further open sub-menu with list of services

```bash
Select a Service you want to view the logs for:
   1) Web
   2) Space
   3) API
   4) Worker
   5) Beat-Worker
   6) Migrator
   7) Proxy
   8) Redis
   9) Postgres
   10) Minio
   11) RabbitMQ
   0) Back to Main Menu

Service: 3
```

Select any of the service to view the logs e.g. `3`. Expect something similar to this

```bash
api-1  | Waiting for database...
api-1  | Database available!
api-1  | Waiting for database migrations to complete...
api-1  | Waiting for database migrations to complete...
api-1  | Waiting for database migrations to complete...
api-1  | Waiting for database migrations to complete...
api-1  | Waiting for database migrations to complete...
api-1  | Waiting for database migrations to complete...
api-1  | Waiting for database migrations to complete...
api-1  | No migrations Pending. Starting processes ...
api-1  | Instance registered
api-1  | ENABLE_SIGNUP loaded with value from environment variable.
api-1  | ENABLE_EMAIL_PASSWORD loaded with value from environment variable.
api-1  | ENABLE_MAGIC_LINK_LOGIN loaded with value from environment variable.
api-1  | GOOGLE_CLIENT_ID loaded with value from environment variable.
api-1  | GITHUB_CLIENT_ID loaded with value from environment variable.
api-1  | GITHUB_CLIENT_SECRET loaded with value from environment variable.
api-1  | EMAIL_HOST loaded with value from environment variable.
api-1  | EMAIL_HOST_USER loaded with value from environment variable.
api-1  | EMAIL_HOST_PASSWORD loaded with value from environment variable.
api-1  | EMAIL_PORT loaded with value from environment variable.
api-1  | EMAIL_FROM loaded with value from environment variable.
api-1  | EMAIL_USE_TLS loaded with value from environment variable.
api-1  | EMAIL_USE_SSL loaded with value from environment variable.
api-1  | OPENAI_API_KEY loaded with value from environment variable.
api-1  | GPT_ENGINE loaded with value from environment variable.
api-1  | UNSPLASH_ACCESS_KEY loaded with value from environment variable.
api-1  | Checking bucket...
api-1  | Bucket 'uploads' does not exist. Creating bucket...
api-1  | Bucket 'uploads' created successfully.
api-1  | Public read access policy set for bucket 'uploads'.
api-1  | Cache Cleared
api-1  | [2024-05-02 03:56:01 +0000] [1] [INFO] Starting gunicorn 21.2.0
api-1  | [2024-05-02 03:56:01 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000 (1)
api-1  | [2024-05-02 03:56:01 +0000] [1] [INFO] Using worker: uvicorn.workers.UvicornWorker
api-1  | [2024-05-02 03:56:01 +0000] [25] [INFO] Booting worker with pid: 25
api-1  | [2024-05-02 03:56:03 +0000] [25] [INFO] Started server process [25]
api-1  | [2024-05-02 03:56:03 +0000] [25] [INFO] Waiting for application startup.
api-1  | [2024-05-02 03:56:03 +0000] [25] [INFO] ASGI 'lifespan' protocol appears unsupported.
api-1  | [2024-05-02 03:56:03 +0000] [25] [INFO] Application startup complete.

```

To exit this, use `CTRL+C` and then you will land on to the main-menu with the list of actions.

Similarly, you can view the logs of other services.

---

### Backup Data (Docker Compose)

There would a time when you might want to backup your data from docker volumes to external storage like S3 or drives.

Lets again run the `./setup.sh` command. You will again be prompted with the below options. This time select `7` to Backup the data.

```bash
Select a Action you want to perform:
   1) Install
   2) Start
   3) Stop
   4) Restart
   5) Upgrade
   6) View Logs
   7) Backup Data
   8) Exit

Action [2]: 7
```

The backup copies the data out of the running containers, so the stack must be running (it fails with "container not found" otherwise), and the database files are copied while it runs. The logs and the proxy's certificates volume are not included. In response, you can find the backup folder

```bash
Backing up plane-db data...
Copying plane-db data directory...
Successfully backed up pgdata data
(the same for uploads, rabbitmq_data and redisdata)

Backup completed successfully. Backup files are stored in /....../plane-app/backup/20240502-1120
```

---

### Restore Data (Docker Compose)

When you want to restore the previously backed-up data, follow the instructions below.

1. Make sure that Pi-Plane is installed, started, and then stopped. This ensures that the Docker volumes are created.

1. **The restore replaces the data in the existing volumes:** each volume is deleted and recreated from the backup, so whatever is in the installation now is lost. Take a fresh backup first if in doubt.

1. Download the restore script using the command below. We suggest downloading it in the same folder as `setup.sh`.

   ```bash
   curl -fsSL -o restore.sh https://github.com/OSM-Piatnica/pi-plane/releases/latest/download/restore.sh
   chmod +x restore.sh
   ```

1. Execute the command below to restore your data.

   ```bash
   ./restore.sh <path to backup folder containing *.tar.gz files>
   ```

   As an example, for a backup folder `/opt/plane-selfhost/plane-app/backup/20240722-0914`, expect the response below:

   ```bash
   --------------------------------------------
    ____  _                          /////////
   |  _ \| | __ _ _ __   ___         /////////
   | |_) | |/ _` | '_ \ / _ \   /////    /////
   |  __/| | (_| | | | |  __/   /////    /////
   |_|   |_|\__,_|_| |_|\___|        ////
                                    ////
   --------------------------------------------
   Project management tool from the future
   --------------------------------------------
   Found /opt/plane-selfhost/plane-app/backup/20240722-0914/pgdata.tar.gz
   .....Restoring plane-app_pgdata
   .....Successfully restored volume plane-app_pgdata from pgdata.tar.gz

   Found /opt/plane-selfhost/plane-app/backup/20240722-0914/redisdata.tar.gz
   .....Restoring plane-app_redisdata
   .....Successfully restored volume plane-app_redisdata from redisdata.tar.gz

   Found /opt/plane-selfhost/plane-app/backup/20240722-0914/uploads.tar.gz
   .....Restoring plane-app_uploads
   .....Successfully restored volume plane-app_uploads from uploads.tar.gz


   Restore completed successfully.
   ```

1. Start the Plane instance using `./setup.sh start`.
