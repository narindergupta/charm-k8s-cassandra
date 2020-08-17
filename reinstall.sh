rm -rf build
charmcraft build
juju kill-controller k8s-cloud -y  -t 5s
juju bootstrap microk8s k8s-cloud
juju add-model cassandra
juju model-config logging-config="<root>=DEBUG"
juju deploy ./charm-k8s-cassandra.charm
