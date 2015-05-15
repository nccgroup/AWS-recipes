#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *
from AWSUtils.utils_sts import *

# Import the Amazon SDK
import boto

# Import other third-party packages
import shutil
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
        print 'Connecting to AWS IAM...'
        session_key_id, session_secret, mfa_serial, session_token = read_creds_from_aws_credentials_file(profile_name)
        iam_connection = boto.connect_iam(aws_access_key_id = session_key_id, aws_secret_access_key = session_secret, security_token = session_token)
    except Exception, e:
        printException(e)
        return

    # Fetch the long-lived key ID if STS credentials are used
    if session_token:
        aws_key_id, aws_secret, foo1, foo2 = read_creds_from_aws_credentials_file(profile_name, aws_credentials_file_no_mfa)
    else:
        aws_key_id = session_key_id

    # Fetch current user name
    if not user_name:
        user_name = fetch_from_current_user(iam_connection, aws_key_id, 'user_name')
        if not user_name:
            print 'Error'
            return

    # Create the new key
    try:
        # Create a new IAM key
        print 'Creating a new access key for \'%s\'...' % user_name
        new_key = iam_connection.create_access_key(user_name)
        new_key_id = new_key['create_access_key_response']['create_access_key_result']['access_key']['access_key_id']
        new_secret = new_key['create_access_key_response']['create_access_key_result']['access_key']['secret_access_key']
        list_access_keys(iam_connection, user_name)
    except Exception, e:
        printException(e)
        return

    # Save the new key to a temporary file
    if session_token:
        write_creds_to_aws_credentials_file(profile_name, key_id = new_key_id, secret = new_secret, session_token = None, credentials_file = aws_credentials_file_tmp)
    else:
        write_creds_to_aws_credentials_file(profile_name, key_id = new_key_id, secret = new_secret, session_token = None, credentials_file = aws_credentials_file_tmp, use_no_mfa_file = False)

    # Init an STS session with the new key
    if session_token:
        # Init an STS session with the new key
        print 'Initiating a session with the new access key...'
        init_sts_session_and_save_in_credentials(profile_name, credentials_file = aws_credentials_file_tmp)

    # Confirm that it works
    try:
        print 'Verifying access with the new key...'
        session_key_id, session_secret, mfa_serial, session_token = read_creds_from_aws_credentials_file(profile_name)
        new_connection = boto.connect_iam(aws_access_key_id = session_key_id, aws_secret_access_key = session_secret, security_token = session_token)
        print 'Deleting the old access key...'
        new_connection.delete_access_key(aws_key_id, user_name)
        list_access_keys(iam_connection, user_name)
    except Exception, e:
        printException(e)
        return

    # Move temporary file to permanent
    if session_token:
        print 'Updating AWS configuration file at %s...' % aws_credentials_file_no_mfa
        shutil.move(aws_credentials_file_tmp, aws_credentials_file_no_mfa)
    else:
        print 'Updating AWS configuration file at %s...' % aws_credentials_file
        shutil.move(aws_credentials_file_tmp, aws_credentials_file)

    print 'Success !'


########################################
##### Additional arguments
########################################

parser.add_argument('--user_name',
                    dest='user_name',
                    default=[''],
                    nargs='+',
                    help='Your AWS IAM user name. This script will find it automatically if not provided, but will take longer to run.')


########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    main(args)
