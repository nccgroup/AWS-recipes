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
    if not check_opinel_version('1.0.4'):
        return 42

    # Read creds automatically prompts for MFA code and initiates a session if expired
    credentials = read_creds(args.profile[0], mfa_code = args.mfa_code, mfa_serial_arg = args.mfa_serial, force_init = True)
    if not credentials['AccessKeyId']:
        return 42


########################################
##### Parse arguments and call main()
########################################

add_sts_argument(parser, 'mfa-serial')
add_sts_argument(parser, 'mfa-code')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
