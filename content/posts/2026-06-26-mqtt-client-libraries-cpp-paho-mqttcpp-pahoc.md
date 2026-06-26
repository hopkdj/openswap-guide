---
title: "Self-Hosted MQTT Client Libraries for C++: Eclipse Paho C++ vs mqtt_cpp vs Paho C for IoT Messaging"
date: "2026-06-26"
tags: ["mqtt", "iot", "c-plus-plus", "messaging", "embedded", "sensors"]
draft: false
---

## Introduction

MQTT (Message Queuing Telemetry Transport) is the backbone of IoT communication — a lightweight publish-subscribe protocol designed for constrained devices and unreliable networks. When building self-hosted IoT infrastructure in C++, whether it's a sensor gateway aggregating environmental data or a home automation controller orchestrating smart devices, the MQTT client library you choose determines connection reliability, memory footprint, and protocol feature support.

Three libraries form the foundation of MQTT connectivity in C++: **Eclipse Paho C++** provides the standards-compliant reference implementation backed by the Eclipse Foundation, **mqtt_cpp** offers a modern header-only design for C++17 projects, and **Paho C** delivers the smallest possible footprint for deeply embedded systems. Each serves a distinct deployment profile.

This comparison examines protocol compliance, resource usage, API design, and integration patterns across edge-to-cloud IoT architectures.

## Understanding MQTT Client Requirements

An MQTT client needs to handle three core operations: publishing messages to topics, subscribing to topic filters, and maintaining a persistent connection with keepalive pings. Beyond basics, production clients need TLS encryption, authentication (username/password or client certificates), Last Will and Testament (LWT) messages for graceful disconnection detection, and Quality of Service (QoS) levels 0, 1, and 2.

For C++ applications, the library's threading model is critical. Should the client run its own internal event loop thread, or should you integrate MQTT events into your existing event loop? The answer depends on whether you're building a single-purpose sensor bridge or integrating MQTT into a larger application server.

## Detailed Comparison

| Feature | Eclipse Paho C++ | mqtt_cpp | Eclipse Paho C |
|---------|-----------------|----------|----------------|
| GitHub Stars | 1,310 | 483 | 2,323 |
| Language | C++11 | C++17 | C99 |
| Header-Only | No (compiled) | Yes | No (compiled) |
| MQTT Version | 3.1, 3.1.1, 5.0 | 5.0 | 3.1, 3.1.1, 5.0 |
| TLS Support | OpenSSL | Optional (OpenSSL) | OpenSSL |
| WebSocket Transport | Yes | No | Yes |
| Async Callbacks | Yes | Yes | Yes |
| Synchronous API | No | Yes | Yes |
| QoS Levels | 0, 1, 2 | 0, 1, 2 | 0, 1, 2 |
| Thread Safety | Full | Caller-managed | Full |

### Eclipse Paho C++: The Reference Standard

Paho C++ is the official Eclipse Foundation client library for MQTT. Built on top of the Paho C library, it provides a modern C++ async API with callback-based event handling, automatic reconnection, and full MQTT 5.0 support including session expiry, message expiry, and topic aliases.

```cpp
#include <mqtt/async_client.h>

class MqttHandler : public virtual mqtt::callback {
    mqtt::async_client client_;
    mqtt::connect_options connOpts_;
    
public:
    MqttHandler(const std::string& broker)
        : client_(broker, "cpp-gateway-001") {
        client_.set_callback(*this);
        connOpts_.set_keep_alive_interval(20);
        connOpts_.set_clean_start(true);
    }
    
    bool connect() {
        mqtt::token_ptr tok = client_.connect(connOpts_);
        tok->wait();
        return tok->get_return_code() == mqtt::connect_return_code::accepted;
    }
    
    void subscribe(const std::string& topic) {
        client_.subscribe(topic, 1);
    }
    
    void publish(const std::string& topic, const std::string& payload) {
        auto msg = mqtt::make_message(topic, payload);
        msg->set_qos(1);
        client_.publish(msg);
    }
    
    // Callback overrides
    void connected(const std::string& cause) override {
        std::cout << "Connected to MQTT broker" << std::endl;
    }
    
    void message_arrived(mqtt::const_message_ptr msg) override {
        std::cout << "Topic: " << msg->get_topic() 
                  << " Payload: " << msg->to_string() << std::endl;
    }
    
    void connection_lost(const std::string& cause) override {
        std::cout << "Connection lost: " << cause << " - reconnecting..." << std::endl;
    }
};
```

