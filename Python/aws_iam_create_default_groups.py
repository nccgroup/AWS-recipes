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
    if not check_opinel_version('1.0.3'):
        return 42

    # Arguments
    profile_name = args.profile[0]

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Connect to IAM
    iam_client = connect_iam(credentials)
    if not iam_client:
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
