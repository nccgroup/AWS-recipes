#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *


########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Arguments
    profile_name = args.profile[0]

    # Check for migration from credentials to credentials.no-mfa
    use_found_credentials = False
    key_id, secret, mfa_serial, token = read_creds_from_aws_credentials_file(profile_name)
    if key_id != None and secret != None and mfa_serial == None and token == None:
        if prompt_4_yes_no('Found long-lived credentials for the profile \'%s\'. Do you want to use those when configuration mfa' % profile_name):
           use_found_credentials = True
           iam_connection = connect_iam(key_id, secret, token)
           if not iam_connection:
               return 42
           try:
               user_name = fetch_from_current_user(iam_connection, key_id, 'user_name')
               mfa_devices = iam_connection.get_all_mfa_devices(user_name)['list_mfa_devices_response']['list_mfa_devices_result']['mfa_devices']
               mfa_serial = mfa_devices[0]['serial_number']
           except Exception, e:
               printException(e)
               pass

    if not use_found_credentials:
       # Get values
        key_id = prompt_4_value('AWS Access Key ID: ', no_confirm = True)
        secret = prompt_4_value('AWS Secret Access Key: ', no_confirm = True)
    if not mfa_serial:
        mfa_serial = prompt_4_mfa_serial()

    # Check for overwrite
    while True:
        k, s, m, t = read_creds_from_aws_credentials_file(profile_name, credentials_file = aws_credentials_file_no_mfa)
        if k or s or m or t:
            if not prompt_4_yes_no('The profile \'%s\' already exists. Do you want to overwrite the existing values' % profile_name):
                if not prompt_4_yes_no('Do you want to create a new profile with these credentials'):
                    print 'Configuration aborted.'
                    return
                profile_name = prompt_4_value('Profile name: ')
            else:
                break
        else:
            break

    # Write values to credentials or credentials.no-mfa
    if mfa_serial:
        write_creds_to_aws_credentials_file(profile_name, key_id = key_id, secret = secret, mfa_serial = mfa_serial, credentials_file = aws_credentials_file_no_mfa)
    else:
        write_creds_to_aws_credentials_file(profile_name, key_id = key_id, secret = secret, mfa_serial = mfa_serial)


########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    main(args)
