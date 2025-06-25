from concurrent.futures import Future
from typing import Optional
from k8sClient import K8sClient
from logger import logger
from clustersConfig import ClustersConfig, ExtraConfigArgs
import host
from imageRegistry import InClusterRegistry, LocalRegistry, RegistryType
from clusterStorage import create_cluster_storage, StorageType


def ExtraConfigImageRegistry(cc: ClustersConfig, cfg: ExtraConfigArgs, futures: dict[str, Future[Optional[host.Result]]]) -> None:
    [f.result() for (_, f) in futures.items()]
    logger.info("Running post config step to enable cluster registry")

    if cfg.registry_type == RegistryType.IN_CLUSTER.value:
        # Reference documentation:
        # https://docs.openshift.com/container-platform/4.15/registry/configuring-registry-operator.html

        # Get registry node information
        registry_node = cc.get_registry_storage_node()

        logger.info(f"Using node '{registry_node.name}' for registry storage")

        registry_storage_size = cc.get_registry_storage_node().in_cluster_registry_storage_size
        # Create ClusterStorage instance targeting the specific registry node
        from clusterStorage import HostPathStorage

        cluster_storage = create_cluster_storage(kubeconfig_path=cc.kubeconfig, storage_type=StorageType.HOSTPATH, target_node_hostname=registry_node.name, storage_path="/var/lib/registry-storage")
        # Ensure we have HostPathStorage for registry storage
        if not isinstance(cluster_storage, HostPathStorage):
            logger.error_and_exit("Expected HostPathStorage implementation for registry storage")

        in_cluster_reg = InClusterRegistry(kubeconfig=cc.kubeconfig, storage_class=cluster_storage.get_storage_class_name(), storage=cluster_storage, storage_size=registry_storage_size)

        logger.info("Redeploying in-cluster registry...")
        in_cluster_reg.undeploy()
        cluster_storage.undeploy_storage()
        # Deploy storage foundation (StorageClass + directories)
        logger.info("Deploying storage foundation...")
        cluster_storage.deploy_storage()

        # Deploy in-cluster registry with configurable storage size
        logger.info("Deploying in-cluster registry...")
        in_cluster_reg.deploy()

    elif cfg.registry_type == RegistryType.LOCAL.value:
        lh = host.LocalHost()
        client = K8sClient(cc.kubeconfig)
        local_reg = LocalRegistry(lh)
        local_reg.ensure_running(delete_all=True)
        local_reg.trust()
        local_reg.ocp_trust(client)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
