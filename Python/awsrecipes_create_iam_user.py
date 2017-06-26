#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
import shutil
import sys
import zipfile

_gnupg_available = True
try:
    import gnupg
    gpg = gnupg.GPG(gnupghome = os.path.join(os.path.expanduser('~'), '.gnupg'))
except Exception as e:
    _gnupg_available = False
    print('Warning: gnupg not found; generated and downloaded credentials will not be encrypted at rest.')

from opinel.services.iam import create_user, init_iam_group_category_regex, delete_user
from opinel.utils.aws import connect_service
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError, printException, printInfo, prompt_4_mfa_serial, prompt_4_value, prompt_4_yes_no
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements


########################################
##### Helpers
########################################

def get_gpg_key(recipient):
    if _gnupg_available:
        gpg_key = None
        public_keys = gpg.list_keys()
        for k in public_keys:
            for uid in k['uids']:
                if re.match('.*%s.*' % recipient, uid):
                    return k
    return None


def gpg_and_write(filename, data, gpg_key, always_trust = False):
    if gpg_key:
        asc_data = gpg.encrypt(data, gpg_key['uids'],  always_trust = always_trust)
        if asc_data.ok:
            data = str(asc_data)
        else:
            printError(asc_data.stderr)
            printError('Error: failed to encrypt data')
            return
    with open(os.path.join(filename), 'wt') as f:
        f.write(data)


def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('user-name', help = 'Name of user(s) to be created.')
    parser.add_argument('group-name', help ='Name of group(s) the user(s) will belong to.')
    parser.add_argument('force-common-group', 
                        default=False,
                        action='store_true',
                        help='Automatically add user(s) to the common group(s)')
    parser.add_argument('no-mfa',
                        default=False,
                        action='store_true',
                        help='Do not configure and enable MFA.')
    parser.add_argument('no-password',
                        default=False,
                        action='store_true',
                        help='Do not create a password and login')
    parser.add_argument('no-access-key',
                        default=False,
                        action='store_true',
                        help='Do not generate an access key')
    parser.add_argument('always-trust',
                        default=False,
                        action='store_true',
                        help='A not generate an access key')
    parser.add_argument('allow-plaintext',
                        default=False,
                        action='store_true',
                        help='')
    parser.add_argument('no-prompt-before-plaintext',
                        dest='prompt_before_plaintext',
                        default=True,
                        action='store_false',
                        help='')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Arguments
    profile_name = args.profile[0]
    if not len(args.user_name):
        printError("Error, you need to provide at least one user name")
        return 42

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Connect to IAM
    iam_client = connect_service('iam', credentials)
    if not iam_client:
        return 42

    # Initialize and compile the list of regular expression for category groups
    #if 'category_groups' in default_args and 'category_regex' in default_args:
    #    category_regex = init_iam_group_category_regex(default_args['category_groups'], default_args['category_regex'])

    # Iterate over users
    for user in args.user_name:

        # Search for the GPG key
        abort = False
        gpg_key = get_gpg_key(user)
        if not gpg_key:
            printInfo('No PGP key found for user matching %s' % user)
            if args.allow_plaintext:
                if args.prompt_before_plaintext and not prompt_4_yes_no('Save unencrypted value'):
                    abort = True
            else:
                abort = True
        if abort:
            printError('Will not create user %s as credentials cannot be saved. Use --allow-plaintext to enable storage of unencrypted credentials.')
            continue

        # Prepare the output folder
        try:
            user_dir = 'users/%s' % user
            os.makedirs(user_dir)
        except Exception as e:
            printError('Error, failed to create a temporary folder for user %s.' % user)
            continue

        # Determine the groups Groups
        groups = args.group_name
        if args.force_common_group:
            groups += args.common_groups
        # Add user to a category group
#        if 'category_groups' in default_args and len(default_args['category_groups']) > 0:
#            add_user_to_category_group(iam_client, args.group_name, default_args['category_groups'], category_regex, user)

        # Create the user
        user_data = create_user(iam_client, user, groups, not args.no_password, not args.no_mfa, not args.no_access_key)
        if 'errors' in user_data and len(user_data['errors']) > 0:
            printError('Error doing the following actions:\n%s' % '\n'.join(' - %s' % action for action in user_data['errors']))

        # Save data
        if 'password' in user_data:
            gpg_and_write('%s/password.txt' % user_dir, user_data['password'], gpg_key, args.always_trust)
        if 'AccessKeyId' in user_data:
            credentials = '[%s]\naws_access_key_id = %s\naws_secret_access_key = %s\n' % (profile_name , user_data['AccessKeyId'], user_data['SecretAccessKey'])
            # TODO: mfa 
            gpg_and_write('%s/credentials' % user_dir, credentials, gpg_key, args.always_trust)
    
        # Create a zip archive
        f = zipfile.ZipFile('users/%s.zip' % user, 'w')
        for root, dirs, files in os.walk(user_dir):
            for file in files:
                f.write(os.path.join(root, file))
        f.close()
        shutil.rmtree(user_dir)


if __name__ == '__main__':
    sys.exit(main())