Paho C++ handles reconnection logic automatically — you configure the retry interval, and it re-establishes the connection and resubscribes to topics transparently. This is essential for IoT deployments where network connectivity is intermittent.

```bash
# Build Paho C (required dependency) then Paho C++
git clone https://github.com/eclipse/paho.mqtt.c.git
cd paho.mqtt.c && mkdir build && cd build
cmake .. -DPAHO_WITH_SSL=TRUE && make -j$(nproc) && sudo make install

git clone https://github.com/eclipse/paho.mqtt.cpp.git
cd paho.mqtt.cpp && mkdir build && cd build
cmake .. && make -j$(nproc) && sudo make install
```

### mqtt_cpp: Modern Header-Only Design

mqtt_cpp takes a fresh approach: a single-header C++17 library with no external dependencies (OpenSSL optional for TLS). It focuses exclusively on MQTT 5.0, embracing modern features like shared subscriptions, flow control, and user properties.

```cpp
#include <mqtt_client_cpp.hpp>

// Create an MQTT client with just a few lines
boost::asio::io_context ioc;
auto client = MQTT_NS::make_sync_client(ioc, "broker.local", 1883);

// Connect
client->connect();

// Subscribe with QoS 1
client->subscribe("sensors/+/temperature", MQTT_NS::qos::at_least_once);

// Publish a retained message
client->publish("gateway/status", "online",
    MQTT_NS::qos::at_least_once | MQTT_NS::retain::yes);

// Receive messages
client->set_message_handler([](MQTT_NS::optional<std::uint16_t> packet_id,
    MQTT_NS::string_view topic, MQTT_NS::string_view payload) {
    std::cout << "[" << topic << "]: " << payload << std::endl;
});

// Run the event loop
ioc.run();
```

The synchronous API simplifies testing and scripting — no callback pyramid for simple publish-subscribe flows. For production services that need async operation, mqtt_cpp integrates naturally with Boost.Asio's event loop, making it a natural fit for applications already using Asio for networking.

mqtt_cpp's header-only distribution makes cross-compilation for ARM and MIPS targets straightforward — no need to build shared libraries for each target architecture.

```bash
# Header-only install
git clone https://github.com/redboltz/mqtt_cpp.git
cp -r mqtt_cpp/include/mqtt_client_cpp.hpp /usr/local/include/
```

### Eclipse Paho C: The Minimal Foundation

For resource-constrained embedded Linux systems with only 64MB RAM, Paho C provides the smallest MQTT client footprint. At approximately 200KB compiled (stripped), it leaves maximum headroom for application logic. Paho C is also the library you use when building language bindings — Paho C++, Python paho-mqtt, and Node.js MQTT.js all eventually call into Paho C or its equivalent.

```c
#include <MQTTClient.h>

#define ADDRESS     "tcp://broker.local:1883"
#define CLIENTID    "embedded-sensor-42"
#define TOPIC       "sensors/temperature"
#define QOS         1
#define TIMEOUT     10000L

volatile int delivered = 0;

void delivered_callback(void* context, MQTTClient_deliveryToken dt) {
    delivered = 1;
}

int message_arrived(void* context, char* topicName, int topicLen,
                    MQTTClient_message* message) {
    printf("Message arrived: %.*s
", message->payloadlen, 
           (char*)message->payload);
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}

int main() {
    MQTTClient client;
    MQTTClient_create(&client, ADDRESS, CLIENTID,
        MQTTCLIENT_PERSISTENCE_NONE, NULL);
    
    MQTTClient_setCallbacks(client, NULL, NULL, 
        message_arrived, delivered_callback);
    
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
    MQTTClient_connect(client, &conn_opts);
    MQTTClient_subscribe(client, TOPIC, QOS);
    
    MQTTClient_message pubmsg = MQTTClient_message_initializer;
    char payload[] = "25.3";
    pubmsg.payload = payload;
    pubmsg.payloadlen = strlen(payload);
    pubmsg.qos = QOS;
    pubmsg.retained = 0;
    MQTTClient_publishMessage(client, TOPIC, &pubmsg, NULL);
    
    // Keep running
    while (1) sleep(1);
    MQTTClient_disconnect(client, TIMEOUT);
    MQTTClient_destroy(&client);
}
```

