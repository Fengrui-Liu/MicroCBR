import logging
import yaml
from schema import Schema, SchemaError, Optional
from collections import Counter
from util import weighted_LCS
import heapq
from difflib import SequenceMatcher

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


class Reasoner:
    def __init__(
        self,
        kb,
        use_metrics=True,
        use_traces=True,
        use_cmds=True,
        use_logs=True,
    ) -> None:
        self.kb = kb
        self.fingerprint = None
        self.f_metrics = None
        self.f_traces = None
        self.f_cmds = None
        self.f_logs = None
        self.metrics_order = False
        self.ground_truth = None

        self.use_metrics = use_metrics
        self.use_traces = use_traces
        self.use_cmds = use_cmds
        self.use_logs = use_logs

        self.score = 0

        self.type_scores = {}
        self.case_scores = {}

        self.cmds_detail = {}
        self.logs_detail = {}

    def load_fingerprint(
        self, f_path: str, cmds_f_path="./CMD.yaml", logs_f_path="./LOG.yaml"
    ) -> bool:
        """Load a case for reasoning and troubleshooting

        Args:
            f_path (str): Target fingerprint file path

        Raises:
            se: Fingerprint yaml file config error

        Returns:
            bool: Success loaded
        """

        if type(f_path) is str:
            f = open(f_path)
            fingerprint = f.read()
            f.close()
            self.fingerprint = yaml.safe_load(fingerprint)
        elif type(f_path) is dict:
            self.fingerprint = f_path

        f = open(cmds_f_path)
        self.cmds_detail = yaml.safe_load(f.read())
        f.close()

        f = open(logs_f_path)
        self.logs_detail = yaml.safe_load(f.read())
        f.close()

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

        custom_schema = Schema(
            {
                "groundtruth": str,
                Optional("order"): bool,
                "anomalies": {
                    Optional("metrics"): custom_metrics_schema,
                    Optional("traces"): custom_traces_schema,
                    Optional("logs"): custom_logs_schema,
                    Optional("cmds"): custom_cmds_schema,
                },
            }
        )

        try:
            custom_schema.validate(self.fingerprint)
            _LOGGER.info("Configuration is valid.")
        except SchemaError as se:
            raise se

        anomalies = self.fingerprint["anomalies"]

        if "order" in self.fingerprint and self.fingerprint["order"] is True:
            self.metrics_order = self.fingerprint["order"]

        self.f_metrics = (
            anomalies["metrics"] if "metrics" in anomalies else None
        )
        self.f_traces = anomalies["traces"] if "traces" in anomalies else None
        self.f_logs = anomalies["logs"] if "logs" in anomalies else None
        self.f_cmds = anomalies["cmds"] if "cmds" in anomalies else None

        if self.metrics_order is True:
            self.f_metrics = self.rename(self.f_metrics, order=True)
        else:
            self.f_metrics = self.rename(self.f_metrics, order=False)
        self.f_traces = self.rename(self.f_traces)
        self.f_cmds = self.rename(self.f_cmds)
        self.f_logs = self.rename(self.f_logs)

        self.ground_truth = (
            self.fingerprint["groundtruth"]
            if "groundtruth" in self.fingerprint
            else None
        )

        return True

    def reasoning(self):

        # For one fault fingerprint
        self.analyse_case()

        # For fault type using exactly matched fingerprint
        self.analyse_type_by_fingerprint()

        # For fault type using top3 case
        # self.analyse_type_by_case()

        # For fault type using partial fingerprint similarity

        # self.analyse_type_by_case_sim()

    def analyse_type_by_case_sim(self):

        kb_case_types = self.kb.kb.keys()

        type_scores = dict()
        self.target_case_score = 0

        def update_score_equal_match(case, scores, fingerprint):
            case = case[0] if case else []
            counter = Counter(case)
            for item in fingerprint[0]:
                if item in case:
                    weight = scores[item]
                    # global score
                    self.target_case_score += (
                        weight
                        * counter[item]
                        / max(len(case), len(fingerprint[0]))
                    )

        def update_score_sim_match(case, scores, fingerprint, type_="logs"):

            if type_ == "logs":
                details = self.logs_detail
            elif type_ == "cmds":
                details = self.cmds_detail

            keys = fingerprint.keys()
            for key in keys:
                for f in fingerprint[key]:
                    for deatil in details[key]:
                        if f["index"] == deatil["index"]:
                            f_details = deatil["query"]
                            break

                    max_c_score = 0

                    if key not in case:
                        key
                        continue
                    for c in case[key]:
                        for detail in details[key]:
                            if c["index"] == detail["index"]:
                                c_detailts = detail["query"]
                                break

                        f_split_detail = f_details.split(" ")
                        c_split_detail = c_detailts.split(" ")
                        s = SequenceMatcher(
                            None, f_split_detail, c_split_detail
                        )
                        size = s.find_longest_match(
                            0, len(f_split_detail), 0, len(c_split_detail)
                        ).size

                        score = size / max(
                            len(f_split_detail), len(c_split_detail)
                        )

                        name = (
                            key + "-" + str(c["index"]) + "-" + str(c["action"])
                        )
                        weight = scores[name]

                        score = score * weight

                        if score > max_c_score:
                            max_c_score = score

                    self.target_case_score += score / max(
                        sum([len(x) for x in case.values()]),
                        sum([len(x) for x in fingerprint.values()]),
                    )

        for kb_case_type in kb_case_types:

            type_scores.setdefault(kb_case_type, {})
            for kb_case in self.kb.kb[kb_case_type]:
                self.target_case_score = 0
                experiment = kb_case["experiment"]

                kb_anomalies = kb_case["anomalies"]

                kb_metrics = (
                    kb_anomalies["metrics"]
                    if "metrics" in kb_anomalies
                    else None
                )
                kb_traces = (
                    kb_anomalies["traces"] if "traces" in kb_anomalies else None
                )
                kb_logs = (
                    kb_anomalies["logs"] if "logs" in kb_anomalies else None
                )
                kb_cmds = (
                    kb_anomalies["cmds"] if "cmds" in kb_anomalies else None
                )

                kb_metrics = self.rename(kb_metrics)
                kb_traces = self.rename(kb_traces)

                update_score_equal_match(
                    kb_metrics, self.kb.type_metrics_score, self.f_metrics
                ) if self.f_metrics and self.use_metrics else None
                update_score_equal_match(
                    kb_traces, self.kb.type_traces_score, self.f_traces
                ) if self.f_traces and self.use_traces else None

                f_logs = (
                    self.fingerprint["anomalies"]["logs"]
                    if "logs" in self.fingerprint["anomalies"]
                    else None
                )
                f_cmds = (
                    self.fingerprint["anomalies"]["cmds"]
                    if "cmds" in self.fingerprint["anomalies"]
                    else None
                )

                update_score_sim_match(
                    kb_logs, self.kb.type_logs_score, f_logs, type_="logs"
                ) if f_logs and self.use_logs and kb_logs else None

                update_score_sim_match(
                    kb_cmds, self.kb.type_cmds_score, f_cmds, type_="cmds"
                ) if f_cmds and self.use_cmds and kb_cmds else None

                type_scores[kb_case_type][experiment] = self.target_case_score

        for key, value in type_scores.items():
            top3_case = heapq.nlargest(3, value, key=value.get)
            top_score = 0
            for item in top3_case:
                top_score += value[item]

            self.type_scores[key] = top_score / len(top3_case)

    def analyse_type_by_case(self):

        kb_case_types = self.kb.kb.keys()

        type_scores = dict()

        for kb_case_type in kb_case_types:
            type_scores.setdefault(kb_case_type, {})
            for kb_case in self.kb.kb[kb_case_type]:
                experiment = kb_case["experiment"]
                type_scores[kb_case_type][experiment] = self.case_scores[
                    experiment
                ]

        for key, value in type_scores.items():
            top3_case = heapq.nlargest(3, value, key=value.get)
            top_score = 0
            for item in top3_case:
                top_score += self.case_scores[item]

            self.type_scores[key] = top_score / len(top3_case)

    def analyse_type_by_fingerprint(self):

        kb_case_types = self.kb.kb.keys()

        for kb_case_type in kb_case_types:

            kb_type_metrics = {0: []}
            kb_type_traces = {0: []}
            kb_type_logs = {0: []}
            kb_type_cmds = {0: []}
            for kb_case in self.kb.kb[kb_case_type]:
                kb_anomalies = kb_case["anomalies"]

                kb_metrics = (
                    kb_anomalies["metrics"]
                    if "metrics" in kb_anomalies
                    else None
                )
                kb_traces = (
                    kb_anomalies["traces"] if "traces" in kb_anomalies else None
                )
                kb_logs = (
                    kb_anomalies["logs"] if "logs" in kb_anomalies else None
                )
                kb_cmds = (
                    kb_anomalies["cmds"] if "cmds" in kb_anomalies else None
                )

                kb_rename_metrics = self.rename(kb_metrics)
                kb_rename_traces = self.rename(kb_traces)
                kb_rename_logs = self.rename(kb_logs)
                kb_rename_cmds = self.rename(kb_cmds)

                kb_type_metrics[0].extend(
                    kb_rename_metrics[0]
                ) if kb_rename_metrics else None

                kb_type_traces[0].extend(
                    kb_rename_traces[0]
                ) if kb_rename_traces else None
                kb_type_logs[0].extend(
                    kb_rename_logs[0]
                ) if kb_rename_logs else None
                kb_type_cmds[0].extend(
                    kb_rename_cmds[0]
                ) if kb_rename_cmds else None

            case_num = len(self.kb.kb[kb_case_type])
            self.cal_similarity(
                kb_type_metrics,
                kb_type_traces,
                kb_type_logs,
                kb_type_cmds,
                case_num,
            )
            self.type_scores[kb_case_type] = self.score

    def cal_similarity(
        self, metrics, traces, logs, cmds, case_num=1, hierarchy="type"
    ):

        self.score = 0

        def update_score(case, scores, fingerprint):

            case = case[0] if case else []
            counter = Counter(case)

            for item in fingerprint[0]:
                if item in case:
                    weight = scores[item]
                    # global score
                    self.score += (
                        weight
                        * counter[item]
                        / max(len(case), len(fingerprint[0]))
                    )

        if hierarchy == "type":
            update_score(
                metrics, self.kb.type_metrics_score, self.f_metrics
            ) if self.f_metrics and self.use_metrics else None
            update_score(
                traces, self.kb.type_traces_score, self.f_traces
            ) if self.f_traces and self.use_traces else None
            update_score(
                logs, self.kb.type_logs_score, self.f_logs
            ) if self.f_logs and self.use_logs else None
            update_score(
                cmds, self.kb.type_cmds_score, self.f_cmds
            ) if self.f_cmds and self.use_cmds else None

        if hierarchy == "case":

            if self.f_metrics and self.metrics_order and self.use_metrics:
                # TODO: finish this temporal code
                f_metrics_reorder = [
                    i
                    for item in dict(sorted(self.f_metrics.items())).values()
                    for i in sorted(item)
                ]

                case_metrics_reorder = [
                    i
                    for item in dict(sorted(metrics.items())).values()
                    for i in sorted(item)
                ]

                metrics = weighted_LCS(
                    f_metrics_reorder,
                    case_metrics_reorder,
                    self.kb.metrics_score,
                )

                for item in metrics:
                    weight = self.kb.metrics_score[item]
                    self.score += weight / max(
                        len(f_metrics_reorder), len(case_metrics_reorder)
                    )
            elif self.f_metrics and self.use_metrics:
                update_score(metrics, self.kb.metrics_score, self.f_metrics)

            update_score(
                traces, self.kb.traces_score, self.f_traces
            ) if self.f_traces and self.use_traces else None
            update_score(
                logs, self.kb.logs_score, self.f_logs
            ) if self.f_logs and self.use_logs else None
            update_score(
                cmds, self.kb.cmds_score, self.f_cmds
            ) if self.f_cmds and self.use_cmds else None

        self.score /= case_num

        return self.score

    def rename(self, fingerprint, order=False):
        rename_instance = dict()
        if fingerprint is None:
            return rename_instance
        types = fingerprint.keys()

        for one in types:
            for clue in fingerprint[one]:
                idx = clue["index"]
                action = clue["action"]
                order = clue["order"] if "order" in clue else 0
                clue_name = one + "-" + str(idx) + "-" + str(action)
                rename_instance.setdefault(order, [])
                rename_instance[order].append(clue_name)
        return rename_instance

    def analyse_case(self):

        kb_case_types = self.kb.kb.keys()

        for kb_case_type in kb_case_types:

            for kb_case in self.kb.kb[kb_case_type]:
                kb_anomalies = kb_case["anomalies"]

                kb_metrics = (
                    kb_anomalies["metrics"]
                    if "metrics" in kb_anomalies
                    else None
                )
                kb_traces = (
                    kb_anomalies["traces"] if "traces" in kb_anomalies else None
                )
                kb_logs = (
                    kb_anomalies["logs"] if "logs" in kb_anomalies else None
                )
                kb_cmds = (
                    kb_anomalies["cmds"] if "cmds" in kb_anomalies else None
                )

                kb_rename_metrics = self.rename(kb_metrics)
                kb_rename_traces = self.rename(kb_traces)
                kb_rename_logs = self.rename(kb_logs)
                kb_rename_cmds = self.rename(kb_cmds)

                self.score = self.cal_similarity(
                    kb_rename_metrics,
                    kb_rename_traces,
                    kb_rename_logs,
                    kb_rename_cmds,
                    hierarchy="case",
                )
                self.case_scores[kb_case["experiment"]] = self.score
