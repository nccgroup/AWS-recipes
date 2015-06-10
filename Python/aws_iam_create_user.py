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
import re
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
    shutil.rmtree(user)

def generate_password(length = 16):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + '!@#$%^&*()_+`-=[]{};:,<.>?/\\|') for _ in xrange(length))

def pgp_and_write(user, filename, data):
    pgp_key = None
    gpg = gnupg.GPG(gnupghome = os.path.join(os.path.expanduser('~'), '.gnupg'))
    public_keys = gpg.list_keys()
    for k in public_keys:
        uid = k['uids'][0]
        if re.match('.*%s.*' % user, uid):
            pgp_key = k
    if pgp_key:
        asc_data = gpg.encrypt(data, pgp_key['uids'])
        if asc_data.ok:
            with open(os.path.join(user, '%s.pgp' % filename), 'w') as f:
                f.write(str(asc_data))
                return
        else:
            print 'Error, %s' % asc_data.stderr

    if prompt_4_yes_no('Save unencrypted value'):
         with open(os.path.join(user, filename), 'w') as f:
             f.write(data)
    else:
        raise Exception("Data discarded, aborting")


########################################
##### Main
########################################

def main(args, default_args):

    # Configure the debug level
    configPrintException(args.debug)

    # Arguments
    profile_name = args.profile[0]
    if not args.users:
        print "Error, you need to provide at least one user name"
        return

    # Read credentials
    key_id, secret, token = read_creds(args.profile[0])

    # Connect to IAM
    iam_connection = connect_iam(key_id, secret, token)
    if not iam_connection:
        return

    # Initialize and compile the list of regular expression for category groups
    category_regex = init_iam_group_category_regex(default_args['category_groups'], default_args['category_regex'])

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
            pgp_and_write(user, 'password.txt', password)
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
        # Add user to a category group
        if len(default_args['category_groups']) > 0:
            add_user_to_category_group(iam_connection, args.groups, default_args['category_groups'], category_regex, user)

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
            qrcode_file = os.path.join(user, 'qrcode.png')
            pgp_and_write(user, 'qrcode.png', base64.b64decode(png))
            with open(qrcode_file, 'w') as f:
                f.write(base64.b64decode(png))
            fabulous.utils.term.bgcolor = 'white'
            print fabulous.image.Image(qrcode_file, 100)
            mfa_code1 = prompt_4_mfa_code()
            mfa_code2 = prompt_4_mfa_code()
            os.remove(qrcode_file)
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
        shutil.rmtree(user)


########################################
##### Parse arguments and call main()
########################################

init_parser()
default_args = read_profile_default_args(parser.prog)

parser.add_argument('--users',
                    dest='users',
                    default=None,
                    nargs='+',
                    help='User name(s) to create')
parser.add_argument('--groups',
                    dest='groups',
                    default=set_profile_default(default_args, 'common_groups', []),
                    nargs='+',
                    help='User name(s) to create')

args = parser.parse_args()

if __name__ == '__main__':
    main(args, default_args)
