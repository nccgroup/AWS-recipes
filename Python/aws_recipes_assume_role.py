#!/usr/bin/env python

# Import opinel
from opinel.utils import *

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

    # Read creds automatically prompts for MFA code and assumes a role if role is already configured
    try:
        credentials = read_creds(args.profile[0], mfa_code = args.mfa_code, mfa_serial_arg = args.mfa_serial)
        print(str(credentials))
    except Exception as e:
        printException(e)
        return 42

    # If the role's ARN was provided...
    if args.role_arn:
        if not args.role_name:
            printError('Error: you must specify a name for this role.')
            return 42
        role_session_name = args.role_session_name if args.role_session_name else 'aws-recipes-%s' % str(datetime.datetime.utcnow()).replace(' ', '_').replace(':','-')
        assume_role(args.role_name, credentials, args.role_arn, role_session_name)

        # TODO save profile to config if not there


########################################
##### Parse arguments and call main()
########################################

add_sts_argument(parser, 'mfa-serial')
add_sts_argument(parser, 'mfa-code')
add_sts_argument(parser, 'external-id')
add_sts_argument(parser, 'role-arn')

parser.add_argument('--role-session-name',
                    dest='role_session_name',
                    default=None,
                    help='The identifier for the assumed role session.')

parser.add_argument('--role-name',
                    dest='role_name',
                    default=None,
                    help='The identifier for the assumed role.')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
