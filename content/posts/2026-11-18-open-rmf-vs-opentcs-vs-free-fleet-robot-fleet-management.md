---
title: "Open-RMF vs openTCS vs Free Fleet in 2026: Self-Hosted Robot Fleet Management Compared"
date: "2026-11-18"
tags: ["robotics", "self-hosted", "automation", "ros2", "comparison"]
draft: false
cover: "/img/screenshots/open-rmf-dashboard.jpg"
description: "A hands-on comparison of Open-RMF, openTCS and Free Fleet for self-hosting a fleet of AGVs or mobile robots in 2026 — traffic control, dispatch, VDA5050 support and real deployment configs."
---

Your warehouse has twelve AMRs, four different vendors, and one spreadsheet that decides which robot gets which aisle. It works — until two vehicles deadlock in the same corridor at 2 a.m. and the pick line stops. Single-robot navigation stacks like Nav2 solve the "drive from A to B" problem; they do not solve the "coordinate a dozen robots that all want the same corridor" problem. That is a traffic-control problem, and it is the exact gap that fleet management software fills.

The three credible open-source options in 2026 are **Open-RMF** (Open Robotics / Intrinsic), **openTCS** (Fraunhofer IML) and **Free Fleet** (part of the Open-RMF ecosystem). They look similar on a feature slide and behave very differently in production. This guide compares them on architecture, protocol support, deployment effort and the operational traps nobody documents.

## TL;DR: The 30-Second Verdict

- **Building a multi-vendor AGV fleet in a warehouse or hospital?** Choose **Open-RMF**. It is the only one with a real traffic scheduler that negotiates reservations between robots from different vendors, plus a browser dashboard your operations team can actually use.
- **Integrating VDA5050 vehicles from industrial suppliers?** Choose **openTCS**. VDA5050 support is built into the kernel, the dispatcher is mature, and the Fraunhofer maintainership means the routing model matches how real AGV projects are planned.
- **Already running ROS 2 Nav2 robots and only need a thin multi-robot adapter layer?** Choose **Free Fleet**. It is not a full fleet manager — it is the glue that lets one Zenoh-based fleet adapter talk to many Nav2 robots across hosts, with almost zero integration work.

If you want one sentence: **Open-RMF coordinates, openTCS dispatches, Free Fleet connects.** Confusing those three verbs is the most common architectural mistake in this space.

## Feature and Architecture Comparison

| Dimension | Open-RMF | openTCS | Free Fleet |
|---|---|---|---|
| Maintainer | Open Robotics / Intrinsic | Fraunhofer IML | Open-RMF project |
| License | Apache-2.0 | MIT (docs CC-BY-4.0) | Apache-2.0 |
| Runtime | ROS 2 (Humble, Jazzy) | Java 21 (JVM, no ROS needed) | ROS 2 + Zenoh bridge |
| Core abstraction | Traffic schedule + task dispatch | Kernel with routing, dispatching, scheduling modules | Fleet adapter + robot client |
| Multi-vendor support | Yes, via fleet adapters per vendor | Yes, via communication adapters (drivers) | Mostly ROS 2 / Nav2 robots |
| VDA5050 | Via community adapter | **Built in** | No |
| Web UI | Yes — `rmf-web` dashboard | Desktop clients (Plant Overview, Operations Desk) | No UI (use RViz or your own) |
| Official container images | `ghcr.io/open-rmf/rmf_demos` | No official image (build from source) | `ghcr.io/open-rmf/free_fleet/*` |
| GitHub stars | 467 (root repo) | 607 | 252 |
| Last commit | 2026-11-12 | 2026-09-17 | 2026-10-21 |
| Learning curve | Steep (ROS 2 + RMF concepts) | Moderate (Java, config-heavy) | Low (if you live in ROS 2) |

Star counts and last-commit dates were pulled live from GitHub at publish time — check them again before you commit to a stack, because all three projects move fast.

## Decision Matrix: Match the Tool to the Job

| Your situation | Recommended tool | Why |
|---|---|---|
| 5+ robots, mixed vendors, shared corridors | Open-RMF | Reservation-based traffic scheduling prevents deadlocks across vendors |
| Industrial AGVs with VDA5050 interfaces | openTCS | Protocol support in the kernel, no adapter code required |
| Hospital / lab logistics with elevators and doors | Open-RMF | Has explicit door, lift and dispenser integrations |
| Single-vendor fleet, simple loop routes | openTCS | Lower runtime overhead than a full ROS 2 graph |
| Prototype fleet of 2-3 Nav2 robots | Free Fleet | Fastest path from `ros2 launch` to multi-robot operation |
| Fleet across multiple physical hosts or subnets | Free Fleet | Zenoh router bridges DDS domains cleanly |
| You need an operator-facing dashboard on day one | Open-RMF | `rmf-web` ships a usable task and fleet view |

