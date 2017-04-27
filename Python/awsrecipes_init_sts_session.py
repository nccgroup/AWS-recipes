#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException
from opinel.utils.credentials import read_creds
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
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Read creds automatically prompts for MFA code and initiates a session if expired
    credentials = read_creds(args.profile[0], mfa_code = args.mfa_code, mfa_serial_arg = args.mfa_serial, force_init = True)
    if not credentials['AccessKeyId']:
        return 42

if __name__ == '__main__':
    sys.exit(main())
