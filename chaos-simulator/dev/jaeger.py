import os
import json
import requests
import logging

_LOGGER = logging.getLogger(__name__)


class Jaeger_Client:
    def __init__(self, url: str) -> None:
        self.jaeger = url
        self.params = "service="
        self.service = None

    def get_traces(self, service: str, limit: int = 20):
        """Get Jaeger traces for a service

        Args:
            service (str): Target service
            limit (int, optional): Trace limitations. Defaults to 20.

        Raises:
            err: Get traces error

        Returns:
            traces: traces
        """
        self.service = service

        TRACES_ENDPOINT = "{jaeger}/api/traces?limit={limit}&{params}{service}".format(
            jaeger=self.jaeger,
            limit=limit,
            params=self.params,
            service=service,
        )

        try:
            response = requests.get(TRACES_ENDPOINT)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise err

        print(response.text)
        response = json.loads(response.text)
        traces = response["data"]
        return traces

    def get_services(self):
        """Get all services

        Raises:
            err: Get services error

        Returns:
            service: services
        """
        SERVICES_ENDPOINT = self.jaeger + "/api/services"
        try:
            response = requests.get(SERVICES_ENDPOINT)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise err

        response = json.loads(response.text)
        services = response["data"]
        self.services = services

        return services

    def write_traces(self, directory, traces):
        """
        Write traces locally to files
        """
        for trace in traces:
            trace_id = trace["traceID"]
            path = directory + "/" + trace_id + ".json"
            with open(path, "w") as fd:
                fd.write(json.dumps(trace))

    def write_traces_all(self, service="all"):

        svc_list = []
        if service == "all":
            svc_list = self.get_services()
        elif isinstance(service, str):
            svc_list = [service]
        elif isinstance(service, list):
            pass
        else:
            _LOGGER.error("Unsupported service type")
            return

        # Pull traces for all the services & store locally as json files
        for service in svc_list:
            if not os.path.exists(service):
                f_path = "../jaeger/{service}/".format(service=service)
                os.makedirs(os.path.dirname(f_path), exist_ok=True)
            traces = self.get_traces(service)
            self.write_traces(f_path, traces)
