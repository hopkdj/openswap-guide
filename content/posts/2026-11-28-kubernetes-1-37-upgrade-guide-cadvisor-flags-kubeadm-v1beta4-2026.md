---
title: "Kubernetes 1.37 Upgrade Guide 2026: The cAdvisor Flags That Stop kubelet From Booting"
date: "2026-11-28"
tags: ["kubernetes", "upgrade", "self-hosted", "kubeadm", "migration"]
draft: false
cover: "/img/screenshots/k8s-137-upgrade.jpg"
---

Kubernetes 1.37 shipped on **26 August 2026**, and it contains a change that is qualitatively different from the usual deprecation cycle: **the kubelet will refuse to start** if you still pass certain cAdvisor flags. Not warn. Not log. Exit.

That matters right now because two support deadlines have already passed and a third is weeks away. **1.33 went end of life on 28 June 2026. 1.34 followed on 27 October 2026.** And **1.35's support window closes on 28 December 2026** — roughly one month from today. If you are on any of those three, you are either unsupported or about to be, and the upgrade you are about to run has a boot-blocking landmine in it.

This is the runbook I would use: the exact removals in 1.37, the version skew rules that decide your upgrade order, and the flags to grep for *before* you drain a node.

## TL;DR: The Quick Verdict

**Upgrade to 1.37.3, and grep your kubelet configuration for cAdvisor flags before you touch anything.** The removal of ~20 legacy cAdvisor flags means a node whose systemd unit still carries `--container-hints` or `--boot-id-file` comes back from the upgrade and fails to start — which turns a rolling upgrade into a fleet outage if your automation does not catch it.

**Control plane one minor at a time; nodes can skip.** kubeadm refuses to jump minors on the control plane, but you do not need to walk worker nodes through every version. **If you are on 1.34 or older, do not "upgrade" — plan a two-step migration**, because 1.34 is out of support and the intervening removals have already accumulated.

## Kubernetes release and support status, November 2026

| Release | Released | Latest patch | Support until | End of life | Verdict |
|---|---|---|---|---|---|
| **1.37** | 2026-08-26 | **1.37.3** | 2027-08-28 | 2027-10-28 | **Target this** |
| 1.36 | 2026-04-22 | 1.36.7 | 2027-04-28 | 2027-06-28 | Fine for a quarter |
| 1.35 | 2025-12-17 | 1.35.11 | **2026-12-28** | 2027-02-28 | **One month left** |
| 1.34 | 2025-08-27 | 1.34.13 | 2026-08-27 | **2026-10-27 (EOL)** | Unsupported |
| 1.33 | 2025-04-23 | 1.33.13 | 2026-04-28 | **2026-06-28 (EOL)** | Unsupported five months |
| 1.32 | 2024-12-11 | 1.32.13 | 2025-12-28 | 2026-02-28 | Long dead |

The project is enormous and moving fast: **129,257 stars**, last push **27 November 2026**. That velocity is why the support window is only about 14 months per minor. Kubernetes does not have an LTS. There is no version you install and forget for three years — the cadence is three minors a year, and staying supported means upgrading roughly annually at minimum.

### The version skew rules that decide your order

Before planning the sequence, know the constraints, because they are not negotiable and they dictate everything:

- **kube-apiserver must never be older than any other component.** It is upgraded first, always.
- **kubelet may trail the API server by up to three minor versions** under the current skew policy. This is what lets you skip minors on worker nodes.
- **kubectl may trail by one minor version.** A 1.37 cluster with a 1.35 `kubectl` will produce strange validation errors.
- **kube-controller-manager and kube-scheduler must not exceed the API server's version**, and are upgraded alongside it.

The practical consequence: control plane 1.36 → 1.37, then nodes can go straight from 1.36 to 1.37 — but you cannot leave a node on 1.34 while the control plane runs 1.37, because that is three minors of skew *and* 1.34 is unsupported.

## What actually breaks in 1.37

### 1. The kubelet cAdvisor flag removal (the boot blocker)

The kubelet's embedded cAdvisor was swapped for a leaner library module, and with it went a set of flags that had been deprecated for years. **Only `--housekeeping-interval` survives.** If configured, any of the following now cause kubelet to fail startup:

```text
--application-metrics-count-limit   --boot-id-file
--container-hints                   --containerd
--containerd-namespace              --enable-load-reader
--event-storage-*                   (and the remaining legacy cAdvisor set)
```

Two data surfaces were removed alongside the flags:

- **Application and custom metrics are no longer collected.** The `userDefinedMetrics` field in `/stats/summary` is gone, and so are the `container_application_*` metric families in `/metrics/cadvisor`.
- **Three metrics are no longer exported:** `container_cpu_load_average_10s`, `container_cpu_load_d_average_10s`, and `container_tasks_state`.

That last point is the quiet one. Any dashboard, alert rule, or recording rule referencing `container_tasks_state` now returns nothing — not an error, just an empty graph. Check your Prometheus rules before the upgrade, not after, or you will discover it during the incident that needed the graph.

### 2. kubeadm `v1beta3` is removed

