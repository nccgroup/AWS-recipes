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

    # Arguments
    profile_name = args.profile[0]

    # Connect to IAM
    try:
        key_id, secret, session_token = read_creds(profile_name)
        iam_client = connect_iam(key_id, secret, session_token)
    except Exception as e:
        printException(e)
        return 42

    # Create the groups
    create_default_groups(iam_client, args.common_groups, args.category_groups, args.dry_run)


########################################
##### Parse arguments and call main()
########################################

init_parser()
default_args = read_profile_default_args(parser.prog)

add_common_argument(parser, default_args, 'dry-run')
add_iam_argument(parser, default_args, 'common-groups')
add_iam_argument(parser, default_args, 'category-groups')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
