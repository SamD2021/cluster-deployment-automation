import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Any
from contextlib import contextmanager
import time, host
from logger import logger

@dataclass
class KeaReservation:
    hw_address: str
    ip_address: str
    hostname: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "hw-address": self.hw_address,
            "ip-address": self.ip_address, 
            "hostname": self.hostname
        }

@dataclass  
class KeaSubnet:
    subnet: str
    pools: List[Dict[str, str]]
    option_data: List[Dict[str, str]]
    reservations: List[KeaReservation]
    id: int = 1  # Add subnet ID with default value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subnet": self.subnet,
            "pools": self.pools,
            "option-data": self.option_data,
            "reservations": [res.to_dict() for res in self.reservations]
        }
    
class KeaConfig:
    def __init__(self, interface: str = "eno12409np1"):
        self.interface = interface
        self.subnets: List[KeaSubnet] = []
        
    def add_subnet(self, subnet: KeaSubnet):
        self.subnets.append(subnet)
        
    def to_json(self) -> str:
        config = {
            "Dhcp4": {
                "interfaces-config": {
                    "interfaces": [self.interface],
                    "dhcp-socket-type": "udp",
                    "outbound-interface": "same-as-inbound"
                },
                "subnet4": [subnet.to_dict() for subnet in self.subnets],
                "loggers": [{
                    "name": "kea-dhcp4",
                    "output_options": [{"output": "/var/log/kea/kea-dhcp4.log"}],
                    "severity": "INFO"
                }]
            }
        }
        return json.dumps(config, indent=2) 

@contextmanager
def kea_paused():
    lh = host.LocalHost()
    was_running = lh.run("systemctl is-active --quiet kea-dhcp4.service").success()
    if was_running:
        logger.info("stopping kea-dhcp4")
        lh.run("systemctl stop kea-dhcp4.service")
        time.sleep(1)          # give raw socket time to vanish
    try:
        yield
    finally:
        if was_running:
            logger.info("starting kea-dhcp4")
            lh.run("systemctl start kea-dhcp4.service") 