## Open-RMF: The Traffic Coordinator

Open-RMF treats a fleet as a scheduling problem. Its `rmf_traffic` library maintains a distributed schedule of space-time reservations: every robot asks for a corridor segment during a time window, and the schedule either grants it or makes the robot wait. Intersections are negotiated, not guessed. On top of that, `rmf_task` handles task bidding — a delivery job is offered to fleet adapters, and the adapter that can serve it cheapest wins.

The pieces you deploy:

- `rmf_traffic` — schedule database and conflict resolution
- `rmf_task` — task dispatch and bidding
- `rmf_demos` — reference deployments (office, airport terminal, hotel)
- `rmf-web` — the dashboard, API server and React front end

The fastest way to see it running is the official demo image, which bundles Gazebo Sim, the RMF core and a pre-built office world:

```bash
docker run -it --rm --net=host \
  ghcr.io/open-rmf/rmf_demos/rmf_demos:humble \
  ros2 launch rmf_demos_gz office.launch.xml

# In a second terminal, bring up the dashboard stack
docker run -it --rm --net=host \
  ghcr.io/open-rmf/rmf-web/api-server:humble
```

![Open-RMF web dashboard showing live robot positions and task queue](/img/screenshots/open-rmf-dashboard.jpg "Open-RMF rmf-web dashboard with live fleet state")

Once you move past the demo, the real work begins: writing a **fleet adapter** for each robot vendor. The adapter is a ROS 2 node that translates between RMF's `RobotCommand`/`RobotState` messages and your vendor's API. Budget two to four weeks per vendor protocol, more if the vendor's API has no state feedback. That adapter cost is the single biggest reason RMF projects stall.

**Where it hurts:** the ROS 2 dependency chain is deep, and version skew between the RMF release and your ROS 2 distribution causes most build failures. Pin your ROS 2 distro and use the matching RMF branch; mixing Jazzy RMF with Humble Nav2 will cost you a weekend.

## openTCS: The Industrial Dispatcher

openTCS is a different lineage entirely. It is a Java 21 application from Fraunhofer IML, designed by people who plan real AGV installations. The kernel owns the plant model — points, paths, locations, vehicles, links — and runs pluggable routing, dispatching and scheduling strategies on top of it.

Because it is JVM-based, it deploys without a ROS graph. The build is Gradle:

```bash
git clone https://github.com/openTCS/openTCS.git
cd openTCS
./gradlew installDist

# Start the kernel (the control core)
./opentcs-kernel/build/install/openTCS-Kernel/bin/openTCS-Kernel

# In another terminal, start the operator client
./opentcs-operationsdesk/build/install/openTCS-OperationsDesk/bin/openTCS-OperationsDesk
```

The kernel exposes a TCP/JSON-RPC style API on port 55100 by default for the clients, and communication adapters connect vehicles over whichever protocol they speak. For VDA5050 vehicles, the `opentcs-commadapter-vda5050` module handles the MQTT topic structure, order messages and state reports without custom code — that is the feature that makes openTCS the default choice in European AGV projects.

**Where it hurts:** the operator clients are Java desktop applications (Swing), not web apps. If your operations team works from tablets in a browser, you will be putting a remote desktop or VNC layer in front of them. There is also no official container image, so a reproducible deployment means writing your own Dockerfile around the installDist output — plan for that in your platform work.

Storage is another trap: openTCS persists the plant model and transport orders in a database you configure (`openTCS` ships with a file-based and a database-backed persistence option). Back it up before you upgrade, because model migrations are not always automatic.

## Free Fleet: The Thin Adapter

Free Fleet is the pragmatic middle ground. It does not schedule traffic the way RMF does; it standardises how a fleet of ROS 2 robots is reached from a single fleet management node. The architecture is simple: a `fleet_adapter` process talks Zenoh to a `robot_client` running next to each robot, which in turn speaks to that robot's Nav2 stack.

That Zenoh hop is the clever part — it lets your fleet adapter and your robots sit on different hosts, different subnets or even different DDS domains without fighting ROS 2 discovery.

The repository ships real integration-test compose files, which is the best documentation you will get:

```yaml
services:
  minimal-nav2-bringup:
    image: ghcr.io/open-rmf/free_fleet/minimal-nav2-bringup:${ROS_DISTRO}-latest
    stop_signal: SIGINT
    network_mode: host
    privileged: true
    stdin_open: true
    tty: true
    environment:
      - ROS_DOMAIN_ID=42

  minimal-zenoh-bridge-ros2dds:
    image: ghcr.io/open-rmf/free_fleet/minimal-zenoh-bridge-ros2dds:${ROS_DISTRO}-latest
    network_mode: host
    stdin_open: true
    tty: true
    environment:
      - ROS_DOMAIN_ID=42

  minimal-zenoh-router:
    image: eclipse/zenoh:${ZENOH_VERSION}
    restart: unless-stopped
    network_mode: host
    stdin_open: true
    tty: true
    environment:
      - RUST_LOG=debug
```

