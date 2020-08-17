# Copyright 2020 Canonical Ltd.
# Licensed under the Apache License, Version 2.0; see LICENCE file for details.

import http.client
import json
import logging
import ssl
import sys

from .version import version as __version__  # noqa: F401 (imported but unused)

__all__ = ("get_pod_status", "APIServer", "PodStatus")

logger = logging.getLogger()


def get_pod_status(juju_model, juju_app, juju_unit):
    namespace = juju_model

    path = "/api/v1/namespaces/{}/pods?labelSelector=juju-app={}".format(namespace, juju_app)

    api_server = APIServer()
    response = api_server.get(path)
    status_dict = None

    if response.get("kind", "") == "PodList" and response["items"]:
        for item in response["items"]:
            if item["metadata"]["annotations"].get("juju.io/unit") == juju_unit:
                status_dict = item
                break

    return PodStatus(status_dict)


class APIServer:
    """
    Wraps the logic needed to access the k8s API server from inside a pod.
    It does this by reading the service account token which is mounted onto
    the pod.
    """

    _SERVICE_ACCOUNT_CA = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    _SERVICE_ACCOUNT_TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"

    def get(self, path):
        return self.request("GET", path)

    def request(self, method, path):
        with open(self._SERVICE_ACCOUNT_TOKEN, "rt", encoding="utf8") as token_file:
            kube_token = token_file.read()

        # drop this when dropping support for 3.5
        if sys.version_info < (3, 6):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        else:
            ssl_context = ssl.SSLContext()

        ssl_context.load_verify_locations(self._SERVICE_ACCOUNT_CA)

        headers = {"Authorization": "Bearer {}".format(kube_token)}

        host = "kubernetes.default.svc"
        conn = http.client.HTTPSConnection(host, context=ssl_context)
        logger.debug("%s %s/%s", method, host, path)
        conn.request(method=method, url=path, headers=headers)

        return json.loads(conn.getresponse().read())


class PodStatus:
    def __init__(self, status_dict):
        self._status = status_dict

    @property
    def is_ready(self):
        if not self._status:
            return False

        for condition in self._status["status"]["conditions"]:
            if condition["type"] == "ContainersReady":
                return condition["status"] == "True"

        return False

    @property
    def is_running(self):
        if not self._status:
            return False

        return self._status["status"]["phase"] == "Running"

    @property
    def is_unknown(self):
        return not self._status
