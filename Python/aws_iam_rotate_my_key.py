#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_iam import *

# Import stock packages
import shutil
import sys
import time
import traceback


########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_opinel_version('1.3.4'):
        return 42

    # Arguments
    profile_name = args.profile[0]
    user_name = args.user_name[0]

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

    # Set the user name
    if not user_name:
        printInfo('Searching for username...')
        user_name = fetch_from_current_user(iam_client, aws_key_id, 'UserName')
        if not user_name:
            printError('Error: could not find user name to rotate the key for.')
            return 42

    # Create the new key
    try:
        # Create a new IAM key
        printInfo('Creating a new access key for \'%s\'...' % user_name)
        new_credentials = iam_client.create_access_key(UserName = user_name)['AccessKey']
        list_access_keys(iam_client, user_name)
    except Exception as e:
        printException(e)
        return 42

    # Write the new key
    if credentials['SessionToken']:
        write_creds_to_aws_credentials_file(profile_name + '-nomfa', new_credentials)
        new_credentials = read_creds(profile_name + '-nomfa')
        printInfo('Initiating a session with the new access key...')
        new_credentials = init_sts_session(profile_name, new_credentials)
    else:
        write_creds_to_aws_credentials_file(profile_name, new_credentials)
        new_credentials = read_creds(profile_name)
        # Sleep because the access key may not be active server-side...
        printInfo('Verifying access with the new key...')
        time.sleep(5)

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

    try:
        list_access_keys(new_iam_client, user_name)
        printInfo('Success !')
    except Exception as e:
        printException(e)
        return 42


########################################
##### Additional arguments
########################################

default_args = read_profile_default_args(parser.prog)

add_iam_argument(parser, default_args, 'user-name')

########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
