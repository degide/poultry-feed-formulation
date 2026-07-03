# Production Deployment Guide: Contabo VPS

This guide documents the procedures for deploying the dynamic least-cost poultry feed formulation system to a production environment on a **Contabo VPS** (4 vCPUs, 8GB RAM, 150GB SSD) running Ubuntu 22.04 LTS, using Docker and Docker Compose.

## Deployment Architecture

The production environment consists of three containerized services managed by Docker Compose:

1.  **FastAPI Backend**: Runs asynchronously under Uvicorn, handling API routing, forecaster training/predictions, and optimization jobs.
2.  **PostgreSQL Database**: Persists user credentials, flock records, price snapshots, and historical price records.
3.  **Nginx Reverse Proxy & SSL (Host Layer)**: Manages incoming HTTPS requests, handles SSL certificates via Let's Encrypt, and forwards traffic to the backend on port `8000`.

## Prerequisites & VPS Setup

### 1. Update OS Packages
Connect to your VPS via SSH and update the package repository:
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Docker & Docker Compose
Install the Docker engine and the compose plugin:
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg -y
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker packages:
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
```

Verify the installation:
```bash
docker --version
docker compose version
```

### 3. Configure Firewall (UFW)
Secure your server by allowing only SSH, HTTP, and HTTPS traffic:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

## Step-by-Step Deployment

### 1. Clone the Repository
Clone the codebase to your desired deployment directory on the VPS:
```bash
cd /opt
git clone https://github.com/degide/poultry-feed-formulation.git
cd poultry-feed-formulation
```

### 2. Configure Environment Variables
Create the production environment file for the backend:
```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Ensure the following variables are configured for production:
```ini
# Production environment overrides
ENVIRONMENT=development

# PostgreSQL
POSTGRES_USER=feed_user
POSTGRES_PASSWORD=feed_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=feed_formulation

# Security
SECRET_KEY=CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# NSGA-II defaults (server-side)
NSGA2_POPULATION_SIZE=150
NSGA2_MAX_GENERATIONS=500
```
*Replace dummy values and generate a cryptographic `SECRET_KEY` using `openssl rand -hex 32`.*

### 3. Launch the Containers
Build and start the services in detached mode:
```bash
docker compose up -d --build
```
This command starts:
*   `db` (PostgreSQL 16) mapped internally on port 5432.
*   `backend` (FastAPI Web API) listening on host port 8000.

Confirm the containers are running:
```bash
docker compose ps
```

### 4. Database Setup & Seeding
Once the PostgreSQL database container is healthy, run database migrations and seed the initial feed libraries and historical price logs:

```bash
# Run database migrations
docker compose exec backend alembic upgrade head

# Seed core ingredients library
docker compose exec backend python -m app.db.seed_ingredients

# Seed the historical price data (19k+ observations including local markets)
docker compose exec backend python -m app.db.seed_price_history
```


## SSL Certificate & Reverse Proxy (Nginx)

To secure the API endpoints, configure Nginx as a reverse proxy on the host machine to serve SSL traffic.

### 1. Install Nginx and Certbot
```bash
sudo apt install nginx certbot python3-certbot-nginx -y
```

### 2. Configure Nginx Block
Create a virtual host configuration file:
```bash
sudo nano /etc/nginx/sites-available/poultry_api
```

Add the configuration below, replacing `api.yourdomain.com` with your actual subdomain:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the configuration and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/poultry_api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Obtain SSL Certificate via Certbot
Run Certbot to request and configure a Let's Encrypt certificate:
```bash
sudo certbot --nginx -d api.yourdomain.com
```
Follow the interactive prompts to enable automatic redirection from HTTP to HTTPS.


## Monitoring & Maintenance

### 1. Viewing Container Logs
To inspect application runtime activity or troubleshoot errors, monitor the container logs:
```bash
docker compose logs -f backend
```

### 2. Automated Backups (PostgreSQL)
Set up a daily cron job to back up the PostgreSQL database schema and tables. 

Create a backup script at `/opt/backups/db_backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
FILE_NAME="pg_backup_$(date +%F_%T).sql"
docker exec -t $(docker ps -q -f name=db) pg_dumpall -U poultry_user > "$BACKUP_DIR/$FILE_NAME"
# Remove backups older than 14 days
find "$BACKUP_DIR" -type f -mtime +14 -delete
```
Make the script executable:
```bash
chmod +x /opt/backups/db_backup.sh
```
Configure a cron job using `crontab -e` to run the backup daily at midnight:
```cron
0 0 * * * /opt/backups/db_backup.sh
```
