#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_ec2 import *

# Import stock packages
import datetime
import sys


########################################
##### Helpers
########################################

def new_ip_info(region, instance_id, is_elastic):
    ip_info = {}
    ip_info['region'] = region
    ip_info['instance_id'] = instance_id
    ip_info['is_elastic'] = is_elastic
    return ip_info

def new_prefix(ip_prefix, obj): 
    obj['ip_prefix'] = ip_prefix
    return obj

def save_ip_ranges(profile_name, prefixes, force_write, debug):
    filename = 'ip-ranges-%s.json' % profile_name
    ip_ranges = {}
    ip_ranges['createDate'] = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    ip_ranges['prefixes'] = prefixes
    save_blob_as_json(filename, ip_ranges, force_write, debug)


########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_opinel_version('0.17.0'):
        return 42

    # Get the environment name
    profile_names = get_environment_name(args)

    # Initialize the list of regions to work with
    regions = build_region_list('ec2', args.regions, args.with_gov, args.with_cn)

    # For each profile/environment...
    for profile_name in profile_names:

        # Initialize IP addresses
        printInfo('Fetching public IP information for the \'%s\' environment...' % profile_name)
        ip_addresses = {}

        # Search for AWS credentials
        key_id, secret, session_token = read_creds(profile_name)
        if not key_id:
            return 42

        # For each region...
        for region in regions:

            # Connect to EC2
            ec2_client = connect_ec2(key_id, secret, session_token, region)
            if not ec2_client:
                continue

            # Get public IP addresses associated with EC2 instances
            printInfo('...in %s : EC2 instances' % region)
            reservations = handle_truncated_response(ec2_client.describe_instances, {}, 'NextToken', ['Reservations'])
            for reservation in reservations['Reservations']:
                for i in reservation['Instances']:
                    if 'PublicIpAddress' in i:
                        ip_addresses[i['PublicIpAddress']] = new_ip_info(region, i['InstanceId'], False) 
                    if 'NetworkInterfaces' in i:
                        for eni in i['NetworkInterfaces']:
                            if 'Association' in eni:
                                ip_addresses[eni['Association']['PublicIp']] = new_ip_info(region, i['InstanceId'], False) # At that point, we don't know whether it's an EIP or not...

            # Get all EIPs (to handle unassigned cases)
            printInfo('...in %s: Elastic IP addresses' % region)
            eips = handle_truncated_response(ec2_client.describe_addresses, {}, 'NextToken', ['Addresses'])
            for eip in eips['Addresses']:
                instance_id = eip['InstanceId'] if 'InstanceId' in eip else None
                # EC2-Classic non associated EIPs have an empty string for instance ID (instead of lacking the attribute in VPC) 
                if instance_id == '':
                    instance_id = None
                ip_addresses[eip['PublicIp']] = new_ip_info(region, instance_id, True)

            # Format 
            prefixes = []
            for ip in ip_addresses:
                prefixes.append(new_prefix(ip, ip_addresses[ip]))

        # Generate an ip-ranges-<profile>.json file
        save_ip_ranges(profile_name, prefixes, args.force_write, args.debug)


########################################
##### Parse arguments and call main()
########################################

default_args = read_profile_default_args(parser.prog)

add_common_argument(parser, default_args, 'regions')
add_common_argument(parser, default_args, 'with-gov')
add_common_argument(parser, default_args, 'with-cn')
add_common_argument(parser, default_args, 'force')
add_common_argument(parser, default_args, 'dry-run')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
