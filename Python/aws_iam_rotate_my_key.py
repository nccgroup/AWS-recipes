#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_iam import *
from opinel.utils_sts import *

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

    # Arguments
    profile_name = args.profile[0]
    user_name = args.user_name[0]

    # Connect to IAM
    try:
        key_id, secret, session_token = read_creds(profile_name)
        iam_client = connect_iam(key_id, secret, session_token)
    except Exception as e:
        printException(e)
        return 42

    # Fetch the long-lived key ID if STS credentials are used
    if session_token:
        aws_key_id, aws_secret, foo1 = read_creds(profile_name + '-nomfa')
    else:
        aws_key_id = key_id
        aws_secret = secret

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
        new_key = iam_client.create_access_key(UserName = user_name)
        new_key_id = new_key['AccessKey']['AccessKeyId']
        new_secret = new_key['AccessKey']['SecretAccessKey']
        list_access_keys(iam_client, user_name)
    except Exception as e:
        printException(e)
        return 42

    # Write the new key
    if session_token:
        write_creds_to_aws_credentials_file(profile_name + '-nomfa', key_id = new_key_id, secret = new_secret, session_token = None)
    else:
        write_creds_to_aws_credentials_file(profile_name, key_id = new_key_id, secret = new_secret, session_token = None)

    if session_token:
        # Init an STS session with the new key
        printInfo('Initiating a session with the new access key...')
        init_sts_session_and_save_in_credentials(profile_name)
    else:
        # Sleep because the access key may not be active server-side...
        printInfo('Verifying access with the new key...')
        time.sleep(5)

    # Confirm that it works...
    try:
        new_key_id, new_secret, new_session_token = read_creds(profile_name)
        new_iam_client = connect_iam(new_key_id, new_secret, new_session_token)
        printInfo('Deleting the old access key...')
        new_iam_client.delete_access_key(AccessKeyId = aws_key_id, UserName = user_name)
    except Exception as e:
        printException(e)
        printInfo('Restoring your old credentials...')
        # Restore the old key here
        if session_token:
            write_creds_to_aws_credentials_file(profile_name + '-nomfa', key_id = aws_key_id, secret = aws_secret, session_token = None)
        else:
            write_creds_to_aws_credentials_file(profile_name, key_id = aws_key_id, secret = aws_secret, session_token = None)
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
