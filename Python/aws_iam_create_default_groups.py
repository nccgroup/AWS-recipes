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

    # Connect to IAM
    try:
        key_id, secret, session_token = read_creds(profile_name)
        iam_client = connect_iam(key_id, secret, session_token)
    except Exception, e:
        printException(e)
        return 42

    # Create the groups
    create_default_groups(iam_client, args.common_groups, args.category_groups, args.dry_run)


########################################
##### Parse arguments and call main()
########################################

init_parser()
saved_args = read_profile_default_args(parser.prog)

parser.add_argument('--common_groups',
                    dest='common_groups',
                    default=set_profile_default(saved_args, 'common_groups', []),
                    nargs='+',
                    help='Groups that all IAM users should belong to.')
parser.add_argument('--category_groups',
                    dest='category_groups',
                    default=set_profile_default(saved_args, 'category_groups', []),
                    nargs='+',
                    help='Choice of groups that all IAM users should belong to.')
parser.add_argument('--dry',
                    dest='dry_run',
                    default=set_profile_default(saved_args, 'dry_run', False),
                    action='store_true',
                    help='Check the status for user but do not take action.')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