kubeadm's `v1beta3` API, deprecated since 1.31, is gone in 1.37. If your cluster configuration files, GitOps repo, or Terraform module still emit `apiVersion: kubeadm.k8s.io/v1beta3`, `kubeadm upgrade` fails at parse time.

Migrate with the 1.35 binary **before** upgrading past it:

```bash
kubeadm config migrate --old-config kubeadm-config.yaml \
  --new-config kubeadm-config-v1beta4.yaml
```

`v1beta4` is the current schema. Note the ordering trap: the migration has to happen while you still have a binary that understands both schemas. Once you are on 1.37, `kubeadm config migrate` has nothing to read.

### 3. Feature gates removed outright

These gates are deleted, so setting them in `--feature-gates` is itself an error:

| Removed gate | Replacement or note |
|---|---|
| `AnyVolumeDataSource` | GA and locked since 1.33 |
| `GangScheduling` | Use `GenericWorkload` |
| `WorkloadAwarePreemption` | Use `GenericWorkload` |
| `SidecarContainers` | Unconditionally enabled since 1.33 |
| `PreventStaticPodAPIReferences` | Behavior now unconditional |
| `NodeLocalCRISocket` (kubeadm) | GA in a prior release |
| `RelaxedDNSSearchValidation` | Removed |
| `RetryGenerateName`, `BtreeWatchCache`, `OrderedNamespaceDeletion`, `APIServerTracing`, `ResilientWatchCacheInitialization`, `ConsistentListFromCache` | Removed locked GA gates |
| `StreamingCollectionEncodingToJSON` / `ToProtobuf` | Removed locked GA gates |

If you manage cluster config declaratively and pin gates "just in case," this is the list that breaks your apply.

### 4. API and behavior changes that affect live workloads

- **`PodStatusResult` is removed from the API.** Unused since 2015, no REST endpoint — but typed client code that references it fails to compile against the 1.37 client libraries.
- **Pod-level resource QoS calculation changed.** Pod resources now determine QoS only when they include an actual request or limit. Empty containers (`{}`, `{requests:{}}`, `{limits:{}}`) no longer influence QoS. A pod that was previously `Burstable` by accident can become `BestEffort` — which changes its eviction priority under node pressure.
- **Pod Certificates went GA**, and the `PKIXPublicKey` and `ProofOfPossession` fields were removed from `PodCertificateRequest` `v1`. Clients setting them must be updated first.
- **`--concurrent-service-syncs` removed** from kube-controller-manager (a no-op since 1.31).
- **Deprecated `apiserver_cache_list_*` metrics are no longer exposed by default.** Migrate to `apiserver_storage_list_*` with `storage="watchcache"`.
- **Go 1.27's header limit hit impersonation.** The API server now accepts up to 16,384 request header values, because Go's default of 500 returns HTTP 431 for proxied or impersonated users carrying ~500 or more groups. If you use group-heavy RBAC with impersonation, this release fixes you — but it also means the old behavior is gone for good.

### 5. kube-proxy IPVS is on the way out

IPVS mode has been deprecated since **1.35**, and nftables mode went GA back in **1.33**. kubeadm now emits a delayed warning recommending nftables on newer kernels. This is not a 1.37 break, but it is the release where ignoring it stops being reasonable — the migration is a rebuild of the service proxy, and doing it during a version upgrade is how you end up debugging two variables at once.

## The upgrade sequence

This is the order that respects every skew rule above. Control plane first, one minor at a time.

### Step 0: inventory the landmines

```bash
# cAdvisor flags present anywhere in kubelet config or unit files?
sudo grep -rE "application-metrics-count-limit|boot-id-file|container-hints|enable-load-reader" \
  /var/lib/kubelet/ /etc/kubernetes/ /etc/systemd/system/kubelet.service.d/ 2>/dev/null

# kubeadm config API version
sudo kubectl -n kube-system get cm kubeadm-config -o yaml | grep apiVersion

# metrics that 1.37 stops exporting
grep -rE "container_tasks_state|container_cpu_load_average_10s|container_application_" \
  /path/to/prometheus/rules/
```

If the first grep returns anything, fix it before proceeding. Removing a flag is a config change; discovering it after `systemctl restart kubelet` is an outage.

### Step 1: control plane

```bash
# 1.35 -> 1.36 -> 1.37, one minor per apply
sudo kubeadm upgrade plan
sudo kubeadm upgrade apply v1.37.3
```

`kubeadm upgrade apply` will refuse a multi-minor jump on the control plane. That refusal is correct — do not script around it by editing version strings.

### Step 2: worker nodes, one at a time

```bash
# on the control plane
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data

# on the node
sudo apt-mark unhold kubeadm kubelet kubectl
sudo apt-get install -y kubeadm=1.37.3-1.1 kubelet=1.37.3-1.1 kubectl=1.37.3-1.1
sudo apt-mark hold kubeadm kubelet kubectl
sudo kubeadm upgrade node
sudo systemctl daemon-reload && sudo systemctl restart kubelet
sudo systemctl status kubelet --no-pager

# back on the control plane
kubectl uncordon node-1
```

Verify `kubelet` is `active (running)` **before** uncordoning. If it exits immediately, you hit the cAdvisor flag removal — check `journalctl -u kubelet -n 50` for `unknown flag`.

