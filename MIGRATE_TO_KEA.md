# Migration Guide: ISC DHCP to Kea DHCP

This guide explains how to migrate CDA from ISC DHCP to Kea DHCP on RHEL 10+.

## Why Migrate?

- **RHEL 10 Compatibility**: ISC DHCP is deprecated in RHEL 10
- **Clean Architecture**: Separates DHCP (Kea) from DNS (dnsmasq) 
- **Modern Features**: JSON configuration, REST API, better logging
- **No More Hacks**: Eliminates the dnsmasq-dhcpd compatibility wrapper

## Prerequisites

### Install Kea DHCP Server

```bash
# Install Kea on RHEL 10
sudo dnf install -y kea-dhcp4

# Enable and start the service (it will initially fail until configured)
sudo systemctl enable kea-dhcp4
```

### Remove Old DHCP Service (if using the compatibility hack)

```bash
# If you have the dnsmasq-dhcpd.conf hack, remove it
sudo systemctl stop dhcpd.service 2>/dev/null || true
sudo systemctl disable dhcpd.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/dhcpd.service
sudo rm -f /usr/local/bin/dhcpd-to-dnsmasq.sh
sudo rm -f /etc/dnsmasq-dhcpd.conf

# Stop conflicting dnsmasq instance
sudo systemctl stop dnsmasq.service 2>/dev/null || true
sudo systemctl disable dnsmasq.service 2>/dev/null || true
```

## Migration Steps

### 1. Files Changed
- `keaConfig.py` - New Kea configuration module
- `dhcpConfig.py` - Updated to use Kea instead of ISC DHCP
- Legacy classes kept for backward compatibility

### 2. Configuration Changes
- **Old**: `/etc/dhcp/dhcpd.conf` (ISC DHCP format)
- **New**: `/etc/kea/kea-dhcp4.conf` (JSON format)

### 3. Service Changes
- **Old**: `systemctl restart dhcpd`
- **New**: `systemctl restart kea-dhcp4`

## Test the Migration

### 1. Test DHCP Configuration
```bash
# Deploy a test cluster to verify DHCP works
cd cluster-deployment-automation
./cda.py ../hack/cluster-configs/config-dpu.yaml deploy

# Check Kea service status
sudo systemctl status kea-dhcp4

# Check Kea configuration
sudo cat /etc/kea/kea-dhcp4.conf

# Check Kea logs
sudo journalctl -u kea-dhcp4 -f
```

### 2. Verify DHCP Reservations
```bash
# Check if your DPU gets the correct IP
# Look for DHCP DISCOVER/OFFER/REQUEST/ACK in Kea logs
sudo tail -f /var/log/kea-dhcp4.log
```

## DNS Configuration (Fix Conflicts)

Since you no longer have conflicting DHCP in dnsmasq, you can now use dnsmasq purely for DNS:

### Fix DNS Resolution
```bash
# Ensure dnsmasq handles cluster DNS properly
sudo tee /etc/dnsmasq.d/servers/cda-servers.conf << 'EOF'
# Written by cluster-deployment-automation for resolving cluster names.
server=/*.api.ocpcluster.redhat.com/*api-int.ocpcluster.redhat.com/#
server=/apps.ocpcluster.redhat.com/192.168.122.101
server=/api.ocpcluster.redhat.com/192.168.122.99
server=/api-int.ocpcluster.redhat.com/192.168.122.99
EOF

# Enable DNS in dnsmasq (remove port=0 restriction)
sudo sed -i '/^port=0/d' /etc/dnsmasq.d/cda.conf

# Point resolv.conf to local dnsmasq
sudo ln -snf resolv.conf.cda-local /etc/resolv.conf

# Restart dnsmasq for DNS only
sudo systemctl restart dnsmasq.service
```

## Troubleshooting

### Kea Service Fails to Start
```bash
# Check Kea configuration syntax
sudo kea-dhcp4 -t /etc/kea/kea-dhcp4.conf

# Check Kea logs
sudo journalctl -u kea-dhcp4 -n 50
```

### DHCP Client Not Getting IP
```bash
# Check if Kea is listening on the right interface
sudo netstat -tulpn | grep :67

# Check Kea lease database
sudo kea-lfc -c /etc/kea/kea-dhcp4.conf

# Verify MAC address in configuration matches client
sudo grep -A5 -B5 "MAC_ADDRESS" /etc/kea/kea-dhcp4.conf
```

### DNS Resolution Issues  
```bash
# Test cluster DNS resolution
nslookup default-route-openshift-image-registry.apps.ocpcluster.redhat.com

# Check dnsmasq status
sudo systemctl status dnsmasq.service

# Verify resolv.conf points to local dnsmasq
cat /etc/resolv.conf | grep 127.0.0.1
```

## Rollback (if needed)

```bash
# Stop Kea
sudo systemctl stop kea-dhcp4
sudo systemctl disable kea-dhcp4

# Restore ISC DHCP (if package still available)
sudo dnf install -y dhcp-server
sudo systemctl enable dhcpd
sudo systemctl start dhcpd

# Or restore the dnsmasq hack
# (recreate /etc/dnsmasq-dhcpd.conf and systemd service)
```

## Benefits After Migration

✅ **Clean separation**: Kea (DHCP) + dnsmasq (DNS only)  
✅ **No port conflicts**: Each service uses its designated ports  
✅ **Better logging**: JSON-structured Kea logs  
✅ **RHEL 10 native**: No compatibility hacks needed  
✅ **Future-proof**: Modern DHCP server with active development 