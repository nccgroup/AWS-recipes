#!/usr/bin/env python

# Import opinel
from opinel.utils_sts import *

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

    # Assume role and store credentials
    try:
        assume_role_and_save_in_credentials(args.profile[0], args.role_arn[0], args.role_session_name[0], args.mfa_serial[0], args.mfa_code[0])
    except Exception as e:
        printException(e)
        return 42


########################################
##### Parse arguments and call main()
########################################

add_sts_argument(parser, 'mfa-serial')
add_sts_argument(parser, 'mfa-code')

parser.add_argument('--role-arn',
                    dest='role_arn',
                    required=True,
                    nargs='+',
                    help='Role to be assumed.')

parser.add_argument('--role-session-name',
                    dest='role_session_name',
                    required=True,
                    nargs='+',
                    help='The identifier for the assumed role session. A new profile will be created as profile-role_session_name.')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
