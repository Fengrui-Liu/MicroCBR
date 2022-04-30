import json
import logging
import os
from datetime import datetime
from typing import Union
from chaos import Chaos

import dateparser
import pandas as pd
import plotly.express as px
import pytz
from prometheus_api_client import PrometheusConnect

_LOGGER = logging.getLogger(__name__)


class Prometheus_Client:
    def __init__(self, url: str, disable_ssl: bool = True) -> None:

        self.PROM = PrometheusConnect(url=url, disable_ssl=disable_ssl)

    def get_all_metrics(self) -> list:
        """Get the list of all the metrics that the Prometheus host scrapes

        Returns:
            list: List of all prometheus metrics
        """

        return self.PROM.all_metrics()

    def get_pod_names(self, namespace="default") -> list:
        """Get the list of all the pods in the namespace

        Args:
            namespace (str, optional): Namespace. Defaults to "default".

        Returns:
            list: List of pods
        """

        QUERY = 'kube_pod_info{namespace="%s"}' % (namespace)
        POD_INFO = self.PROM.custom_query(QUERY)

        POD_NAME = []
        for pod in POD_INFO:
            POD_NAME.append(pod["metric"]["pod"])
        return POD_NAME

    def get_instance(self, type="mysql") -> list:
        """Get the instance of microservice

        Args:
            type (str, optional): Get the mysql instance. Defaults to "mysql".

        Returns:
            list: Instance of type
        """

        QUERY = ""
        if type == "mysql" or "mongodb":
            QUERY = "%s_up" % (type)
        else:
            _LOGGER.warn(
                "Undefined instance type, only supprot mysql and mongodb"
            )

        INSTANCE_NAME = []
        INSTANCE_INFO = self.PROM.custom_query(QUERY)
        for instance in INSTANCE_INFO:
            INSTANCE_NAME.append(instance["metric"]["instance"])

        return INSTANCE_NAME

    def query_metric(
        self,
        query: str,
        query_idx: int,
        start_time: datetime,
        end_time: datetime,
        step: str,
        namespace: str,
        pod: str,
        chaos: Chaos = Chaos(),
        save: bool = True,
    ) -> Union[list, None]:
        """Query metrics from Prometheus

        Args:
            query (str): PromQL query
            query_idx (int): PromQL query index
            start_time (datetime): PromQL query start time
            end_time (datetime): PromQL query end time
            step (str): PromQL query step
            namespace (str): PromQL query namespace
            pod (str): PromQL query pod
            chaos (Chaos, optional): Label with chaos experiment. Defaults to Chaos().
            save (bool, optional): Save the query result. Defaults to True.

        Returns:
            Union[list, None]: Query result
        """

        query = query.strip()

        metric_data = self.PROM.custom_query_range(
            query=query, start_time=start_time, end_time=end_time, step=step
        )

        if not save:
            return metric_data

        if not metric_data:
            _LOGGER.error("No values for {}".format(query))
            return None

        chaos_name = chaos.name
        if not chaos_name:
            _LOGGER.warn("Undefined chaos, use none as default")
            chaos_name = "none"
        data = metric_data[0]
        value = data["values"]

        f_path = "../metric/{chaos_name}/{namespace}/{pod}/{query_idx}.json".format(
            chaos_name=chaos_name,
            namespace=namespace,
            pod=pod,
            query_idx=str(query_idx),
        )

        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, "w") as f:
            json.dump(value, f)

        return value

    def plot_metric(
        self,
        chaos: Chaos,
        namespace: str,
        pod: str,
        idx: int,
        tz: str = "Asia/Shanghai",
    ) -> px.line:
        """Plot the query metric with plotly

        Args:
            chaos (Chaos): Label the query
            namespace (str): PromQL query namespace
            pod (str): PromQL query pod
            idx (int): PromQl query index
            tz (str, optional): Format result with timezone. Defaults to "Asia/Shanghai".

        Returns:
            px.line : Plotly line chart
        """
        chaos_name = chaos.name
        f_path = "../metric/%s/%s/%s/%s.json" % (
            chaos_name,
            namespace,
            pod,
            idx,
        )
        if not os.path.exists(f_path):
            _LOGGER.error("No metric data for %s" % (f_path))
        df = pd.read_json(f_path).rename(columns={0: "timestamp", 1: "value"})
        df["timestamp"] = pd.to_datetime(
            df["timestamp"].values, unit="s", utc=True
        ).tz_convert(tz)

        chaos_creation_time = chaos.creation_time.astimezone(pytz.timezone(tz))
        chaos_stop_time = dateparser.parse(
            "in %s" % (chaos.duration),
            settings={"RELATIVE_BASE": chaos_creation_time},
        ).astimezone(pytz.timezone(tz))

        fig = px.line(df, x="timestamp", y="value")
        fig.add_vrect(
            x0=chaos_creation_time,
            x1=chaos_stop_time,
            fillcolor="LightSalmon",
            opacity=0.5,
            layer="below",
            line_width=0,
            annotation_text=chaos_name,
            annotation_position="top left outside",
        )

        fig.update_layout(
            title={
                "text": "namespace: %s <br>pod: %s <br>chaos: %s"
                % (namespace, pod, chaos_name),
                "y": 0.97,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top",
            },
            font={"family": "Times New Roman", "size": 10, "color": "Black"},
        )

        return fig
