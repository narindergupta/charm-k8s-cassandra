rm -rf build
charmcraft build
juju kill-controller k8s-cloud -y  -t 5s
juju bootstrap microk8s k8s-cloud
juju add-model cassandramodel
juju model-config logging-config="<root>=DEBUG"
juju deploy ./cassandra.charm
