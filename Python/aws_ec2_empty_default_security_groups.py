#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_ec2 import *

# Import stock packages
import sys

########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_opinel_version('1.0.3'):
        return 42

    # Arguments
    profile_name = args.profile[0]

    # Initialize the list of regions to work with
    regions = build_region_list('ec2', args.regions, args.with_gov, args.with_cn)

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not key_id:
        return 42

    # For each region...
    for region in regions:

        # Connect to EC2
        ec2_client = connect_ec2(credentials, region)
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
                except Exception, e:
                    printException(e)
                    pass
                # Delete egress rules
                try:
                    if sg['IpPermissionsEgress']:
                        ec2_client.revoke_security_group_egress(GroupId = sg['GroupId'], DryRun = args.dry_run, IpPermissions = sg['IpPermissionsEgress'])
                        printInfo('Removed all egress rules from security group %s (%s).' % (sg['GroupName'], sg['GroupId']))
                    else:
                        printInfo('The list of egress rules for security group %s (%s) is already empty.' % (sg['GroupName'], sg['GroupId']))
                except Exception, e:
                    printException(e)
                    pass


########################################
##### Parse arguments and call main()
########################################

default_args = read_profile_default_args(parser.prog)

add_common_argument(parser, default_args, 'regions')
add_common_argument(parser, default_args, 'with-gov')
add_common_argument(parser, default_args, 'with-cn')
add_common_argument(parser, default_args, 'dry-run')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
