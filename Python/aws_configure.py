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
    profile_name = args.profile_name[0]

    # Get values
    key_id = prompt_4_value('AWS Access Key ID: ')
    secret = prompt_4_value('AWS Secret Access Key: ')
    serial = prompt_4_value('AWS MFA serial: ')

    # Check for overwrite
    while True:
        k, s, m, t = read_creds_from_aws_credentials_file(profile_name)
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
    if serial:
        write_creds_to_aws_credentials_file(profile_name, key_id = key_id, secret = secret, mfa_serial = serial, credentials_file = aws_credentials_file_no_mfa)
    else:
        write_creds_to_aws_credentials_file(profile_name, key_id = key_id, secret = secret, mfa_serial = serial)


########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    main(args)
