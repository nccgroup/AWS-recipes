#!/usr/bin/env python

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
    if not args.user_name:
        printError("Error, you need to provide at least one user name")
        return 42

    # Connect to IAM
    try:
        key_id, secret, session_token = read_creds(profile_name)
        iam_client = connect_iam(key_id, secret, session_token)
    except Exception as e:
        printException(e)
        return 42

    # Iterate over users
    for user in args.user_name:
        delete_user(iam_client, user)


########################################
##### Parse arguments and call main()
########################################

parser.add_argument('--user-name',
                    dest='user_name',
                    default=None,
                    nargs='+',
                    help='Name of user(s) to be deleted')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
