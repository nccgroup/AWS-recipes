#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time

from opinel.services.iam import show_access_keys
from opinel.utils.aws import connect_service, get_username
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printInfo, printException
from opinel.utils.credentials import read_creds, write_creds_to_aws_credentials_file, init_sts_session
from opinel.utils.globals import check_requirements

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
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

    # Fetch the long-lived key ID if STS credentials are used
    if credentials['SessionToken']:
        akia_creds = read_creds(profile_name + '-nomfa')
    else:
        akia_creds = credentials
    aws_key_id = akia_creds['AccessKeyId']
    aws_secret = akia_creds['SecretAccessKey']

    # Fetch username
    printInfo('Fetching username...')
    user_name = get_username(credentials)

    # Create the new key
    try:
        # Create a new IAM key
        printInfo('Creating a new access key for \'%s\'...' % user_name)
        new_credentials = iam_client.create_access_key(UserName = user_name)['AccessKey']
        show_access_keys(iam_client, user_name)
    except Exception as e:
        printException(e)
        return 42

    # Save the new key
    if credentials['SessionToken']:
        write_creds_to_aws_credentials_file(profile_name + '-nomfa', new_credentials)
    else:
        write_creds_to_aws_credentials_file(profile_name, new_credentials)
    printInfo('Credentials file updated with new access key.')

    printInfo('Waiting 10 seconds before verifying access with the new key...')
    # Sleep because the access key may not be active server-side...
    time.sleep(10)
    if credentials['SessionToken']:
        new_credentials = read_creds(profile_name + '-nomfa')
        new_credentials = init_sts_session(profile_name, new_credentials)
    else:
        new_credentials = read_creds(profile_name)
    # Confirm that it works...
    try:
        new_iam_client = connect_service('iam', new_credentials)
        printInfo('Deleting the old access key...')
        new_iam_client.delete_access_key(AccessKeyId = aws_key_id, UserName = user_name)
    except Exception as e:
        printException(e)
        printInfo('Restoring your old credentials...')
        # Restore the old key here
        if credentials['SessionToken']:
            write_creds_to_aws_credentials_file(profile_name + '-nomfa', akia_creds)
        else:
            write_creds_to_aws_credentials_file(profile_name, akia_creds)
        return 42

    # Summary of existing access keys
    try:
        show_access_keys(new_iam_client, user_name)
        printInfo('Success !')
    except Exception as e:
        printException(e)
        return 42


if __name__ == '__main__':
    sys.exit(main())
