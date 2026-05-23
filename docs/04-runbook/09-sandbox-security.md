# 13 — Sandbox Security

## Threat model

Evaluator runs untrusted or semi-trusted model-generated code. The sandbox must assume code can attempt:

- network exfiltration;
- filesystem writes;
- process spawning;
- fork bombs;
- CPU/memory exhaustion;
- reading secrets;
- modifying evaluator files;
- hiding malicious behavior in tests.

## MVP sandbox

Use Docker with:

- no network;
- read-only root filesystem;
- writable tmpfs only;
- memory limit;
- CPU limit;
- PID limit;
- no new privileges;
- cap drop all;
- hard timeout;
- max file size ulimit;
- no mounted secrets.

## Example policy

```yaml
network_mode: none
read_only: true
tmpfs:
  - /tmp:size=100M
mem_limit: 512m
cpus: 1.0
pids_limit: 50
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true
ulimits:
  nofile: 1024
  fsize: 10485760
```

## Future hardening

| Stage | Runtime |
|---|---|
| v0.1 | Docker rootless |
| v0.3 | gVisor or Kata Containers |
| v1.0 | Firecracker microVM |
| Enterprise | per-run ephemeral VM |

## Rule

Community-submitted evaluators must never run directly on the host. They must pass static inspection and execute only inside sandbox.
