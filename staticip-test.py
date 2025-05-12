import subprocess
import random
import time
import re
import ipaddress
import netifaces

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()

def get_interface_info(interface):
    try:
        addrs = netifaces.ifaddresses(interface)
        ip = addrs[netifaces.AF_INET][0]['addr']
        netmask = addrs[netifaces.AF_INET][0]['netmask']
        gateway = netifaces.gateways()['default'][netifaces.AF_INET][0]
        dns = []

        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    dns.append(line.strip().split()[1])
        return ip, netmask, gateway, dns[0] if dns else None
    except Exception as e:
        print(f"Error getting interface info: {e}")
        return None, None, None, None

def perform_reachability_tests(gateway, dns, external="www.google.com"):
    print("\nReachability Tests:")
    for target in [gateway, dns, external]:
        print(f"Pinging {target}...", end=" ")
        result = subprocess.run(["ping", "-c", "2", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("Reachable ✅")
        else:
            print("Unreachable ❌")

def get_random_ip_in_subnet(ip, netmask):
    subnet = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
    host_ips = list(subnet.hosts())
    new_ip = random.choice([h for h in host_ips if str(h) != ip])
    return str(new_ip)

def set_static_ip(interface, ip, netmask, gateway, dns):
    print(f"\nSetting static IP {ip} on {interface}...")
    subprocess.run(f"sudo ip addr flush dev {interface}", shell=True)
    subprocess.run(f"sudo ip addr add {ip}/{netmask} dev {interface}", shell=True)
    subprocess.run(f"sudo ip link set dev {interface} up", shell=True)
    subprocess.run(f"sudo ip route add default via {gateway}", shell=True)
    
    resolv_conf = f"nameserver {dns}\n"
    with open("/etc/resolv.conf", "w") as f:
        f.write(resolv_conf)
    print("Static IP configured.")

def reset_to_dhcp(interface):
    print(f"\nResetting {interface} to DHCP...")
    subprocess.run(f"sudo ip addr flush dev {interface}", shell=True)
    subprocess.run(f"sudo dhclient -r {interface}", shell=True)
    subprocess.run(f"sudo dhclient {interface}", shell=True)
    print("DHCP configuration restored.")

def main():
    interface = "eth0"  # change to your interface
    print(f"Requesting DHCP lease on {interface}...")
    subprocess.run(f"sudo dhclient -r {interface}", shell=True)
    subprocess.run(f"sudo dhclient {interface}", shell=True)
    time.sleep(5)

    ip, netmask, gateway, dns = get_interface_info(interface)
    if not ip or not gateway:
        print("Failed to get DHCP configuration.")
        return

    print(f"\nDHCP Lease Info:\n  IP: {ip}\n  Netmask: {netmask}\n  Gateway: {gateway}\n  DNS: {dns}")
    perform_reachability_tests(gateway, dns)

    static_ip = get_random_ip_in_subnet(ip, netmask)
    set_static_ip(interface, static_ip, netmask, gateway, dns)
    perform_reachability_tests(gateway, dns)

    # Optional reset to DHCP
    reset_to_dhcp(interface)

if __name__ == "__main__":
    main()
