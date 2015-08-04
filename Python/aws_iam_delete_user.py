#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_iam import *

# Import stock packages
import sys


########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_opinel_version('0.10.0'):
        return 42

    # Arguments
    profile_name = args.profile[0]
    if not args.user_name:
        printError("Error, you need to provide at least one user name")
        return 42

    # Search for AWS credentials
    key_id, secret, session_token = read_creds(profile_name)
    if not key_id:
        return 42

    # Connect to IAM
    iam_client = connect_iam(key_id, secret, session_token)
    if not iam_client:
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