The C API is verbose but gives you full control over memory allocation — essential for embedded systems where dynamic allocation may be restricted or disabled entirely after initialization.

## Why Self-Host Your MQTT Infrastructure?

Running your own MQTT broker and writing custom C++ clients gives you complete control over data flow without relying on cloud IoT platforms that charge per message or per device. A Raspberry Pi 4 running Mosquitto can handle 10,000+ concurrent MQTT connections with sub-millisecond latency. Our [MQTT broker platform comparison](../self-hosted-mqtt-platforms-mosquitto-emqx-hivemq-iot-guide-2026/) covers Mosquitto, EMQX, and HiveMQ for self-hosted deployments.

For diagnostic and monitoring tools, see our [MQTT diagnostic tools guide](../2026-06-07-self-hosted-mqtt-diagnostic-tools-mqttx-mqtt-explorer-hivemq-cli-guide/) covering MQTTX, MQTT Explorer, and HiveMQ CLI for debugging message flows during development. If you're building BLE-to-MQTT bridges for sensor data collection, our [BLE MQTT gateway comparison](../2026-06-11-self-hosted-bluetooth-ble-mqtt-gateway-theengs-openmqttgateway/) covers Theengs Gateway and OpenMQTTGateway integration patterns.

## Deployment Architecture

A typical IoT deployment connects C++ sensor gateways to a central MQTT broker, with data flowing to time-series databases and dashboard applications. The C++ MQTT client runs on each gateway, collecting sensor readings and publishing them at configurable intervals. The broker distributes messages to subscribers — a database writer, an alerting service, and a real-time dashboard.

For TLS security in production, use client certificates rather than username/password authentication. Generate device-specific certificates with OpenSSL and configure your MQTT broker to verify them. Paho C++ and Paho C support client certificate authentication natively.

## FAQ

### Which library should I use for an ESP32 or similar microcontroller?

None of these — C++ standard library dependencies make them unsuitable for microcontroller environments. Use a purpose-built embedded MQTT library like PubSubClient (Arduino), esp-mqtt (ESP-IDF), or the embedded Paho C variant (paho.mqtt.embedded-c). The libraries discussed here target Linux-based embedded systems with full POSIX support.

### How do I handle MQTT broker failover?

Paho C++ supports multiple broker URIs in its connection options — if the primary broker is unreachable, it tries the next one automatically. With mqtt_cpp, implement failover manually by catching connection exceptions and reconnecting to an alternate broker. For high-availability deployments, run an MQTT broker cluster with EMQX or VerneMQ rather than relying on client-side failover.

### What is the memory footprint difference between these libraries?

Paho C adds approximately 200KB to your binary (stripped, without TLS). Paho C++ adds about 500KB (including the underlying Paho C dependency). mqtt_cpp as a header-only library contributes roughly 150KB of compiled code for typical usage. For embedded Linux gateways with 256MB+ RAM, any of these is well within budget.

### Can I process MQTT messages in a C++ coroutine?

Yes. mqtt_cpp integrates directly with Boost.Asio, which supports C++20 coroutines — you can `co_await` message reception. Paho C++ uses a callback model, but you can bridge callbacks to coroutines using promise/future or a channel abstraction. This is particularly useful for request-response patterns over MQTT where you publish a request and await the response on a reply topic.

### Does MQTT 5.0 matter for self-hosted deployments?

MQTT 5.0 adds session expiry (connections survive brief network outages without re-subscribing), message expiry (stale sensor data auto-discards), shared subscriptions (load-balance messages across multiple consumer instances), and user properties (attach arbitrary metadata to messages). For new deployments, MQTT 5.0 features significantly reduce application-level boilerplate. Both Paho C++ and mqtt_cpp support MQTT 5.0; Paho C added 5.0 support in recent versions.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MQTT Client Libraries for C++: Eclipse Paho C++ vs mqtt_cpp vs Paho C for IoT Messaging",
  "description": "Compare Eclipse Paho C++, mqtt_cpp, and Paho C for building self-hosted IoT MQTT clients in C++. Covers protocol support, memory footprint, threading models, and deployment patterns for Linux embedded gateways.",
  "datePublished": "2026-06-26",
  "dateModified": "2026-06-26",
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
