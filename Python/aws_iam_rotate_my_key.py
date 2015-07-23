#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *
from AWSUtils.utils_sts import *

# Import third-party modules
import shutil
import sys
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
    except Exception, e:
        printException(e)
        return 42

    # Fetch the long-lived key ID if STS credentials are used
    if session_token:
        aws_key_id, aws_secret, foo1, foo2 = read_creds_from_aws_credentials_file(profile_name, aws_credentials_file_no_mfa)
    else:
        aws_key_id = session_key_id

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
    except Exception, e:
        printException(e)
        return 42

    # Save the new key to a temporary file
    if session_token:
        write_creds_to_aws_credentials_file(profile_name, key_id = new_key_id, secret = new_secret, session_token = None, credentials_file = aws_credentials_file_tmp)
    else:
        write_creds_to_aws_credentials_file(profile_name, key_id = new_key_id, secret = new_secret, session_token = None, credentials_file = aws_credentials_file_tmp, use_no_mfa_file = False)

    # Init an STS session with the new key
    if session_token:
        # Init an STS session with the new key
        printInfo('Initiating a session with the new access key...')
        init_sts_session_and_save_in_credentials(profile_name, credentials_file = aws_credentials_file_tmp)

    # Confirm that it works
    try:
        printInfo('Verifying access with the new key...')
        session_key_id, session_secret, mfa_serial, session_token = read_creds_from_aws_credentials_file(profile_name)
        new_iam_client = connect_iam(session_key_id, session_secret, session_token)
        printInfo('Deleting the old access key...')
        new_iam_client.delete_access_key(AccessKeyId = aws_key_id, UserName = user_name)
        list_access_keys(iam_client, user_name)
    except Exception, e:
        printException(e)
        return 42

    # Move temporary file to permanent
    if session_token:
        printInfo('Updating AWS configuration file at %s...' % aws_credentials_file_no_mfa)
        shutil.move(aws_credentials_file_tmp, aws_credentials_file_no_mfa)
    else:
        printInfo('Updating AWS configuration file at %s...' % aws_credentials_file)
        shutil.move(aws_credentials_file_tmp, aws_credentials_file)

    printInfo('Success !')


########################################
##### Additional arguments
########################################

add_iam_argument(parser, 'user_name')

########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
