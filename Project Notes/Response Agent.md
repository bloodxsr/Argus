# Response Agent

Executes defensive actions determined by the Decision Engine.

## Related Notes
- [[Autonomous Response]]
- [[Decision Engine]]

---

## Operating Model: Human-on-the-Loop

The Response Agent does NOT mean no humans. It means:

```
High Risk   → Act first, human audits the action after
Medium Risk → Recommend action, human approves before execution
Low Risk    → Log only, human never sees it
```

Every automated action is logged with full audit trail. Humans review a digest at the end of each shift. If an action was wrong, the analyst marks it a false positive — this feeds directly into the Learning Agent.

---

## Action Categories

### Process Actions

```rust
// Kill a specific process
async fn kill_process(pid: u32, host: &str, ssh: &SshClient) -> ActionResult {
    let cmd = format!("kill -9 {}", pid);
    ssh.exec(host, &cmd).await
}

// Block an executable from running again
async fn block_executable(path: &str, host: &str, ssh: &SshClient) -> ActionResult {
    // Set immutable bit + remove execute permission
    let cmd = format!("chmod -x {} && chattr +i {}", path, path);
    ssh.exec(host, &cmd).await
}

// Disable a user account
async fn disable_account(username: &str, host: &str, ssh: &SshClient) -> ActionResult {
    let cmd = format!("usermod -L {}", username);
    ssh.exec(host, &cmd).await
}
```

### Network Actions

```rust
// Block an IP via iptables
async fn block_ip(ip: &str, host: &str, ssh: &SshClient) -> ActionResult {
    let cmd = format!(
        "iptables -I INPUT -s {} -j DROP && iptables -I OUTPUT -d {} -j DROP",
        ip, ip
    );
    ssh.exec(host, &cmd).await
}

// For Kubernetes environments — update NetworkPolicy
async fn update_network_policy(namespace: &str, blocked_ip: &str, k8s: &K8sClient) {
    // Patch NetworkPolicy to deny egress to blocked IP
    k8s.patch_network_policy(namespace, blocked_ip).await;
}
```

### Container Actions

```rust
// Pause container (suspend all processes, keep state)
async fn pause_container(container_id: &str, docker: &DockerClient) -> ActionResult {
    docker.pause_container(container_id).await
}

// Kill container (hard stop)
async fn kill_container(container_id: &str, docker: &DockerClient) -> ActionResult {
    docker.remove_container(container_id, true).await
}

// Isolate namespace — drop all network access
async fn isolate_container(container_id: &str, k8s: &K8sClient) -> ActionResult {
    // Apply deny-all NetworkPolicy to pod's namespace
    k8s.apply_deny_all(container_id).await
}
```

---

## Rollback Capability

Every action records a rollback command before executing.

```rust
struct ActionRecord {
    action_id: Uuid,
    incident_id: Uuid,
    action_type: ActionType,
    target: String,
    command_executed: String,
    rollback_command: String,   // stored before action runs
    timestamp: DateTime<Utc>,
    executed_by: String,        // "auto" or analyst username
    result: ActionResult,
}

// Example rollback entries
// kill_process: cannot un-kill, but records "process killed" for post-mortem
// block_ip: "iptables -D INPUT -s <ip> -j DROP"
// disable_account: "usermod -U <username>"
// pause_container: "docker unpause <id>"
```

Any analyst can trigger a rollback from the dashboard within 24 hours.

---

## Audit Log Schema

```sql
CREATE TABLE action_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id     UUID NOT NULL,
    action_type     VARCHAR(50),
    target          TEXT,
    host            VARCHAR(255),
    executed_by     VARCHAR(50),   -- 'auto' or analyst ID
    approved_by     VARCHAR(50),   -- NULL if auto
    command         TEXT,
    result          JSONB,
    rollback_cmd    TEXT,
    rolled_back     BOOLEAN DEFAULT FALSE,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Implementation — Action Executor

```rust
async fn execute_action(decision: &Decision, ctx: &ActionContext) -> ActionResult {
    // 1. Record intent before execution
    let record_id = log_action_intent(&decision, &ctx.db).await;

    // 2. Execute
    let result = match decision.action.as_str() {
        "kill_process"       => kill_process(ctx.pid, &ctx.host, &ctx.ssh).await,
        "block_ip"           => block_ip(&ctx.ip, &ctx.host, &ctx.ssh).await,
        "pause_container"    => pause_container(&ctx.container_id, &ctx.docker).await,
        "kill_container"     => kill_container(&ctx.container_id, &ctx.docker).await,
        "disable_account"    => disable_account(&ctx.user, &ctx.host, &ctx.ssh).await,
        _                    => ActionResult::Unknown,
    };

    // 3. Update record with result
    update_action_log(record_id, &result, &ctx.db).await;

    // 4. Publish action event for dashboard
    ctx.nats.publish("actions.completed", result.to_json()).await;

    result
}
```

---

## Scalability

- Response Agent connects to target hosts via SSH (short-lived connections, no persistent tunnel)
- For Kubernetes: uses in-cluster service account with RBAC-scoped permissions
- Action queue in NATS ensures no action is executed twice even if agent restarts
- Multiple Response Agent instances safe — each action is idempotent (killing an already-dead process is a no-op)
- At scale: region-specific Response Agents deployed near the infrastructure they manage
