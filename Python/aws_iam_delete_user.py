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
    if not args.users:
        printError("Error, you need to provide at least one user name")
        return 42

    # Connect to IAM
    try:
        key_id, secret, session_token = read_creds(profile_name)
        iam_client = connect_iam(key_id, secret, session_token)
    except Exception, e:
        printException(e)
        return 42

    # Iterate over users
    for user in args.users:
        delete_user(iam_client, user)


########################################
##### Parse arguments and call main()
########################################

parser.add_argument('--users',
                    dest='users',
                    default=None,
                    nargs='+',
                    help='User name(s) to delete')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
