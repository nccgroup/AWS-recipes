#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import sys

from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError, printException
from opinel.utils.credentials import read_creds, assume_role
from opinel.utils.globals import check_requirements

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('mfa-serial')
    parser.add_argument('mfa-code')
    parser.parser.add_argument('--role-session-name',
                                dest='role_session_name',
                                default=None,
                                help='Identifier for the assumed role\'s session.')
    parser.parser.add_argument('--role-name',
                                dest='role_name',
                                default=None,
                                help='Identifier for the assumed role.')
    parser.parser.add_argument('--role-arn',
                                dest='role_arn',
                                default=None,
                                help='ARN of the assumed role.')
    parser.parser.add_argument('--external-id',
                                dest='external_id',
                                default=None,
                                help='External ID to use when assuming the role.')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Read creds automatically prompts for MFA code and assumes a role if role is already configured
    try:
        credentials = read_creds(args.profile[0], mfa_code = args.mfa_code, mfa_serial_arg = args.mfa_serial)
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

if __name__ == '__main__':
    sys.exit(main())
