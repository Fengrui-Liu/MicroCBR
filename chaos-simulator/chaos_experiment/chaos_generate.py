import logging
import os
import subprocess
from typing import Union
import yaml

_LOGGER = logging.getLogger(__name__)


class Chaos_Generate:
    def __init__(self):
        self.template = None
        self.name = "default"
        self.type = None

    def load_template(self, f_path: str) -> Union[dict, None]:
        """Load chaos template

        Args:
            f_path (str): chaos template path

        Returns:
            dict: chaos template
        """

        if not os.path.exists(f_path):
            _LOGGER.error("Error chaos template path, %s" % (f_path))
            return None

        f = open(f_path, "r", encoding="utf-8")
        data = f.read()
        f.close()
        self.template = yaml.safe_load(data)
        self.name = self.template["metadata"]["name"]
        self.type = self.template["kind"]

        return self.template

    def generate_by_pods(
        self,
        namespace: str,
        pods: list,
        types: str = "Serial",
        output_dir: str = "./exp/",
    ):
        """Generate chaos experiment by pods

        Args:
            namespace (str): microservice namespace.
            pods (list): A list of pods to inject.
            types (str, optional): Serial, once a time. Defaults to "Serial".
            output_dir (str, optional): Data collection path. Defaults to "./exp/".
        """
        if self.template is None:
            _LOGGER.error("Error, no chaos template loaded")
            return

        self.clear_experiments(
            types=types, namespace=namespace, pods=pods, output_dir=output_dir,
        )

        _LOGGER.info("Remove old experiments")

        for pod in pods:
            name_config = self.name + "-" + namespace + "-" + pod
            self.template["metadata"]["name"] = name_config
            pod_config = {namespace: [pod]}
            self.template["spec"]["selector"]["pods"] = pod_config

            if "target" in self.template["spec"]:
                self.template["spec"]["target"]["selector"]["namespaces"] = [
                    namespace
                ]

            f_path = output_dir + "/" + types + "/" + name_config + ".yaml"
            os.makedirs(os.path.dirname(f_path), exist_ok=True)
            with open(f_path, "w") as f:
                yaml.safe_dump(self.template, f)

        return

    def clear_experiments(
        self,
        namespace: str,
        pods: list,
        types: str = "Serial",
        output_dir: str = "./experiments/",
    ):
        """Clear an existing experiment

        Args:
            namespace (str): microservice namespace
            pods (list): A list of injected pods
            types (str, optional): Serial experiment, once a time. Defaults to "Serial".
            output_dir (str, optional): Collection data dir. Defaults to "./experiments/".
        """
        for pod in pods:
            name_config = self.name + "-" + namespace + "-" + pod
            f_path = output_dir + "/" + types + "/" + name_config + ".yaml"
            if os.path.exists(f_path):
                cmd = "kubectl delete -f {f_path} -n {namespace}".format(
                    f_path=f_path, namespace=namespace
                )
                stat = subprocess.run(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if stat.returncode == 0:
                    _LOGGER.info("Remove experiment %s" % (f_path))
                elif stat.returncode == 1:
                    _LOGGER.info("Experiment %s not exist" % (f_path))
                else:
                    _LOGGER.error(
                        "Return code: {}. {}".format(
                            stat.returncode, stat.stderr.decode("utf-8")
                        )
                    )
                os.remove(f_path)
            else:
                _LOGGER.warn("YAML file %s not exist" % (f_path))
