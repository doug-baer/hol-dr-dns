#!/usr/bin/env python3
import argparse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
DNS_SERVER_URL = "https://dns.vcf.lab:443"
# Create an API token in your Technitium instance and put it here
API_TOKEN = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

DNS_ZONE = "vcf.lab"

# set up the records with the hostnames and the prod/DR IP addresses
VMS_TO_MOVE = {
    "acct-app-01": { "prod": "10.1.11.130", "DR": "10.2.11.130" },
    "acct-db-01":  { "prod": "10.1.11.131", "DR": "10.2.11.131" },
    "acct-web-01": { "prod": "10.1.11.132", "DR": "10.2.11.132" }
}
# ---------------------

# --- NOTHING TO SEE HERE ---
def add_dns_record(zone, host, ip):
    url = f"{DNS_SERVER_URL}/api/zones/records/add"
    payload = {
        "token": API_TOKEN,
        "zone": zone,
        "domain": f"{host}.{zone}",
        "type": "A",
        "ipAddress": ip,
        "ttl": 3600,
        "ptr": "true"
    }
    response = requests.get(url, params=payload, verify=False)
    return response.json()

def delete_dns_record(zone, host, ip):
    url = f"{DNS_SERVER_URL}/api/zones/records/delete"
    payload = {
        "token": API_TOKEN,
        "zone": zone,
        "domain": f"{host}.{zone}",
        "type": "A",
        "ipAddress": ip,
        "ptr": "true"
    }
    response = requests.get(url, params=payload, verify=False)
    return response.json()

def main():

    parser = argparse.ArgumentParser(description="Manage DR Failover and Failback for Technitium DNS.")
    parser.add_argument(
        "-Failback", "--failback", "-f",
        action="store_true",
        help="Switches 'prod' and 'DR' IP mapping to undo the migration."
    )
    args = parser.parse_args()

    # Determine mode string and map IPs based on flag
    if args.failback:
        update_mode = 'FAILBACK (return to Production)'
    else:
        update_mode = 'FAILOVER'

    print(f"** Starting DNS update...\n** DR Mode: {update_mode}\n")
    
    for vm, ips in VMS_TO_MOVE.items():
        vm_fqdn = f"{vm}.{DNS_ZONE}"
        
        # If failback, we swap 'prod' and 'DR' targets
        from_ip = ips['DR'] if args.failback else ips['prod']
        to_ip = ips['prod'] if args.failback else ips['DR']
        
        # 1. Delete the active record
        print(f"Deleting: {vm_fqdn} * {from_ip}")
        del_res = delete_dns_record(DNS_ZONE, vm, from_ip)
        
        if del_res.get("status") == "ok":
            print(f" * Successfully deleted {vm_fqdn}")
            
            # 2. Add the target record
            print(f"Creating: {vm_fqdn} * {to_ip}")
            add_res = add_dns_record(DNS_ZONE, vm, to_ip)
            
            if add_res.get("status") == "ok":
                print(f" * Successfully created {vm_fqdn}")
            else:
                print(f" * Failed to create new record: {add_res.get('errorMessage')}")
        else:
            print(f" * Failed to delete old record: {del_res.get('errorMessage')}. Skipping creation for safety.")
            
        print("-" * 40)

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")

