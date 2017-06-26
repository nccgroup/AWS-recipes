#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.aws import connect_service
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements
from opinel.services.iam import delete_user


########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('user-name', help = 'Name of the user(s) to be deleted.')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Require at least one user names
    if not len(args.user_name):
        printError("Error, you need to provide at least one user name.")
        return 42

    # Read creds
    credentials = read_creds(args.profile[0])
    if not credentials['AccessKeyId']:
        return 42

    # Connect to IAM APIs
    iam_client = connect_service('iam', credentials)

    # Delete users
    for user in args.user_name:
        delete_user(iam_client, user)


if __name__ == '__main__':
    sys.exit(main())
