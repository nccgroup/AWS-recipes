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

    # Read credentials
    key_id, secret, token = read_creds(args.profile[0])

    # Connect to IAM
    iam_connection = connect_iam(key_id, secret, token)
    if not iam_connection:
        return 42

    # Fetch the current user name
    print 'Searching for username...'
    user = fetch_from_current_user(iam_connection, key_id, 'user_name')
    if not user:
        print 'Error: could not find user name to enable MFA for.'
        return 42

    # Status
    print 'Enabling MFA for user \'%s\'...' % user

    # Create an MFA device
    mfa_serial = enable_mfa(iam_connection, user)

    # Update the no-mfa credentials file
    write_creds_to_aws_credentials_file(profile_name, key_id = key_id, secret = secret, mfa_serial = mfa_serial, credentials_file = aws_credentials_file_no_mfa)
    print 'Your credentials file has been updated; you may now use aws_init_session.py to access the API using short-lived credentials.'


########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
