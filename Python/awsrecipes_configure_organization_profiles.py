#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.aws import connect_service
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printDebug, printError, printException, printInfo, prompt_4_mfa_serial, prompt_4_value, prompt_4_yes_no
from opinel.utils.credentials import assume_role, read_creds, write_creds_to_aws_credentials_file
from opinel.utils.globals import check_requirements
from opinel.utils.profiles import AWSProfiles, AWSProfile, aws_config_file
from opinel.services.organizations import get_organization_accounts, get_organizational_units, list_accounts_for_parent

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.parser.add_argument('--role-name',
                                dest='role_name',
                                default=[],
                                nargs='+',
                                required=True,
                                help='Name of the role to be assumed in each child account.')
    parser.parser.add_argument('--ou',
                                dest='org_unit',
                                default=[],
                                nargs='+',
                                help='')
    parser.parser.add_argument('--profile-prefix',
                                dest='profile_prefix',
                                default=None,
                                help='')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Arguments
    source_profile = AWSProfiles.get(args.profile)[0]
    credentials = read_creds(args.profile[0])
    if not credentials['AccessKeyId']:
        return 42

    # Get all accounts to setup
    api_client = connect_service('organizations', credentials)
    if len(args.org_unit) == 0:
        if prompt_4_yes_no('Do you want to specify a particular organizational unit'):
            ous = get_organizational_units(api_client)
            choice = prompt_4_value('Which OU do you want to configure IAM for', choices = [ou['Name'] for ou in ous], display_indices = True, no_confirm = True, return_index = True)
            account_list = list_accounts_for_parent(api_client, ous[choice]) 
        else:
            account_list = get_organization_accounts(api_client)

    # Setup the accounts
    organization_profiles = {'ready': [], 'notready': []}
    
    for account in account_list:
        printInfo('Validating role name in %s...' % account['Name'], newLine = False)
        profile_name = account['Name'].lower().replace(' ', '_')
        if args.profile_prefix:
            profile_name = '%s-%s' % (args.profile_prefix, profile_name)
        profile = AWSProfile(filename = aws_config_file, name = profile_name)
        profile.set_attribute('source_profile', source_profile.name)
        success = False
        for role_name in args.role_name:
            try:
                role_arn = 'arn:aws:iam::%s:role/%s' % (account['Id'], role_name)
                role_credentials = assume_role(role_name, credentials, role_arn, 'aws-recipes', silent = True )
                profile.set_attribute('role_arn', 'arn:aws:iam::%s:role/%s' % (account['Id'], role_name))
                profile.set_attribute('source_profile', source_profile.name)
                organization_profiles['ready'].append(profile)
                printInfo(' success')
                success = True
                break
            except Exception as e:
                pass
        if not success:
            printInfo(' failure')
            organization_profiles['notready'].append(profile)

    for profile in organization_profiles['ready']:
        profile.write()

    for profile in organization_profiles['notready']:
        printError('Failed to determine a valid role in %s' % profile.name)

if __name__ == '__main__':
    sys.exit(main())
