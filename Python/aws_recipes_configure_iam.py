#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_iam import *

# Import stock opinel
import sys

########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Arguments
    profile_name = args.profile[0]

    # Check for migration from existing profile to no-mfa profile
    use_found_credentials = False
    key_id, secret, mfa_serial, token = read_creds_from_aws_credentials_file(profile_name)
    if key_id != None and secret != None and mfa_serial == None and token == None:
        if prompt_4_yes_no('Found long-lived credentials for the profile \'%s\'. Do you want to use those when configuring mfa' % profile_name):
           use_found_credentials = True
           iam_client = connect_iam(key_id, secret, token)
           if not iam_client:
               return 42
           try:
               printInfo('Trying to read the MFA serial number associated with this IAM user...')
               user_name = fetch_from_current_user(iam_client, key_id, 'UserName')
               mfa_devices = iam_client.list_mfa_devices(UserName = user_name)['MFADevices']
               mfa_serial = mfa_devices[0]['SerialNumber']
           except Exception as e:
               printException(e)
               pass

    if not use_found_credentials:
       # Get values
        key_id = prompt_4_value('AWS Access Key ID: ', no_confirm = True)
        secret = prompt_4_value('AWS Secret Access Key: ', no_confirm = True)
    if not mfa_serial:
        mfa_serial = prompt_4_mfa_serial()

    # Update the profile name if an MFA serial number is stored
    if mfa_serial and not profile_name.endswith('-nomfa'):
        profile_name = profile_name + '-nomfa'
        printInfo('Your long-lived credentials will now be available via the %s profile.' % profile_name)

    # Check for overwrite
    while True:
        k, s, m, t = read_creds_from_aws_credentials_file(profile_name)
        if k or s or m or t:
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
    write_creds_to_aws_credentials_file(profile_name, key_id = key_id, secret = secret, mfa_serial = mfa_serial)


########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
