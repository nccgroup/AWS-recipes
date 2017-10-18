#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.aws import build_region_list, connect_service, get_name, handle_truncated_response
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printException, printInfo, prompt_4_value, prompt_4_yes_no
from opinel.utils.credentials import read_creds
from opinel.utils.fs import read_ip_ranges, save_ip_ranges
from opinel.utils.globals import check_requirements
from opinel.utils.profiles import AWSProfiles


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


########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('force')
    parser.add_argument('dry-run')
    parser.add_argument('regions')
    parser.add_argument('partition-name')
    parser.parser.add_argument('--interactive',
                        dest='interactive',
                        default=False,
                        action='store_true',
                        help='Interactive prompt to manually enter CIDRs.')
    parser.parser.add_argument('--csv-ip-ranges',
                        dest='csv_ip_ranges',
                        default=[],
                        nargs='+',
                        help='CSV file(s) containing CIDRs information.')
    parser.parser.add_argument('--skip-first-line',
                        dest='skip_first_line',
                        default=False,
                        action='store_true',
                        help='Skip first line when parsing CSV file.')
    parser.parser.add_argument('--attributes',
                        dest='attributes',
                        default=[],
                        nargs='+',
                        help='Name of the attributes to enter for each CIDR.')
    parser.parser.add_argument('--mappings',
                        dest='mappings',
                        default=[],
                        nargs='+',
                        help='Column number matching attributes when headers differ.')
    parser.parser.add_argument('--public-only',
                        dest='public_only',
                        default=False,
                        action='store_true',
                        help='Do not fetch VPC and subnet CIDR information.')
    parser.parser.add_argument('--single-file',
                        dest='single_file',
                        default=False,
                        action='store_true',
                        help='Save all profile\'s IP addresses into a single file.')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Initialize the list of regions to work with
    regions = build_region_list('ec2', args.regions, args.partition_name)

    # For each profile/environment...
    profile_names = AWSProfiles.list(args.profile)
    if len(profile_names) == 0:
        profile_names = args.profile

    # Initialize the list of prefixes
    prefixes = []

    for profile_name in profile_names:

      try:

        # Interactive mode
        if args.interactive:

            # Initalize prefixes
            attributes = args.attributes
            filename = 'ip-ranges-%s.json' % profile_name
            if os.path.isfile(filename):
                printInfo('Loading existing IP ranges from %s' % filename)
                prefixes = read_ip_ranges(filename)
                # Initialize attributes from existing values
                if attributes == []:
                    for prefix in prefixes:
                        for key in prefix:
                            if key not in attributes:
                                attributes.append(key)

            # IP prefix does not need to be specified as an attribute
            attributes = [a for a in attributes if a != 'ip_prefix']

            # Prompt for new entries
            while prompt_4_yes_no('Add a new IP prefix to the ip ranges'):
                ip_prefix = prompt_4_value('Enter the new IP prefix:')
                obj = {}
                for a in attributes:
                    obj[a] = prompt_4_value('Enter the \'%s\' value:' % a)
                prefixes.append(new_prefix(ip_prefix, obj))

        # Support loading from CSV file
        elif len(args.csv_ip_ranges) > 0:

            # Load CSV file contents
            for filename in args.csv_ip_ranges:
                with open(filename, 'rt') as f:
                    csv_contents = f.readlines()

                # Initialize mappings
                attributes = args.attributes
                mappings = {}
                if attributes == []:
                    # Follow structure of first line
                    headers = csv_contents.pop(0).strip().split(',')
                    for index, attribute in enumerate(headers):
                        mappings[attribute] = index
                elif attributes and args.mappings == []:
                    # Follow structure of first line but only map a subset of fields
                    headers = csv_contents.pop(0).strip().split(',')
                    attributes.append('ip_prefix')
                    for attribute in set(attributes):
                        mappings[attribute] = headers.index(attribute)
                else:
                    # Indices of columns are provided as an argument
                    for index, attribute in enumerate(attributes):
                        mappings[attribute] = int(args.mappings[index])
                    if args.skip_first_line:
                        csv_contents.pop(0)

                # For each line...
                for line in csv_contents:
                    ip_prefix = {}
                    values = line.strip().split(',')
                    if len(values) < len(mappings):
                        continue
                    for attribute in mappings:
                        ip_prefix[attribute] = values[mappings[attribute]]
                    if 'ip_prefix' in mappings and 'mask' in mappings:
                        ip = ip_prefix.pop('ip_prefix')
                        mask = ip_prefix.pop('mask')
                        ip_prefix['ip_prefix'] = '%s/%s' % (ip, mask.replace('/',''))
                    prefixes.append(ip_prefix)

        # AWS mode
        else:

            # Initialize IP addresses
            printInfo('Fetching IP information for the \'%s\' environment...' % profile_name)
            if not args.single_file:
                prefixes = []
            ip_addresses = {}

            # Search for AWS credentials
            credentials = read_creds(profile_name)
            if not credentials['AccessKeyId']:
                return 42

            # For each region...
            for region in regions:

                # Connect to EC2
                ec2_client = connect_service('ec2', credentials, region)
                if not ec2_client:
                    continue

                # Get public IP addresses associated with EC2 instances
                printInfo('Fetching EC2 instances...')
                reservations = handle_truncated_response(ec2_client.describe_instances, {}, ['Reservations'])
                for reservation in reservations['Reservations']:
                    for i in reservation['Instances']:
                        if 'PublicIpAddress' in i:
                            ip_addresses[i['PublicIpAddress']] = new_ip_info(region, i['InstanceId'], False)
                            get_name(i, ip_addresses[i['PublicIpAddress']], 'InstanceId')
                        if 'NetworkInterfaces' in i:
                            for eni in i['NetworkInterfaces']:
                                if 'Association' in eni:
                                    ip_addresses[eni['Association']['PublicIp']] = new_ip_info(region, i['InstanceId'], False) # At that point, we don't know whether it's an EIP or not...
                                    get_name(i, ip_addresses[eni['Association']['PublicIp']], 'InstanceId')

                # Get all EIPs (to handle unassigned cases)
                printInfo('Fetching Elastic IP addresses...')
                eips = handle_truncated_response(ec2_client.describe_addresses, {}, ['Addresses'])
                for eip in eips['Addresses']:
                    instance_id = eip['InstanceId'] if 'InstanceId' in eip else None
                    # EC2-Classic non associated EIPs have an empty string for instance ID (instead of lacking the attribute in VPC)
                    if instance_id == '':
                        instance_id = None
                    ip_addresses[eip['PublicIp']] = new_ip_info(region, instance_id, True)
                    ip_addresses[eip['PublicIp']]['name'] = instance_id

                # Format
                for ip in ip_addresses:
                    prefixes.append(new_prefix(ip, ip_addresses[ip]))

                if not args.public_only:

                    # Get all VPCs
                    printInfo('Fetching VPCs...')
                    vpcs = ec2_client.describe_vpcs()['Vpcs']
                    for vpc in vpcs:
                        prefix = new_prefix(vpc['CidrBlock'], {})
                        prefix['id'] = vpc['VpcId']
                        prefix['name'] = get_name(vpc, {}, 'VpcId')
                        prefix['region'] = region
                        prefixes.append(prefix)

                    # Get all Subnets
                    printInfo('Fetching subnets...')
                    subnets = ec2_client.describe_subnets()['Subnets']
                    for subnet in subnets:
                        prefix = new_prefix(subnet['CidrBlock'], {})
                        prefix['id'] = subnet['SubnetId']
                        prefix['name'] = get_name(subnet, {}, 'SubnetId')
                        prefix['region'] = region
                        prefixes.append(prefix)

        if not args.single_file:
            # Generate an ip-ranges-<profile>.json file
            save_ip_ranges(profile_name, prefixes, args.force_write, args.debug)

      except Exception as e:
        printException(e)

    if args.single_file:
        save_ip_ranges('default', prefixes, args.force_write, args.debug)

if __name__ == '__main__':
    sys.exit(main())
