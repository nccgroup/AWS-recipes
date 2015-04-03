#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *

# Import third-party modules
import base64
import fabulous.utils
import fabulous.image
import gnupg
import os
import random
import string
import time
import zipfile


########################################
##### Helpers
########################################
def cleanup(iam_connection, user, stage = 0, serial = None):
    print 'Cleaning up...'
    time.sleep(5)
    delete_user(iam_connection, user, stage, serial)
    if stage >= 4:
        try:
            os.remove('%s.png' % user)
        except:
            pass
    shutil.rmtree(user)

def generate_password(length = 16):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + '!@#$%^&*()_+`-=[]{};:,<.>?/\\|') for _ in xrange(length))


########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Arguments
    profile_name = args.profile_name[0]
    if not args.users:
        print "Error, you need to provide at least one user name"
        return

    # Connect to IAM
    iam_connection = connect_iam(profile_name)
    if not iam_connection:
        return

    # Iterate over users
    for user in args.users:

        # Status
        print 'Creating user %s...' % user
        password = ''

        # Prepare the output folder
        try:
            os.mkdir(user)
        except Exception, e:
            printException(e)
            return

        # Generate and save a random password
        try:
            password = generate_password()
            password_file = os.path.join(user, 'password.txt')
            with open(password_file, 'wt') as f:
                f.write(password)
        except Exception, e:
            printException(e)
            cleanup(iam_connection, user)
            return

        # Create the new IAM user
        try:
            iam_connection.create_user(user)
        except Exception, e:
            printException(e)
            cleanup(iam_connection, user)
            return

        # Create a login profile
        try:
            # Pending merge of https://github.com/boto/boto/pull/3007
            # TODO: check boto version once this goes through
            iam_connection.create_login_profile(user, password) # True)
        except Exception, e:
            printException(e)
            cleanup(iam_connection, user, 1)
            return

        # Add user to groups
        for group in args.groups:
            try:
                print 'Adding user to group %s...' % group
                iam_connection.add_user_to_group(group, user)
            except Exception, e:
                printException(e)
                cleanup(iam_connection, user, 2)
                return

        # Status
        print 'Enabling MFA for user %s...' % user
        serial = ''
        mfa_code1 = ''
        mfa_code2 = ''

        # Create an MFA device
        try:
            mfa_device = iam_connection.create_virtual_mfa_device('/', user)
            png = mfa_device['create_virtual_mfa_device_response']['create_virtual_mfa_device_result']['virtual_mfa_device']['qr_code_png']
            serial = mfa_device['create_virtual_mfa_device_response']['create_virtual_mfa_device_result']['virtual_mfa_device']['serial_number']
        except Exception, e:
            printException(e)
            cleanup(iam_connection, user, 3)
            return

        # Save and display file
        try:
            qrcode_file = os.path.join(user, '%s.png' % user)
            with open(qrcode_file, 'w') as f:
                f.write(base64.b64decode(png))
            fabulous.utils.term.bgcolor = 'white'
            print fabulous.image.Image(qrcode_file, 100)
            mfa_code1 = prompt_4_mfa_code()
            mfa_code2 = prompt_4_mfa_code()
        except Exception, e:
            printException(e)
            cleanup(iam_connection, user, 4)
            return

        # Activate the MFA device
        try:
            iam_connection.enable_mfa_device(user, serial, mfa_code1, mfa_code2)
        except Exception, e:
            printException(e)
            cleanup(iam_connection, user, 5)
            return

        # Create a zip archive
        f = zipfile.ZipFile('%s.zip' % user, 'w')
        for root, dirs, files in os.walk(user):
            for file in files:
                f.write(os.path.join(root, file))
        f.close()

        # TODO: PGP stuff


########################################
##### Parse arguments and call main()
########################################

parser.add_argument('--users',
                    dest='users',
                    default=None,
                    nargs='+',
                    help='User name(s) to create')

parser.add_argument('--groups',
                    dest='groups',
                    default=[],
                    nargs='+',
                    help='User name(s) to create')

args = parser.parse_args()

if __name__ == '__main__':
    main(args)
