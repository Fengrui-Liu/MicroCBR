import yaml
import os
import logging
from weight import Weight
from schema import Schema, SchemaError, Optional
from typing import Union

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


class KB_Chaos:
    def __init__(self, chaos_path):
        self.chaos_path = chaos_path
        self.last_chaos = None

    def is_instance_related(self):
        """Check whether chaos is instance related"""

        if len(os.listdir(self.chaos_path)) == 0:
            _LOGGER.error("No chaos found in {}".format(self.chaos_path))
            return True, None

        for chaos in os.listdir(self.chaos_path):
            if chaos.endswith(".yaml"):
                f = open(self.chaos_path + "/" + chaos)
                data = f.read()
                f.close()
                data = yaml.safe_load(data)
                if self.last_chaos is None:
                    self.last_chaos = data

                else:
                    if data["anomalies"] == self.last_chaos["anomalies"]:
                        continue
                    else:
                        return True, data

        if len(os.listdir(self.chaos_path)) <= 2:
            return True, data

        return False, data


class KB:
    def __init__(self) -> None:

        self.kb = None
        self.hierarchy = {0: "chaos_type", 1: "chaos"}
        self.metrics = []
        self.traces = []
        self.logs = []
        self.cmds = []

        self.type_metrics = []
        self.type_traces = []
        self.type_logs = []
        self.type_cmds = []

        self.metrics_score = None
        self.traces_score = None
        self.logs_score = None
        self.cmds_score = None

        self.type_metrics_score = None
        self.type_traces_score = None
        self.type_logs_score = None
        self.type_cmds_score = None

    def load(self, kb_path: str) -> Union[dict, None]:
        """Load knowledge base

        Args:
            kb_path (str): Knowledge base path

        Raises:
            Exception: Knowledge base check

        Returns:
            dict: Knowledge base
        """

        if type(kb_path) is str:
            f = open(kb_path)
            data = f.read()
            f.close()
            self.kb = yaml.safe_load(data)
        elif type(kb_path) is dict:
            self.kb = kb_path

        is_checked = self.check_kb()

        if is_checked:
            self.score_fingerprint()
            return self.kb
        else:
            raise Exception("Knowledge Base check failed")

    def check_kb(self) -> bool:
        """Check knowledge base config

        Raises:
            se: Schema error

        Returns:
            bool: check result
        """
        if self.kb is None:
            _LOGGER.error("Knowledge Base is not loaded")
            return False

        anomaly_schema = [{"index": int, "action": str, Optional("order"): int}]
        custom_metrics_schema = {
            Optional("network"): anomaly_schema,
            Optional("cpu"): anomaly_schema,
            Optional("memory"): anomaly_schema,
            Optional("io"): anomaly_schema,
            Optional("container"): anomaly_schema,
            Optional("mongo"): anomaly_schema,
            Optional("mysql"): anomaly_schema,
            Optional("icmp"): anomaly_schema,
            Optional("time"): anomaly_schema,
            Optional("jvm"): anomaly_schema,
            Optional("http"): anomaly_schema,
        }

        custom_traces_schema = {
            Optional("onehop"): anomaly_schema,
        }

        custom_logs_schema = {
            Optional("pod"): anomaly_schema,
        }

        custom_cmds_schema = {
            Optional("config"): anomaly_schema,
            Optional("exec"): anomaly_schema,
        }

        custom_schema = [
            {
                "index": int,
                "experiment": str,
                "instance_related": bool,
                Optional("order"): bool,
                "anomalies": {
                    Optional("metrics"): custom_metrics_schema,
                    Optional("traces"): custom_traces_schema,
                    Optional("logs"): custom_logs_schema,
                    Optional("cmds"): custom_cmds_schema,
                },
            }
        ]

        config_schema = Schema(
            {
                Optional("network"): custom_schema,
                Optional("pod"): custom_schema,
                Optional("stress"): custom_schema,
                Optional("time"): custom_schema,
                Optional("jvm"): custom_schema,
                Optional("dns"): custom_schema,
                Optional("http"): custom_schema,
                Optional("io"): custom_schema,
                Optional("config"): custom_schema,
            }
        )

        try:
            config_schema.validate(self.kb)
            _LOGGER.info("Configuration is valid.")
        except SchemaError as se:
            raise se

        return True

    def score_fingerprint(self):
        """Score fingerprint"""

        # Two hierarchies for our experiment

        chaos_types = self.kb.keys()

        for chaos_type in chaos_types:

            type_metrics = []
            type_traces = []
            type_logs = []
            type_cmds = []
            for chaos in self.kb[chaos_type]:
                anomalies = chaos["anomalies"]
                metrics = (
                    anomalies["metrics"] if "metrics" in anomalies else None
                )
                traces = anomalies["traces"] if "traces" in anomalies else None
                logs = anomalies["logs"] if "logs" in anomalies else None
                cmds = anomalies["cmds"] if "cmds" in anomalies else None

                (
                    metrics_instance,
                    traces_instance,
                    logs_instance,
                    cmds_instance,
                ) = self.analyse(metrics, traces, logs, cmds)

                type_metrics += metrics_instance
                type_traces += traces_instance
                type_logs += logs_instance
                type_cmds += cmds_instance

            self.type_metrics.append(type_metrics) if type_metrics else None
            self.type_traces.append(type_traces) if type_traces else None
            self.type_logs.append(type_logs) if type_logs else None
            self.type_cmds.append(type_cmds) if type_cmds else None

        for (data, score) in zip(
            [
                self.metrics,
                self.traces,
                self.logs,
                self.cmds,
                self.type_metrics,
                self.type_traces,
                self.type_logs,
                self.type_cmds,
            ],
            [
                "metrics_score",
                "traces_score",
                "logs_score",
                "cmds_score",
                "type_metrics_score",
                "type_traces_score",
                "type_logs_score",
                "type_cmds_score",
            ],
        ):
            weight = Weight(data)
            weighted_score = weight()
            max_score = max(weighted_score.values())
            for key in weighted_score:
                weighted_score[key] = weighted_score[key] / max_score
            setattr(self, score, weighted_score)

    def analyse(
        self, metrics: list, traces: list, logs: list, cmds: list
    ) -> tuple:
        """Analyse metrics, traces, logs, cmds

        Args:
            metrics (list): metrics
            traces (list): traces
            logs (list): logs
            cmds (list): commands

        Returns:
            tuple: metrics, traces, logs, cmds
        """

        metrics_instance = self.analyse_fingerprint(metrics, "metrics")
        traces_instance = self.analyse_fingerprint(traces, "traces")
        logs_instance = self.analyse_fingerprint(logs, "logs")
        cmds_instance = self.analyse_fingerprint(cmds, "cmds")

        return metrics_instance, traces_instance, logs_instance, cmds_instance

    def analyse_fingerprint(
        self, fingerprint: list, target_type: str = ""
    ) -> list:
        """Analyse fingerprint individually

        Args:
            fingerprint (list): Fingerprint
            target_type (str, optional): Fingerprint type. Defaults to "".

        Returns:
            list: Rename instances
        """

        if fingerprint is None or target_type == "":
            _LOGGER.info("No {} found in Knowledge Base".format(target_type))
            return []

        types = fingerprint.keys()
        new_instance = []
        for one_type in types:
            for clue in fingerprint[one_type]:
                idx = clue["index"]
                action = clue["action"]
                clue_name = one_type + "-" + str(idx) + "-" + action
                new_instance.append(clue_name)

        if new_instance:
            if target_type == "metrics":
                self.metrics.append(new_instance)
            elif target_type == "traces":
                self.traces.append(new_instance)
            elif target_type == "logs":
                self.logs.append(new_instance)
            elif target_type == "cmds":
                self.cmds.append(new_instance)
            self.logs.append(new_instance)

        return new_instance
