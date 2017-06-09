#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import time

from opinel.utils.aws import build_region_list, connect_service, handle_truncated_response
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printInfo, printException
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('regions')
    parser.add_argument('partition-name')
    parser.parser.add_argument('--filters',
                               dest='filters',
                               default=None,
                               help='')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Get profile name
    profile_name = args.profile[0]

    # Build list of region
    regions = build_region_list('ec2', args.regions, args.partition_name)
    printInfo(str(regions))

    # Build filters
    filters = json.loads(args.filters) if args.filters else None

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # List all EC2 instances
    instances = []
    for region in regions:
        printInfo('Fetching instances in %s...' % region)
        ec2_client = connect_service('ec2', credentials, region_name = region)
        args = {'Filters': filters} if filters else {}
        reservations = handle_truncated_response(ec2_client.describe_instances, args, ['Reservations'])['Reservations']
        for r in reservations:
            instances += r['Instances']
    printInfo(' Found %d instances' % len(instances))

    # Build list of private and public IPs
    prvips = {}
    pubips = {}
    for i in instances:
        security_groups = i['SecurityGroups']
        for eni in i['NetworkInterfaces']:
            for prvip in eni['PrivateIpAddresses']:
                prvips[prvip['PrivateIpAddress']] = {'security_groups': security_groups}
                if 'Association' in prvip:
                    pubips[prvip['Association']['PublicIp']] = {'security_groups': security_groups}

    # Create target files
    with open('targets-%s-prv.txt' % profile_name, 'wt') as f:
        for prvip in prvips:
            f.write('%s\n' % prvip)
    with open('targets-%s-pub.txt' % profile_name, 'wt') as f:
        for pubip in pubips:
            f.write('%s\n' % pubip)
    
if __name__ == '__main__':
    sys.exit(main())
