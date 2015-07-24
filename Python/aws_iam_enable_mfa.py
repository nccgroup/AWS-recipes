#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *

# Import third-party modules
import sys


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

    # Set the user name
    if not user_name:
        printInfo('Searching for username...')
        user_name = fetch_from_current_user(iam_client, key_id, 'UserName')
        if not user_name:
            printInfo('Error: could not find user name to enable MFA for.')
            return 42

    # Create an MFA device
    mfa_serial = enable_mfa(iam_client, user_name)

    # Update the no-mfa credentials file
    write_creds_to_aws_credentials_file(profile_name, key_id = key_id, secret = secret, mfa_serial = mfa_serial, credentials_file = aws_credentials_file_no_mfa)
    printInfo('Your credentials file has been updated; you may now use aws_recipes_init_sts_session.py to access the API using short-lived credentials.')


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
