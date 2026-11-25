---
title: "LoxiLB vs PureLB vs OpenELB in 2026: Which Bare-Metal Kubernetes Load Balancer Survives Production?"
date: "2026-11-25"
tags: ["kubernetes", "load-balancer", "bgp", "ebpf", "networking", "bare-metal"]
draft: false
cover: "/img/screenshots/openelb-architecture.jpg"
---

Every bare-metal Kubernetes cluster hits the same wall on day one: `type: LoadBalancer` creates a Service with `EXTERNAL-IP: <pending>` forever, because there is no cloud controller to hand out an address. MetalLB solved that years ago and became the default answer, but it only announces addresses — it does not add dataplane features, hardware offload, or per-service traffic policy. That gap is where LoxiLB, PureLB, and OpenELB compete.

Live project data for this comparison, pulled from GitHub on 2026-11-25:

| Project | Stars | Last push | License | Dataplane | IPv6 / dual-stack |
|---|---|---|---|---|---|
| **LoxiLB** (`loxilb-io/loxilb`) | **1,887** | 2026-11-24 | Apache-2.0 | eBPF (kernel) | Yes, dual-stack pools |
| **PureLB** (`purelb/purelb`) | **133** | 2026-11-16 | Apache-2.0 | IPVS + GoBGP | Yes, native dual-stack |
| **OpenELB** (`openelb/openelb`) | **1,768** | **2025-05-26** | Apache-2.0 | iptables/IPVS + GoBGP | Partial (`Eip` v4 pools) |
| MetalLB (`metallb/metallb`) — baseline | 8,415 | 2026-11-20 | Apache-2.0 | iptables/IPVS + FRR | Yes |

That last-push column is the single most important row in the table. OpenELB has not received a commit in roughly eighteen months. Its CRDs still work, but you are deploying a project that is effectively in maintenance freeze, which matters when a Kubernetes minor release breaks an admission webhook.

## Quick Verdict (TL;DR)

- **Choose LoxiLB** if throughput, DSR, or telco-style L4 features matter. It is the only one of the three with a genuine eBPF dataplane and active daily development. Deploy `kube-loxilb` in-cluster and `loxilb` as an external container on a spare node or VM.
- **Choose PureLB** if you want dual-stack IPv4/IPv6 with integrated BGP and a tiny operational footprint (one allocator Deployment plus one `lbnodeagent` DaemonSet). Best fit for small-to-medium clusters run by a team that reads logs for a living.
- **Choose OpenELB** only if you are already on KubeSphere, or you specifically need `Eip` + `BgpConf` resources managed from a UI. Weigh the dormancy risk explicitly.
- **Stay on MetalLB** if you need anycast/BGP announcement and nothing more; it has 4x the community of the next option and the most documentation.

## The Decision Matrix

| Your constraint | Pick | Why |
|---|---|---|
| 100 Gbit/s ingress, DSR required | **LoxiLB** | eBPF dataplane, no kube-proxy hairpin, direct server return |
| Small cluster, want dual-stack now | **PureLB** | Purpose-built dual-stack pools, minimal components |
| Existing KubeSphere install | **OpenELB** | Native integration, `Eip` managed by the platform |
| Only need ARP/BGP announcement | **MetalLB** | Largest community, simplest model, best docs |
| Need ECMP over BGP with FRR knobs | **MetalLB** | FRR integration is more mature than OpenELB's GoBGP |
| Air-gapped, no external LB VM allowed | **LoxiLB in-cluster mode** | Can run the dataplane inside worker nodes |
| Layer-2 only network (no BGP peering) | **MetalLB or PureLB** | Both do ARP/NDP announcement cleanly |

## LoxiLB — the eBPF Option

LoxiLB splits into two pieces, and understanding the split is the whole trick. `kube-loxilb` is a Deployment in `kube-system` that watches Services and programs load-balancer rules. `loxilb` itself is the packet-processing container, usually running **outside** the cluster on a spare node or VM, mirroring how a cloud provider keeps its LB out of the tenant cluster.

Install the controller from the project's own manifest:

```bash
wget https://github.com/loxilb-io/kube-loxilb/raw/main/manifest/ext-cluster/kube-loxilb.yaml
# edit the args block, then:
kubectl apply -f kube-loxilb.yaml
```

The args block is where every decision lives. These are the flags shipped in the manifest:

```yaml
        args:
            - --loxiURL=http://12.12.12.1:11111
            - --cidrPools=defaultPool=123.123.123.1/24
            #- --cidr6Pools=defaultPool=3ffe::1/96
            #- --monitor
            #- --setBGP=65100
            #- --extBGPPeers=50.50.50.1:65101,51.51.51.1:65102
            #- --enableBGPCRDs
            #- --setRoles=0.0.0.0
            #- --setLBMode=1
            #- --setUniqueIP=false
```

