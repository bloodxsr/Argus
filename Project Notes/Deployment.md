# AGRUS: Enterprise Deployment & Hosting Guide

This guide details exactly how to take the AGRUS platform from a local development environment to a production-grade cloud deployment.

## 1. System Architecture Overview

Before deploying, understand the 4 isolated pillars of AGRUS:
1. **The AI Engine (Python):** The heavy-lifter. Runs the PyTorch Foundation Model and handles inference. Needs a GPU instance for production latency.
2. **The Cloud Gateway (Go):** The high-concurrency router. Ingests millions of eBPF telemetry events, proxies API traffic, and queues requests for the Python AI.
3. **The Dashboards (React/Node):** The `report-website` and `test-website`. Built as static Vite bundles served by Express.
4. **The Sensor (Rust):** The eBPF kernel agent installed *only* on the client servers you are protecting.

---

## 2. Server Requirements & Setup

You will need a Cloud VPS or Bare-Metal Server (e.g., AWS EC2, DigitalOcean Droplet, RunPod).

### Minimum Specs for Inference (Running the AI)
*   **OS:** Ubuntu 22.04 LTS or Fedora Server
*   **GPU:** 1x NVIDIA RTX 3090, A100, or L40 (Must have 24GB+ VRAM for a 3B parameter model).
*   **RAM:** 32GB System RAM.
*   **Storage:** 100GB NVMe SSD.

### Step-by-Step Server Configuration
1. **Install NVIDIA Drivers & Docker Runtime:** You must install the `nvidia-container-toolkit` so Docker can access the GPU.
2. **Install Orchestration Tools:** Ensure `make` and `docker compose` (or `podman-compose`) are installed on the host.
3. **Clone the Repo:** Git clone this repository to the server.

---

## 3. Deploying the Cloud Platform

We have automated the entire deployment via the `Makefile`. 

1. SSH into your cloud server.
2. Navigate to the AGRUS repository.
3. Run the deployment command:
   ```bash
   make deploy
   ```

**What this does:**
* It builds the Go Gateway binary.
* It compiles the React frontends into optimized production builds.
* It boots the MongoDB database.
* It starts the Python `uvicorn` ASGI server.
* It networks them all together safely via Docker bridge networks.

### Exposing to the Internet (Nginx / Domain)
By default, the Go Gateway runs on port `8080`, and the websites on `4100` and `4200`. In a real cloud environment, you should place an **Nginx Reverse Proxy** in front of Docker and secure it with an SSL certificate using Let's Encrypt (`certbot`).

---

## 4. Deploying the Rust Sensors (To Client Servers)

You do **not** run the Rust sensor on your main AI hosting server. You install it on the servers you are trying to protect (e.g., a client's web server).

1. Compile the Rust binary for release on a Linux machine:
   ```bash
   cd agrus-sensor
   cargo build --release
   ```
2. Copy the resulting binary (`target/release/agrus-sensor`) to the client's Linux server.
3. Run it as a systemd background service as the root user (root is required to hook into eBPF kernel functions).

*Note: You will need to update the Go Gateway IP address inside the Rust source code before compiling so it knows where to send the telemetry.*

---

## 5. Training the Foundation Model (RunPod / AWS Cluster)

If you need to re-train or pre-train the 3-Billion Parameter model from scratch, do NOT run it on your standard web server.

1. Rent a multi-GPU cluster (e.g., 4x or 8x A100s on RunPod).
2. Clone the repository.
3. Install dependencies: `pip install -r requirements.txt` and `pip install accelerate transformers datasets`.
4. Configure your distributed environment:
   ```bash
   accelerate config
   ```
   *(Select "Multi-GPU" and follow the prompts).*
5. Execute the massive unified training script:
   ```bash
   accelerate launch train/train_agrus_foundation.py
   ```
This will automatically generate the synthetic Kali/Linux/Windows dataset, shuffle it, train the tokenizer, and distribute the Deep Learning PyTorch workload across all your GPUs.
