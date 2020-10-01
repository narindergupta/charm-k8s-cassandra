#!/usr/bin/env python3
# Copyright 2020 Canonical Ltd..
# See LICENSE file for licensing details.

import logging
import yaml
import time

import glob
import json
import os
import subprocess
import time
import socket

from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    UnknownStatus,
    WaitingStatus,
    ModelError,
)
import ops.lib

logger = logging.getLogger(__name__)


class K8SCassandraCharm(CharmBase):
    """ This charm class is main Class of the
    K8s Cassandra charm.
    """
    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.status_action, self._on_status_action)
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade)
        self.framework.observe(self.on.remove, self._on_remove)
        self._stored.set_default(
            recently_started=True,
            config_propagated=True,
            image="",
        )

    def _on_start(self, event):
        """ This method is for start of charm event. """
        self.set_juju_pod_spec()
        self.wait_for_pod_readiness()
        self._stored.recently_started = True
        self._stored.config_propagated = True
        self._stored.image = self.model.config["image"]

    def _on_config_changed(self, event):
        """ This method is for config change event. """
        self.wait_for_pod_readiness()
        currentimage = self.model.config["image"]
        if currentimage not in self._stored.image:
            logger.debug("found a new image: %r", currentimage)
            self.set_juju_pod_spec()
            self.wait_for_pod_readiness()
            self._stored.image = currentimage

    def _on_update_status(self, event):
        """ This method with update status every juju refresh cycle. """
        self.wait_for_pod_readiness()

    def _on_upgrade(self, event):
        """ This method with upgrade Cassandra. """
        self._on_start(event)

    def _on_status_action(self, event):
        """ This method with run the action on Cassandra. """
        nodecommand = event.params["command"]
        if not nodecommand:
            event.fail(nodecommand)
        else:
            outputmes = self.runNodeTool(nodecommand)
            event.set_results({nodecommand: outputmes})

    def _on_remove(self, event):
        """ This method with remove Cassandra instance. """
        nodecommand = event.params["command"]
        #self.runNodeTool("decommission")
        return true

    def runNodeTool(self, action):
        """ This method with run nodetool Command. """
        nodecommand = "nodetool " + action
        statusout = subprocess.check_output(nodecommand,
                               universal_newlines=True,shell=True)
        logger.debug(statusout)
        if statusout:
            return  statusout
        else:
            return "cassandra is Not running"

    def build_juju_unit_status(self, pod_status):
        """ This method with build the charm status based on container. """
        if pod_status.is_unknown:
            unit_status = MaintenanceStatus("Waiting for pod to appear")
        elif not pod_status.is_running:
            unit_status = MaintenanceStatus("Pod is starting")
        elif pod_status.is_running and not pod_status.is_ready:
            unit_status = MaintenanceStatus("Pod is getting ready")
        elif pod_status.is_running and pod_status.is_ready:
            unit_status = ActiveStatus("Pod is Ready")
        else:
            # Covering a "variable referenced before assignment" linter error
            unit_status = BlockedStatus(
                "Error: Unexpected pod_status received: {0}".format(
                    pod_status.raw_status
                )
            )

        return unit_status

    def ensure_config_is_reloaded(event, state):
        """ This method with reload the config for container. """
        juju_model = self.model.name
        juju_app = self.model.app.name

        # CofigMap are synchronized so there's no need to reload.
        if state.recently_started:
            state.recently_started = False
            return

        config_was_changed_post_startup = \
            not state.recently_started and state.config_propagated
        config_needs_reloading = \
            not state.recently_started and not state.config_propagated

        if config_was_changed_post_startup:
            # We assume that the new config hasn't propagated all the way up
            # to the Cassandra container.
            state.config_propagated = False

            #self.model.unit.status = 
            #     MaintenanceStatus("Waiting for new config to propagate to unit")
            logger.debug("Config not yet propagated. Deferring.")
            # The rest of this event handler is deferred so that Juju can continue
            # with the config-change cycle, apply the new config to the ConfigMap
            # and allow kubernetes to propagate that the the mounted volume in
            # the Cassandra pod.
            event.defer()
            return
        return

    def set_juju_pod_spec(self):
        """ This method with reload the config for container. """
        logging.info('MAKING POD SPEC')
        if not self.unit.is_leader():
            logging.debug("Unit is not a leader, skip pod spec configuration")
            # Although PodSpec will not be altered, the pod provisioning process
            # still have to continue
            return True

        logging.debug("Building Juju pod spec")
        with open("templates/spec_template.yaml") as spec_file:
            podSpecTemplate = spec_file.read()
        data = {
            "name": self.model.app.name,
            "model": self.model.name,
            "docker_image": self.model.config['image'],
            "cluster_name": self.model.config['cluster_name'],
            "max_heap_size": self.model.config['max_heap_size'],
            "heap_newsize": self.model.config['heap_newsize'],
            "datacenter": self.model.config['datacenter'],
            "rack": self.model.config['rack'],
            "jvm_opt": self.model.config['jvm_opt'],
        }
        logging.info(data)
        podSpec = podSpecTemplate % data
        juju_pod_spec = yaml.load(podSpec)
        self.model.pod.set_spec(juju_pod_spec)
        return True

    def wait_for_pod_readiness(self):
        """ This method with create a pod and waut for ready state. """
        juju_model = self.model.name
        juju_app = self.model.app.name
        juju_unit = self.model.unit.name
        pod_is_ready = False
        k8s = ops.lib.use("k8s", 0, "chipaca@canonical.com")

        # TODO: Fail by timeout, if pod will never go to the Ready state?
        logging.debug("Checking k8s pod readiness")
        k8s_pod_status = k8s.get_pod_status(juju_model=juju_model,
                                            juju_app=juju_app,
                                            juju_unit=juju_unit)
        logging.debug("Received k8s pod status: {0}".format(k8s_pod_status))
        juju_unit_status = self.build_juju_unit_status(k8s_pod_status)
        logging.debug("Built unit status: {0}".format(juju_unit_status))
        self.model.unit.status = juju_unit_status


if __name__ == "__main__":
    """ Main of the charm class instantiation. """
    main(K8SCassandraCharm)
