from clustersConfig import ClustersConfig
from concurrent.futures import Future
from typing import Optional
from logger import logger
from clustersConfig import ExtraConfigArgs
import host
from imageRegistry import InClusterRegistry, LocalRegistry, RegistryType


def ExtraConfigImageRegistry(cc: ClustersConfig, cfg: ExtraConfigArgs, futures: dict[str, Future[Optional[host.Result]]]) -> None:
    [f.result() for (_, f) in futures.items()]
    logger.info("Running post config step to enable cluster registry")

    if cfg.registry_type == RegistryType.IN_CLUSTER.value:
        # Reference documentation:
        # https://docs.openshift.com/container-platform/4.15/registry/configuring-registry-operator.html


        logger.info("Redeploying in-cluster registry...")
        in_cluster_reg.undeploy()

        # Deploy in-cluster registry with configurable storage size
        logger.info("Deploying in-cluster registry...")
        in_cluster_reg.deploy()

    elif cfg.registry_type == RegistryType.LOCAL.value:
        lh = host.LocalHost()
        local_reg = LocalRegistry(lh)
        local_reg.deploy()


def main() -> None:
    pass


if __name__ == "__main__":
    main()
