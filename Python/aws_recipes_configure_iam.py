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

    # Check version of opinel
    if not check_opinel_version('0.15.0'):
        return 42

    # Arguments
    profile_name = args.profile[0]

    # Read credentials from a CSV file
    if args.csv_credentials[0]:
        credentials = {}
        credentials['AccessKeyId'], credentials['SecretAccessKey'], credentials['SerialNumber'] = read_creds_from_csv(args.csv_credentials[0])
        if not credentials['AccessKeyId'] or not credentials['SecretAccessKey']:
            printError('Failed to read credentials from %s' % args.csv_credentials[0])
            return 42
        else:
            use_found_credentials = True
    else:
        # Check for migration from existing profile to no-mfa profile
        use_found_credentials = False
        credentials = read_creds_from_aws_credentials_file(profile_name)
        if 'AccessKeyId' in credentials and credentials['AccessKeyId'] != None and credentials['SecretAccessKey'] != None and credentials['SerialNumber'] == None and credentials['SessionToken'] == None:
            if prompt_4_yes_no('Found long-lived credentials for the profile \'%s\'. Do you want to use those when configuring mfa' % profile_name):
               use_found_credentials = True
               iam_client = connect_iam(credentials)
               if not iam_client:
                   return 42
               try:
                   printInfo('Trying to read the MFA serial number associated with this IAM user...')
                   user_name = fetch_from_current_user(iam_client, credentials['AccessKeyId'], 'UserName')
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

    # Update the profile name if an MFA serial number is stored
    if credentials['SerialNumber'] and not profile_name.endswith('-nomfa'):
        profile_name = profile_name + '-nomfa'
        printInfo('Your long-lived credentials will now be available via the %s profile.' % profile_name)

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
    if args.csv_credentials[0] and prompt_4_yes_no('Do you want to delete the CSV file that contains your long-lived credentials?'):
        os.remove(args.csv_credentials[0])

########################################
##### Parse arguments and call main()
########################################

init_parser()
default_args = read_profile_default_args(parser.prog)

add_iam_argument(parser, default_args, 'csv-credentials')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
