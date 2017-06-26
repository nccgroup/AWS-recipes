#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.aws import connect_service
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
    parser.add_argument('common-groups',
                        default=[],
                        nargs='+',
                        help='List of groups each IAM user should belong to.')
    parser.add_argument('category-groups',
                        default=[],
                        nargs='+',
                        help='List of category groups; each IAM user must belong to one.')
    parser.add_argument('category-regex',
                        default=[],
                        nargs='+',
                        help='List of regex enabling auto-assigment of category groups.')
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

    # Connect to IAM
    iam_client = connect_service('iam', credentials)
    if not iam_client:
        return 42

    # Create groups
    for group in args.category_groups + args.common_groups:
        try:
            printInfo('Creating group %s...' % group)
            iam_client.create_group(GroupName = group)
        except  Exception as e:
            if e.response['Error']['Code'] != 'EntityAlreadyExists':
                printException(e)


if __name__ == '__main__':
    sys.exit(main())
