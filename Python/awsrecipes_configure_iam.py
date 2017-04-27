#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.aws import connect_service
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError, printException, printInfo, prompt_4_mfa_serial, prompt_4_value, prompt_4_yes_no
from opinel.utils.credentials import read_creds_from_csv, read_creds_from_aws_credentials_file, write_creds_to_aws_credentials_file
from opinel.utils.globals import check_requirements

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('csv-credentials')
    parser.add_argument('mfa-serial')
    parser.add_argument('mfa-code')
    parser.parser.add_argument('--role-arn',
                                dest='role_arn',
                                default=None,
                                help='ARN of the assumed role.')
    parser.parser.add_argument('--external-id',
                                dest='external_id',
                                default=None,
                                help='External ID to use when assuming the role.')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Arguments
    profile_name = args.profile[0]

    if args.csv_credentials:
        # Read credentials from a CSV file
        credentials = {}
        credentials['AccessKeyId'], credentials['SecretAccessKey'], credentials['SerialNumber'] = read_creds_from_csv(args.csv_credentials)
        if not credentials['AccessKeyId'] or not credentials['SecretAccessKey']:
            printError('Failed to read credentials from %s' % args.csv_credentials)
            return 42
        use_found_credentials = True
    else:
        # Check for migration from existing profile to no-mfa profile
        use_found_credentials = False
        credentials = read_creds_from_aws_credentials_file(profile_name)
        if 'AccessKeyId' in credentials and credentials['AccessKeyId'] != None and credentials['SecretAccessKey'] != None and credentials['SerialNumber'] == None and credentials['SessionToken'] == None:
            if prompt_4_yes_no('Found long-lived credentials for the profile \'%s\'. Do you want to use those when configuring MFA' % profile_name):
               use_found_credentials = True
               iam_client = connect_service('iam', credentials)
               try:
                   printInfo('Trying to read the MFA serial number associated with this IAM user...')
                   user_name = iam_client.get_user()['User']['UserName']
                   mfa_devices = iam_client.list_mfa_devices(UserName = user_name)['MFADevices']
                   credentials['SerialNumber'] = mfa_devices[0]['SerialNumber']
               except Exception as e:
                   printException(e)
                   pass

    if not use_found_credentials:
       # Get values
        credentials['AccessKeyId'] = prompt_4_value('AWS Access Key ID: ', no_confirm = True)
        credentials['SecretAccessKey'] = prompt_4_value('AWS Secret Access Key: ', no_confirm = True)
    if 'SerialNumber' not in credentials or not credentials['SerialNumber']:
        credentials['SerialNumber'] = prompt_4_mfa_serial()

    # Check for overwrite
    while True:
        c = read_creds_from_aws_credentials_file(profile_name)
        if 'AccessKeyId' in c and c['AccessKeyId']:
            if not prompt_4_yes_no('The profile \'%s\' already exists. Do you want to overwrite the existing values' % profile_name):
                if not prompt_4_yes_no('Do you want to create a new profile with these credentials'):
                    printError('Configuration aborted.')
                    return
                profile_name = prompt_4_value('Profile name: ')
            else:
                break
        else:
            break

    # Write values to credentials file
    write_creds_to_aws_credentials_file(profile_name, credentials)

    # Delete CSV file?
    if args.csv_credentials and prompt_4_yes_no('Do you want to delete the CSV file that contains your long-lived credentials?'):
        os.remove(args.csv_credentials)

if __name__ == '__main__':
    sys.exit(main())
