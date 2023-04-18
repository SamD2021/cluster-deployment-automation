from k8sClient import K8sClient


class ConfigCVO:
    def scaleDown(self, client: K8sClient) -> None:
        print("Scaling down the cluster-version-operator deployment.")
        client.oc("scale --replicas=0 deploy/cluster-version-operator -n openshift-cluster-version")

class ConfigCNO:
    def scaleDown(self, client: K8sClient) -> None:
        print("Scaling down the cluster-network-operator deployment.")
        client.oc("scale --replicas=0 deploy/network-operator -n openshift-network-operator")


def main():
    pass


if __name__ == "__main__":
    main()