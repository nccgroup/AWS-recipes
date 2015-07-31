#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_iam import *

# Import stock packages
import base64
import os
import random
import re
import string
import sys
import time
import zipfile

# Import third-party packages
_gnupg_available = True
try:
    import gnupg
except Exception as e:
    _gnupg_available = False
    pass

########################################
##### Helpers
########################################
def cleanup(iam_client, user, local_only = False, mfa_serial = None):
    printInfo('Cleaning up...')
    time.sleep(5)
    if not local_only:
        delete_user(iam_client, user)
    shutil.rmtree(user)

def generate_password(length = 16):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + '!@#$%^&*()_+`-=[]{};:,<.>?/\\|') for _ in xrange(length))

def pgp_and_write(user, filename, data):
    if not _gnupg_available:
        return
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
            printError('Error, %s' % asc_data.stderr)

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
    if not len(args.user_name):
        printError("Error, you need to provide at least one user name")
        return 42

    # Connect to IAM
    try:
        key_id, secret, session_token = read_creds(profile_name)
        iam_client = connect_iam(key_id, secret, session_token)
    except Exception as e:
        printException(e)
        return 42

    # Initialize and compile the list of regular expression for category groups
    category_regex = init_iam_group_category_regex(default_args['category_groups'], default_args['category_regex'])

    # Iterate over users
    for user in args.user_name:

        # Status
        printInfo('Creating user %s...' % user)
        password = ''

        # Prepare the output folder
        try:
            os.mkdir(user)
        except Exception as e:
            printError('Failed to create a temporary folder for user %s.' % user)
            return 42

        # Create the new IAM user
        try:
            iam_client.create_user(UserName = user)
        except Exception as e:
            printException(e)
            cleanup(iam_client, user, True)
            return 42

        # Password enabled?
        if not args.no_password:
            # Generate and save a random password
            try:
                password = generate_password()
                pgp_and_write(user, 'password.txt', password)
            except Exception as e:
                printException(e)
                cleanup(iam_client, user)
                return 42
            # Create a login profile
            try:
                iam_client.create_login_profile(UserName = user, Password = password, PasswordResetRequired = True)
            except Exception as e:
                printException(e)
                cleanup(iam_client, user)
                return 42

        # Add user to groups
        for group in args.group_name:
            try:
                printInfo('Adding user to group %s...' % group)
                iam_client.add_user_to_group(GroupName = group, UserName = user)
            except Exception as e:
                printException(e)
                cleanup(iam_client, user)
                return 42
        # Add user to the common group(s)
        add_user_to_common_group(iam_client, args.group_name, default_args['common_groups'], user, args.force_common_group)
        # Add user to a category group
        if len(default_args['category_groups']) > 0:
            add_user_to_category_group(iam_client, args.group_name, default_args['category_groups'], category_regex, user)

        # MFA enabled?
        if not args.no_mfa:
            printInfo('Enabling MFA for user %s...' % user)
            serial = ''
            mfa_code1 = ''
            mfa_code2 = ''
            # Create an MFA device, Display the QR Code, and activate the MFA device
            try:
                mfa_serial = enable_mfa(iam_client, user, '%s/qrcode.png' % user)
            except Exception as e:
                cleanup(iam_client, user)
                return 42

        # Access key enabled?
        if not args.no_access_key:
            printInfo('Creating a new access key for user %s...' % user)
            try:
                access_key = iam_client.create_access_key(UserName = user)['AccessKey']                
                id_and_secret = 'Access Key ID: %s\nSecret Access Key: %s' % (access_key['AccessKeyId'], access_key['SecretAccessKey'])
                pgp_and_write(user, 'access_key.txt', id_and_secret)
            except Exception as e:
                printException(e)
                cleanup(iam_client, user)
                return 42

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

default_args = read_profile_default_args(parser.prog)

parser.add_argument('--user-name',
                    dest='user_name',
                    default=[],
                    nargs='+',
                    help='Name of user(s) to be created')
parser.add_argument('--group-name',
                    dest='group_name',
                    default=[],
                    nargs='+',
                    help='Name of group(s) that the user(s) will belong to')
parser.add_argument('--force-common-group',
                    dest='force_common_group',
                    default=set_profile_default(default_args, 'force_common_group', False),
                    action='store_true',
                    help='Automatically add user(s) to the common group(s)')
parser.add_argument('--no-mfa',
                    dest='no_mfa',
                    default=set_profile_default(default_args, 'no_mfa', False),
                    action='store_true',
                    help='Do not configure and enable MFA')
parser.add_argument('--no-password',
                    default=set_profile_default(default_args, 'no_password', False),
                    action='store_true',
                    help='Do not create a password and login')
parser.add_argument('--no-access-key',
                    dest='no_access_key',
                    default=set_profile_default(default_args, 'no_access_key', False),
                    action='store_true',
                    help='Do not generate an access key')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args, default_args))
