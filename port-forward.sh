# nohup kubectl port-forward svc/chaos-dashboard -n chaos-testing 2333:2333 --address='0.0.0.0' &
# nohup kubectl port-forward svc/frontend-external -n default 1080:80 --address='0.0.0.0' &
# nohup kubectl port-forward svc/front-end -n sock-shop 1081:80 --address='0.0.0.0' &
# nohup kubectl port-forward svc/ts-ui-dashboard -n tt 1082:80 --address='0.0.0.0' &

# nohup kubectl port-forward svc/jaeger-frontend -n default 16686:16686 --address='0.0.0.0' &

# nohup kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090 --address='0.0.0.0' &
# nohup kubectl port-forward svc/prometheus-grafana -n monitoring 80:80 --address='0.0.0.0' &

# nohup kubectl port-forward svc/chaos-dashboard -n chaos-testing 2333:2333 --address='0.0.0.0' &


nohup kubectl port-forward svc/jaeger-frontend -n default 16686:16686 &

nohup kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090  &
nohup kubectl port-forward svc/prometheus-grafana -n monitoring 8080:80 &

nohup kubectl port-forward svc/chaos-dashboard -n chaos-testing 2333:2333 &