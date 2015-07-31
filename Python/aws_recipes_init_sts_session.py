#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_iam import *
from opinel.utils_sts import *

# Import stock packages
import sys

########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Init STS session
    try:
        init_sts_session_and_save_in_credentials(args.profile[0], mfa_code = args.mfa_code[0], mfa_serial_arg = args.mfa_serial[0])
    except Exception as e:
        printException(e)
        return 42


########################################
##### Parse arguments and call main()
########################################

add_sts_argument(parser, 'mfa_serial')
add_sts_argument(parser, 'mfa_code')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