- `--loxiURL` points at the loxilb container's API (`:11111`). Get this wrong and Services stay pending with no error in the controller log worth reading.
- `--cidrPools` / `--cidr6Pools` define the address pools. A `/24` gives you 254 services per pool.
- `--setBGP=65100` enables announcement with a local ASN; pair it with `--extBGPPeers` to peer with your routers.
- `--setLBMode=1` selects the operating mode — the useful one for most on-prem setups, where loxilb handles the full NAT and the return path does not need to traverse the node again.
- `--setUniqueIP=false` lets several Services share one address (different ports), which is how you stretch a small public prefix.

Then run the dataplane container on the external node:

```bash
docker run -d --name loxilb --privileged --network host \
  -v /opt/loxilb/certs:/opt/loxilb/certs \
  ghcr.io/loxilb-io/loxilb:latest \
  --cloud=kubernetes
```

`--privileged` and `--network host` are not optional: the dataplane loads eBPF programs, manages interfaces, and needs the host network namespace to answer ARP/NDP for the pool addresses. If your security posture forbids privileged containers, LoxiLB is the wrong tool — do not try to work around it with a reduced capability set.

![kube-loxilb in-cluster topology](/img/screenshots/kube-loxilb-topology.jpg "kube-loxilb in-cluster topology, official diagram from the kube-loxilb repository")

Strengths that no other option here matches: **DSR (direct server return)**, per-service CT state handling in eBPF, and a dataplane that scales with cores because packet processing is not serialized through iptables chains. Weaknesses: operational complexity (two components, privileged container, external node or in-cluster DaemonSet), and documentation that assumes you already know what `--setLBMode` does.

## PureLB — Dual-Stack Without the Ceremony

PureLB ships two components: an **allocator** Deployment that hands out addresses and a **lbnodeagent** DaemonSet that programs the nodes. It integrates **GoBGP** for announcement — the Helm chart ships GoBGP RBAC and a metrics Service, so the routing daemon is part of the deployment, not an external dependency you assemble yourself.

Address pools live in a `ServiceGroup` custom resource (`purelb.io/v2`). This is the project's own sample:

```yaml
---
apiVersion: purelb.io/v2
kind: ServiceGroup
metadata:
  name: default
  namespace: purelb-system
spec:
  local:
    v4pools:
    - subnet: 192.168.254.0/24
      pool: 192.168.254.230/32
      aggregation: default
    - subnet: 192.168.254.0/24
      pool: 192.168.254.231-192.168.254.240
      aggregation: default
    v6pools:
    - subnet: fd53:9ef0:8683::/120
      pool: fd53:9ef0:8683::-fd53:9ef0:8683::3
      aggregation: default
```

Note the structure: `v4pools` and `v6pools` are **separate lists of the same object**, with three pool syntaxes supported — single address (`/32`), CIDR, and explicit ranges. Each entry carries a `subnet` (the on-link network the address belongs to) and an `aggregation` name, which controls ARP/NDP announcement behaviour. This is the cleanest dual-stack model of the three projects, and for a cluster that must serve both families it removes the usual "one more controller for IPv6" step.

Install from the chart in the repository:

```bash
git clone https://github.com/purelb/purelb
helm install purelb ./purelb/build/helm/purelb \
  -n purelb-system --create-namespace
```

The `ServiceGroup` above is `local` mode — PureLB announces addresses on the node's own interfaces. BGP mode uses a `bgp` section in the same `ServiceGroup`, with the peers and ASN defined there; the allocator then programs the embedded GoBGP instance rather than answering ARP.

The honest trade-off: **133 stars and a very small maintainer pool**. The code is clean, the design is right, and releases are current (2026-11-16), but the community is thin enough that you should expect to read the source when something goes wrong. If your team cannot do that, pick MetalLB.

## OpenELB — KubeSphere's Load Balancer, Now Dormant

OpenELB installs a controller, a speaker, and an admission webhook, plus three CRDs: `Eips`, `BgpConfs`, and `BgpPeers`. The full manifest is a single apply:

```bash
kubectl apply -f https://raw.githubusercontent.com/openelb/openelb/master/deploy/openelb.yaml
```

That manifest creates the `openelb-system` namespace, all three CRDs, three ServiceAccounts (`openelb-controller`, `openelb-speaker`, `openelb-admission`), and the corresponding RBAC — so one file gives you the whole control plane.

Address pools are `Eip` resources:

```yaml
apiVersion: network.kubesphere.io/v1alpha2
kind: Eip
metadata:
  name: eip-pool
spec:
  address: 192.168.0.100-192.168.0.110
  protocol: layer2
  disable: false
```

`protocol: layer2` announces via ARP/NDP; `protocol: bgp` hands announcement to the speaker's GoBGP instance. For BGP you also need a `BgpConf` describing the local router — its CRD requires exactly three fields:

```yaml
apiVersion: network.kubesphere.io/v1alpha2
kind: BgpConf
metadata:
  name: default
spec:
  as: 65000
  port: 179
  routerID: 10.0.0.1
```

Three required fields, all validated by the CRD schema (`as` and `port` as int32 with `port` bounded 1-65535, `routerID` matched against an IPv4 pattern). Peers go in separate `BgpPeer` resources.

