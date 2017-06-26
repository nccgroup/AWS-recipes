#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.aws import build_region_list, connect_service
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printInfo, printException
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser(os.path.basename(__file__))
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('regions')
    parser.add_argument('partition-name')
    parser.add_argument('dry-run')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Get profile name
    profile_name = args.profile[0]

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Initialize the list of regions to work with
    regions = build_region_list('ec2', args.regions, args.partition_name)

    # For each region...
    for region in regions:

        # Connect to EC2
        ec2_client = connect_service('ec2', credentials, region)
        if not ec2_client:
            continue

        # List all EC2 groups
        security_groups = ec2_client.describe_security_groups()['SecurityGroups']
        for sg in security_groups:
            # Find default security groups (security groups cannot be renamed and do not have an 'IsDefault' attribute)
            if sg['GroupName'] == 'default':
                # Delete ingress rules
                try:
                    if sg['IpPermissions']:
                        ec2_client.revoke_security_group_ingress(GroupId = sg['GroupId'], DryRun = args.dry_run, IpPermissions = sg['IpPermissions'])
                        printInfo('Removed all ingress rules from security group %s (%s).' % (sg['GroupName'], sg['GroupId']))
                    else:
                        printInfo('The list of ingress rules for security group %s (%s) is already empty.' % (sg['GroupName'], sg['GroupId']))
                except Exception as e:
                    printException(e)
                    pass
                # Delete egress rules
                try:
                    if sg['IpPermissionsEgress']:
                        ec2_client.revoke_security_group_egress(GroupId = sg['GroupId'], DryRun = args.dry_run, IpPermissions = sg['IpPermissionsEgress'])
                        printInfo('Removed all egress rules from security group %s (%s).' % (sg['GroupName'], sg['GroupId']))
                    else:
                        printInfo('The list of egress rules for security group %s (%s) is already empty.' % (sg['GroupName'], sg['GroupId']))
                except Exception as e:
                    printException(e)
                    pass


if __name__ == '__main__':
    sys.exit(main())
