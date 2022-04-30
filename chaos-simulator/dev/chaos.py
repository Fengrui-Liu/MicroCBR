import os
import yaml
import datetime
import logging
import subprocess

_LOGGER = logging.getLogger(__name__)


class Chaos:
    def __init__(self):
        self.name = None
        self.duration = None
        self.creation_time = None
        self.namespace = None
        self.kind = None
        self.is_executed = False

    def load(
        self, f_path: str = "",
    ):
        """Load chaos from template file

        Args:
            f_path (str, optional): Chaos template file path. Defaults to "".

        """

        if f_path == "" or not os.path.exists(f_path):
            self.creation_time = datetime.datetime.now(tz=datetime.timezone.utc)
            self.duration = "0s"
            _LOGGER.warn("No chaos file: {}, set no chaos".format(f_path))
            return None

        f = open(f_path, "r", encoding="utf-8")
        data = f.read()
        f.close()
        data = yaml.safe_load(data)
        self.name = data["metadata"]["name"]
        self.namespace = list(data["spec"]["selector"]["pods"])[0]
        self.duration = (
            data["spec"]["duration"] if "duration" in data["spec"] else "1s"
        )
        self.kind = data["kind"]

    def execute(self, f_path: str, namespace: str):
        """Execute the loaded chaos

        Args:
            f_path (str): Chaos template file path.
            namespace (str): Chaos namespace.

        Returns:
            stat: Apply result
        """
        self.load(f_path=f_path)

        stat = None

        if self.name is not None:
            self.creation_time = datetime.datetime.now(tz=datetime.timezone.utc)
            self.is_executed = True

            cmd = "kubectl apply -f {f_path} -n {namespace}".format(
                f_path=f_path, namespace=namespace
            )
            stat = subprocess.run(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            if stat.returncode != 0:
                _LOGGER.error(
                    "Can not deploy chaos. Return code: {}. {}".format(
                        stat.returncode, stat.stderr.decode("utf-8")
                    )
                )
                return None

        return stat

    def status(self, kind: str = None, name: str = None, namespace: str = None):
        """Check chaos status

        Args:
            kind (str, optional): Chaos object kind. Defaults to None.
            name (str, optional): Chaos name. Defaults to None.
            namespace (str, optional): Chaos namespace. Defaults to None.

        Returns:
            stat: Chaos status
        """

        if kind is not None and namespace is not None and name is not None:
            self.kind = kind
            self.name = name
            self.namespace = namespace
        elif (
            self.kind is not None
            and self.namespace is not None
            and self.name is not None
        ):
            _LOGGER.info("Use default kind and namespace")
        else:
            _LOGGER.info("Please define chaos kind and namespace")

        if self.name is None:
            _LOGGER.warn("No chaos initialized")
            return None

        cmd = "kubectl describe {kind} {name} -n chaos-testing".format(
            kind=self.kind, name=self.name
        )

        stat = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if stat.returncode != 0:
            _LOGGER.error(
                "Can not find chaos deploy. Return code: {}. {}".format(
                    stat.returncode, stat.stderr.decode("utf-8")
                )
            )

            return None

        stat = yaml.safe_load(stat.stdout)
        self.creation_time = stat["Metadata"]["Creation Timestamp"]
        self.name = stat["Name"]
        self.duration = (
            stat["Spec"]["Duration"] if "Duration" in stat["Spec"] else "1s"
        )
        self.namespace = stat["Namespace"]
        self.kind = stat["Kind"]
        self.is_executed = True

        if stat["Status"]["Experiment"]["Desired Phase"] == "Stop":
            _LOGGER.info("Chaos {} is finished".format(self.name))
        elif stat["Status"]["Experiment"]["Desired Phase"] == "Run":
            _LOGGER.info("Chaos {} is running".format(self.name))
        else:
            _LOGGER.warn("Unsupported chaos {} status".format(self.name))

        return stat

    def delete(self, kind: str = None, name: str = None, namespace: str = None):
        """Delete deployed chaos

        Args:
            kind (str, optional): Chaos object kind. Defaults to None.
            name (str, optional): Chaos name. Defaults to None.
            namespace (str, optional): Chaos namespace. Defaults to None.

        Returns:
            stat: Chaos status
        """

        self.status(kind=kind, name=name, namespace=namespace)

        cmd = "kubectl delete {kind} {name} -n {namespace}".format(
            kind=self.kind, name=self.name, namespace=self.namespace
        )

        stat = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if stat.returncode != 0:
            _LOGGER.error(
                "Can not find chaos deploy. Return code: {}. {}".format(
                    stat.returncode, stat.stderr.decode("utf-8")
                )
            )

            return None

        _LOGGER.info("Success delete chaos {}".format(self.name))

        return None