Start it with `ROS_DISTRO=humble ZENOH_VERSION=1.0.0 docker compose -f nav2-docker-compose.yaml up`, then point your `fleet_adapter` config at the Zenoh router endpoint. If your robots already run Nav2 with a working `navigate_to_pose` action, you can be moving a small fleet in an afternoon.

**Where it hurts:** Free Fleet gives you connection and command routing, not conflict resolution. Two robots assigned overlapping paths will still collide unless your Nav2 costmaps or your own logic handle it. It also has no operator UI and no task bidding, so it is a component, not a product.

## Pitfalls and Migration Notes

1. **Do not confuse "fleet adapter" with "fleet manager."** Free Fleet adapters and RMF fleet adapters are both called adapters; only the RMF one plugs into a traffic scheduler. Teams that pick Free Fleet expecting RMF behaviour end up writing their own deadlock handling.
2. **Time synchronisation is not optional.** All three systems reason about time windows or message ordering. Run chrony or systemd-timesyncd on every host, and keep clock drift under 50 ms. We have seen reservation conflicts appear purely from a 300 ms clock skew between two hosts.
3. **Map frame consistency.** RMF and Nav2 both need a shared `map` frame. If your robots localise in separate maps with different origins, traffic reservations are meaningless. Build one site map and have every robot localise against it.
4. **VDA5050 is MQTT-shaped.** openTCS expects the standard topic layout (`order`, `state`, `instantAction`, `connection`). If a vendor "supports VDA5050" but renamed topics, you are writing an adapter anyway — ask for a protocol conformance statement before purchase.
5. **Upgrade one component at a time.** RMF's internal messages change between releases. Upgrade `rmf_traffic` and your fleet adapters together, then the dashboard.

If you are still choosing the robot-side navigation stack, our [ROS 2 Nav2 and MoveIt 2 deployment guide](../2026-06-05-self-hosted-ros2-robotics-navigation2-moveit2-guide/) covers the layer underneath this one. For testing routes before you commit hardware, the [robotics simulation comparison](../2026-06-09-self-hosted-robotics-simulation-gazebo-webots-coppeliasim-guide/) shows how to validate a plant model in Gazebo, Webots or CoppeliaSim. And if your robots are moving goods rather than people, the [vehicle routing optimization guide](../2026-06-16-self-hosted-vehicle-routing-optimization-vroom-jsprit-ortools/) explains how to compute the delivery orders your dispatcher will execute.

## FAQ

**Is Open-RMF free for commercial warehouse use?**
Yes. Open-RMF is Apache-2.0, which permits commercial use, modification and redistribution. You pay for integration labour and hardware, not licences. The same is true for openTCS (MIT) and Free Fleet (Apache-2.0).

**Can openTCS control robots that do not speak VDA5050?**
Yes, but you must write a communication adapter that translates between the openTCS kernel's abstract vehicle interface and your robot's protocol. openTCS ships a loopback adapter for virtual vehicles that is the best starting template.

**Do I need ROS 2 to run Open-RMF?**
Effectively yes. The core libraries are ROS 2 packages, and fleet adapters are ROS 2 nodes. You can containerise the whole stack so your operators never see ROS, but your integration team will be working in ROS 2.

**Which one handles elevators and automatic doors?**
Open-RMF. It has explicit door, lift and dispenser integrations as part of its building infrastructure adapters, which is why hospital and hotel logistics projects gravitate to it. openTCS can model them as special locations, but you implement the device handshake yourself.

**How many robots can each system handle?**
Practically, openTCS and Open-RMF both run installations with dozens of vehicles; the limit is usually network latency and map complexity rather than the scheduler. Free Fleet scales with your Zenoh router placement, and is typically used for small fleets where ROS 2 discovery would otherwise be painful.

**What is the smallest viable deployment to evaluate them?**
For openTCS, one kernel plus the loopback adapter gives you a simulated vehicle with no hardware. For Open-RMF, the `rmf_demos` office world in Docker is the fastest end-to-end look. For Free Fleet, run the Nav2 compose file above with a single simulated robot.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Open-RMF vs openTCS vs Free Fleet in 2026: Self-Hosted Robot Fleet Management Compared",
  "description": "A hands-on comparison of Open-RMF, openTCS and Free Fleet for self-hosting AGV and mobile robot fleets, including traffic scheduling, VDA5050 support and real deployment configs.",
  "datePublished": "2026-11-18",
  "dateModified": "2026-11-18",
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
