# 0017 Future Roadmap: Completing the AI-Native Security Pipeline

While the core sensors (eBPF/WMI), NATS event bus, Llama 3.1 8B inference engine, and auto-remediation PR pipelines are fully built and live, there are three major architectural pillars required to reach 100% parity with the "Next-Gen EDR/SOAR" vision.

Here is the exact to-do list to start building these features immediately.

---

## 1. Container Runtime Isolation
**Goal:** Enable the AI to physically isolate or kill compromised Docker/Kubernetes containers instead of just detecting them. Currently, eBPF sees the syscalls, but the AI lacks the "hands" to quarantine the container namespace.

**To-Do List:**
- [ ] **Docker Socket Integration (`ai/actions/container.py`)**
  - Use the Python `docker` library (`pip install docker`) to connect to `/var/run/docker.sock`.
  - Implement a `quarantine_container(container_id)` function that moves the container to a restricted Docker network (disconnects it from all other networks) to prevent lateral movement.
  - Implement a `kill_container(container_id)` function that stops and pauses the container for forensic analysis.
- [ ] **eBPF Container ID Extraction (`ebpf/src/main.rs`)**
  - Update the kernel eBPF tracepoints to capture the `cgroup` ID (which maps to the container ID) using `bpf_get_current_cgroup_id()`.
  - Pass the `cgroup_id` up through the `ProcessExecEvent` so the AI knows exactly *which* container the process belongs to.
- [ ] **Action Wiring (`ai/engine.py`)**
  - When the AI decision engine outputs the `quarantine_container` action, wire it to execute the new Python Docker scripts automatically (subject to `CompanyConstraints` approval).

## 2. UEBA (User & Entity Behavior Analytics)
**Goal:** Give the AI long-term memory of what is "normal" for every specific user, IP, and asset, rather than judging every event in isolation.

**To-Do List:**
- [ ] **MongoDB Timeseries Collection (`gateway/mongo.go` & `ai/mongo.py`)**
  - Create a new MongoDB collection called `entity_baselines`.
  - For every incoming event, aggregate the data: update the user's standard working hours, most common target IPs, and standard process executions.
- [ ] **Baseline Retrieval (`ai/retriever.py`)**
  - Before the AI analyzes an incident, query the `entity_baselines` collection for the specific `asset_id` or `uid`.
  - Calculate the deviation. For example, if the current event is at 3:00 AM but the user's baseline is 9:00 AM - 5:00 PM, flag `off_hours_deviation=True`.
- [ ] **Context Injection (`ai/prompts.py`)**
  - Add a new section to the prompt: `Entity Baseline Data: [User normally runs {process_list}, standard hours {hours}. Current deviation: {deviation}]`.
  - This allows the LLM to understand when an otherwise safe action (like SSH) is highly anomalous for that specific entity.

## 3. APT Event Correlation Engine
**Goal:** Catch slow, multi-stage attacks that happen over weeks by stitching together isolated events into a coherent "Attack Timeline" or incident graph.

**To-Do List:**
- [ ] **Graph Database or Relational Linking (`ai/correlation.py`)**
  - Build a module that subscribes to the `incidents.scored` NATS topic.
  - Instead of analyzing immediately, store the event and look for related recent events based on: `host_ip`, `uid`, or shared MITRE tactics.
- [ ] **Sliding Window Analysis**
  - Implement a sliding time window (e.g., 7 days). If a sequence of events maps to the MITRE kill chain sequentially (e.g., Initial Access -> Execution -> Persistence) on the same asset within 7 days, bundle them into a single `CorrelatedIncident`.
- [ ] **Multi-Event Prompting (`ai/engine.py`)**
  - Modify the AI input schema to accept a `list[IncidentContext]` representing a timeline, rather than a single `IncidentContext`.
  - Instruct the Llama model to assess the *sequence* of events as a whole to detect lateral movement.