### Step 3: verify the whole fleet

```bash
kubectl get nodes -o wide
kubectl version --output=yaml | grep -E "gitVersion|minor"
kubectl get --raw /metrics | grep -c container_application_
```

The last command should return `0`. If it returns a count, you are looking at a node that has not actually restarted onto the new kubelet.

## Pitfalls that turn a rolling upgrade into a fleet outage

**Draining without `--delete-emptydir-data` hangs forever.** Pods using `emptyDir` block eviction by default. This is the single most common reason a drain "hangs" and someone escalates at 2 a.m.

**PDBs with `minAvailable` equal to replica count deadlock the drain.** If a Deployment has 2 replicas and a PodDisruptionBudget of `minAvailable: 2`, no pod can ever be evicted. Fix the budget before the window, not during.

**Upgrading the control plane while an old kubelet streams is fine; the reverse is not.** kubelet must never be newer than the API server. On a self-managed cluster the API server is upgraded first by construction — but if you use a managed control plane with a delayed upgrade, check its version before touching nodes.

**etcd is the actual risk surface.** A control plane upgrade rewrites etcd's data through the new API server. Take a verified snapshot immediately before `kubeadm upgrade apply`, and confirm the snapshot restores — an untested etcd backup is a hope, not a rollback plan.

**`--feature-gates` reordering is silent until it fails.** Deleting a removed gate from your config is mandatory; leaving it produces a hard error at `kubeadm upgrade apply`, which is a good failure — but only if your config is in version control where you can see it.

**The Go 1.27 header limit change cuts both ways.** If you proxy authentication and stuff groups into headers, 1.37's raised limit helps. If you wrote custom middleware assuming a 500-header ceiling, that assumption is now wrong.

## Why run your own control plane at all?

Because the version you run is the version you chose. Managed Kubernetes hands you whatever the provider supports on the provider's timeline — and when a minor goes out of support, your only levers are "accept their forced upgrade" or "migrate clusters." A self-managed cluster lets you sit on 1.36 for a quarter while you clean up the cAdvisor flags and dashboard rules, which is the difference between a planned Saturday and an unplanned one.

If you are weighing provisioning tools before this upgrade, our [kOps vs KubeOne vs kubeadm comparison](../2026-05-17-self-hosted-kubernetes-cluster-provisioning-kops-vs-kubeone-vs-kubeadm-guide/) covers which of them actually let you control version cadence, the [etcd backup and disaster recovery guide](../2026-05-02-etcd-backup-disaster-recovery-complete-guide-2026/) is the prerequisite reading for any control plane upgrade, and the [Rancher vs Kubespray vs kind comparison](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) covers the higher-level management layers that automate exactly this runbook.

## FAQ

**Is Kubernetes 1.34 still supported?**
No. 1.34 reached end of life on **27 October 2026**, and 1.33 on **28 June 2026**. Neither receives patches, including security fixes. Supported releases as of November 2026 are 1.35, 1.36, and 1.37 — and 1.35's support ends on 28 December 2026.

**Why does kubelet fail to start after upgrading to 1.37?**
Because the embedded cAdvisor was replaced with a leaner library and roughly twenty legacy flags were removed — only `--housekeeping-interval` remains. A kubelet unit or config still passing `--container-hints`, `--boot-id-file`, `--containerd`, or similar will exit with an unknown-flag error. Remove those flags before restarting kubelet.

**Can I skip minor versions when upgrading Kubernetes?**
On worker nodes, yes — kubelet may trail the API server by up to three minors, so a 1.36 node can go to 1.37 directly. On the control plane, no: `kubeadm upgrade apply` requires one minor at a time, and that restriction exists because control plane components have strict version coupling.

**Which metrics disappear in 1.37?**
`container_cpu_load_average_10s`, `container_cpu_load_d_average_10s`, and `container_tasks_state` are no longer exported from `/metrics/cadvisor`. Application and custom metrics are gone entirely: the `userDefinedMetrics` field in `/stats/summary` and the `container_application_*` families are removed. Update dashboards and recording rules before upgrading.

**What happens to kubeadm `v1beta3` configuration?**
It is removed in 1.37. Convert with `kubeadm config migrate` using a 1.35 or 1.36 binary, producing a `v1beta4` config, before you upgrade past those versions. After upgrading to 1.37, the old schema has no reader.

**Do I need to upgrade kube-proxy IPVS to nftables in this release?**
Not required by 1.37, but IPVS has been deprecated since 1.35 and nftables has been GA since 1.33. Do it as its own change, not bundled with a version upgrade — otherwise you cannot tell which change caused a networking regression.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kubernetes 1.37 Upgrade Guide 2026: The cAdvisor Flags That Stop kubelet From Booting",
  "description": "A production Kubernetes 1.37 upgrade guide covering the removed cAdvisor kubelet flags, the kubeadm v1beta3 removal, version skew rules, the full upgrade sequence, and the pitfalls that turn a rolling upgrade into a fleet outage.",
  "datePublished": "2026-11-28",
  "dateModified": "2026-11-28",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
