# MicroCBR

MicroCBR: Case-based Reasoning on Spatio-temporal Fault Knowledge Graph for Microservices Troubleshooting

## k8s experiment

### demo project:

1. [Online Boutique with OpenTelemetry](https://github.com/julianocosta89/opentelemetry-microservices-demo)
2. [Sock shop with OpenTelemetry](https://github.com/microservices-demo/microservices-demo)
3. [Train ticket with OpenTelemetry](https://github.com/FudanSELab/train-ticket)
4. [Banks](https://github.com/GoogleCloudPlatform/bank-of-anthos)

# exporters

1. [blackbox-exporter](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-blackbox-exporter)
2. [mongodb-exporter](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-mongodb-exporter)
3. [mysql-exporter](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-mysql-exporter)
4. [rabbitmq-exporter](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-rabbitmq-exporter)
5. [redis-exporter](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-redis-exporter)
6. [jmx-exporter](https://github.com/prometheus/jmx_exporter)
7. [kube-state-metrics](https://github.com/kubernetes/kube-state-metrics)
8. [ping_exporter](https://github.com/czerwonk/ping_exporter)

### chaos tool:

1. [Chaos-mesh](https://github.com/chaos-mesh/chaos-mesh)
2. Manual injection

## Fault injection

1. k8s experiment
    1. Pod failure, kill, container kill
    2. Network disconnection, partition, high delays, high packet loss rate, packet reordering, limit bandwidth
    3. Stress of CPU, memory
    4. DNS error, wrong
    5. Time faults for clock skew
    6. JVM cpu-count stress, memory-type stress, trigger garbage collection
    7. HTTP patch
2. physical nodes


# Knowledge base description (KNOWLEDGE_BASE.yaml)

* instance_related: whether the kb is peculiar to instance or not
* metrics: prometheus metrics, some of them rely on exporters
  * index: index for queries from [QUERY.yaml](chaos-simulator/dev/METRIC.yaml)
* traces: Jaeger traces
* logs: k8s logs and application logs
* cmd: command line operations