![OpenELB architecture](/img/screenshots/openelb-architecture.jpg "OpenELB node architecture, official diagram from the openelb repository")

The layer-2 mode is genuinely easy, and the KubeSphere integration is real. But the repository's last push is **2025-05-26**, and the Kubernetes ecosystem moves faster than that. An admission webhook that worked against Kubernetes 1.31 is exactly the kind of component that breaks on 1.34 without anyone noticing until a Service fails to allocate. Treat OpenELB as a stable-but-frozen component: pin your Kubernetes version, test upgrades in staging, and have a migration path to MetalLB or PureLB written down before you need it.

## Where MetalLB Still Wins

For announcement-only use cases — one flat L2 segment, BGP to a pair of routers, no DSR, no offload — MetalLB remains the right answer: **8,415 stars**, an FRR-based BGP implementation that is more configurable than OpenELB's, a `MetalLB`-specific `IPAddressPool`/`L2Advertisement`/`BGPAdvertisement` model that maps closely to how network engineers think, and the largest body of operational knowledge. Our [MetalLB vs kube-vip vs Cilium comparison](../2026-04-26-metallb-vs-kube-vip-vs-cilium-lb-bare-metal-kubernetes-load-balancer-guide/) covers that baseline in depth, including the ARP-speaker leader-election behaviour that surprises people during node drains.

If you are peering with real routers, the [BGP route reflector guide](../2026-05-12-self-hosted-bgp-route-reflector-frr-bird-gobgp-guide/) explains the iBGP topologies these controllers assume, and the [CNI comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) covers whether your pod network can even carry the traffic your LB will hand it.

## Pitfalls That Break Bare-Metal Deployments

- **`--privileged` is not negotiable for LoxiLB.** It loads eBPF programs and manipulates host interfaces. Dropping capabilities produces a container that starts and silently forwards nothing.
- **BGP ASN or router ID mismatch fails silently.** The session stays `Active` or `Connect` and Services show an external IP that nothing routes to. Check the session state on the router, not on the cluster.
- **`externalTrafficPolicy: Local` plus a single-speaker setup drops traffic.** With Local, only nodes running a backend answer; if your speaker announces from a node with no endpoints, clients get timeouts.
- **Pool overlaps with the node subnet cause ARP conflicts.** Every pool address must be outside the DHCP range and outside any address the nodes themselves use.
- **Two LB controllers on one cluster fight over Services.** Set `loadBalancerClass` explicitly. LoxiLB, MetalLB, and PureLB all support class-based selection, and running two without it produces flapping addresses.
- **OpenELB's freeze is a real risk, not a footnote.** An eighteen-month-old admission webhook against a fast-moving API server is a latent upgrade failure.

## FAQ

**Can I run LoxiLB, PureLB, or OpenELB without BGP?**
Yes. All three support layer-2 announcement via ARP/NDP, which needs no router configuration — LoxiLB through its L2 mode, PureLB through `local` ServiceGroups, OpenELB through `protocol: layer2` in an `Eip`. BGP becomes necessary when you need ECMP across multiple nodes or when the LB node is not on the same segment as the clients.

**Which one handles IPv6 dual-stack best?**
PureLB. Its `ServiceGroup` treats `v4pools` and `v6pools` as first-class siblings in the same object, so a single resource defines both families. LoxiLB supports dual-stack through separate `--cidrPools` and `--cidr6Pools` flags, which works but splits configuration across two places. OpenELB's `Eip` model is primarily IPv4-oriented.

**Do I need to remove kube-proxy to use these?**
No. LoxiLB can bypass kube-proxy in its eBPF path for performance, but it does not require its removal. PureLB and OpenELB rely on the standard Service machinery and expect kube-proxy (or a CNI's replacement) to remain in place.

**What is the actual difference between DSR and the usual NAT return path?**
With the default NAT behaviour, return traffic from the pod goes back through the LB node, doubling bandwidth on that node and adding a hop. With DSR, the LB rewrites only the destination on ingress and the pod answers directly to the client, so the LB node only handles inbound packets. That is the main reason to choose LoxiLB over MetalLB at high throughput.

**Is a 133-star project safe to run in production?**
PureLB's design is small and the components are easy to reason about: an allocator plus a per-node agent, both stateless enough to restart. The risk is maintainer bandwidth, not architecture. If your team can read Go and you pin versions, it is defensible for a mid-size cluster. If you need vendor-grade support and a large user base, MetalLB is the conservative choice.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "LoxiLB vs PureLB vs OpenELB in 2026: Which Bare-Metal Kubernetes Load Balancer Survives Production?",
  "description": "Comparison of LoxiLB, PureLB and OpenELB bare-metal Kubernetes load balancers in 2026: eBPF dataplane, dual-stack pools, BGP configuration, real manifests and production pitfalls.",
  "datePublished": "2026-11-25",
  "dateModified": "2026-11-25",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
