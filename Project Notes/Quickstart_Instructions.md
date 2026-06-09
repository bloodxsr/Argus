# AGRUS Quickstart: What to do and when

This is the exact sequence of steps to boot up, test, and present the AGRUS platform.

---

## Phase 1: Boot the Cloud Platform (Do this right now)
You must spin up the backend gateways, the AI service, and the front-end dashboards before anything else can happen.

1. Open your terminal in the root `AGRUS` project folder.
2. Run the deployment orchestrator:
   ```bash
   make deploy
   ```
3. **What happens?** Docker will build the Go API Gateway, the Python AI Engine, the MongoDB database, and the two React Websites, running them all seamlessly in the background.

---

## Phase 2: Open the Dashboards (To view the platform)
Once the platform is running (Phase 1), you can access the beautiful UI.

1. **The SOC Report Dashboard:** Open your browser to `http://localhost:4200`
   * *Purpose:* This is the main screen for the cybersecurity team. It shows Active problems (waiting for human review) and Solved problems (neutralized by AI).
2. **The Attack Simulator:** Open your browser to `http://localhost:4100`
   * *Purpose:* This allows you to inject fake cyberattacks into the system to test the AI.

---

## Phase 3: Simulate an Attack (To see the AI in action)
Because we don't have real hackers attacking your laptop right now, you need to simulate an attack to see data populate on the SOC Dashboard.

1. Go to the Attack Simulator (`http://localhost:4100`).
2. Select an attack from the dropdown (e.g., "RCE With C2 Beacon").
3. Click **"Simulate Attack"**.
4. **What happens?** The Go Gateway receives the fake telemetry and instantly routes it to the Python AI. The AI processes the attack, makes a decision based on the Blast Radius constraints, and saves it to MongoDB.
5. Go back to the SOC Report Dashboard (`http://localhost:4200`) and watch the new Incident Report instantly appear!

---

## Phase 4: Deploy the Rust Sensors (Optional / Enterprise Only)
If you were deploying this for a real Fortune 500 company, you would need to install the sensor on their actual servers to get real data (instead of using the Attack Simulator).

1. Go into the `agrus-sensor` folder.
2. Run `cargo build --release` to compile the Rust binary.
3. Move that binary to the client's Linux server and run it. It will hook into the Linux Kernel (eBPF) and automatically stream real attacks to your Go Gateway!

---

## Phase 5: Train the 3-Billion Parameter Model (Future Step)
Right now, the Python engine is running a lightweight, local logic prototype. To actually inject the massive, 3-Billion parameter Deep Learning brain into the system, you must rent a GPU cluster.

1. Rent a GPU instance (e.g., RunPod or AWS).
2. Install the repository.
3. Run the massive unified training script:
   ```bash
   python train/train_agrus_foundation.py
   ```
4. **What happens?** This single script will generate thousands of Windows and Linux hacker commands, shuffle them, train the BPE tokenizer, initialize the 3B PyTorch Transformer, and run the Deep Learning training loop. 
5. When it finishes, you point the `security-ai` Python service to the newly trained model weights, and your platform becomes vastly more intelligent!
