from k8sClient import K8sClient
from configOperators import ConfigCVO
import sys
from concurrent.futures import Future
from typing import Dict

class ExtraConfigCNO:
    def __init__(self, cc):
        self._cc = cc

    def run(self, cfg, futures: Dict[str, Future]) -> None:
        [f.result() for (_, f) in futures.items()]
        print("Running post config step to load custom CNO")
        iclient = K8sClient(self._cc["kubeconfig"])

        if "image" not in cfg:
            print("Error image not provided to load custom CNO")
            sys.exit(-1)

        image = cfg["image"]

        print(f"Image {image} provided to load custom CNO")

        patch = f"""spec:
  template:
    spec:
      containers:
      - name: network-operator
        image: {image}
"""

        configCVO = ConfigCVO()
        configCVO.scaleDown(iclient)
        iclient.oc(f'patch -p "{patch}" deploy network-operator -n openshift-network-operator')


def main():
    pass


if __name__ == "__main__":
    main()