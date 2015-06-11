#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *

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
        print "Error, you need to provide at least one user name"
        return 42

    # Connect to IAM
    iam_connection = connect_iam(profile_name)
    if not iam_connection:
        return 42

    # Iterate over users
    for user in args.users:

        # Status
        print 'Deleting user %s...' % user

        # Delete user
        delete_user(iam_connection, user)


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
