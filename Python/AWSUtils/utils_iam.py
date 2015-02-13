#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *

# Import the Amazon SDK
import boto

# Import other third-party packages
import argparse
import fileinput
import os
import re
import sys
import shutil


########################################
##### Globals
########################################

re_profile_name = re.compile(r'\[\w+\]')
re_access_key = re.compile(r'aws_access_key_id')
re_secret_key = re.compile(r'aws_secret_access_key')
re_mfa_serial = re.compile(r'aws_mfa_serial')
re_session_token = re.compile(r'aws_session_token')

aws_credentials_file = os.path.join(os.path.join(os.path.expanduser('~'), '.aws'), 'credentials')
aws_credentials_file_no_mfa = os.path.join(os.path.join(os.path.expanduser('~'), '.aws'), 'credentials.no-mfa')
aws_credentials_file_tmp = os.path.join(os.path.join(os.path.expanduser('~'), '.aws'), 'credentials.tmp')


########################################
##### Helpers
########################################

#
# Fetch the IAM user name associated with the access key in use
#
def fetch_current_user_name(iam_connection, aws_key_id):
    user_name = None
    try:
        # Fetch all users
        users = handle_truncated_responses(iam_connection.get_all_users, None, ['list_users_response', 'list_users_result'], 'users')
        for user in users:
            keys = handle_truncated_responses(iam_connection.get_all_access_keys, user['user_name'], ['list_access_keys_response', 'list_access_keys_result'], 'access_key_metadata')
            for key in keys:
                if key['access_key_id'] == aws_key_id:
                    user_name = user['user_name']
                    break
            if user_name:
                break
        print 'Active user name is %s' % user_name
    except Exception, e:
        printException(e)
    return user_name

#
# Handle truncated responses
#
def handle_truncated_responses(callback, callback_args, result_path, items_name):
    marker_value = None
    items = []
    while True:
        if callback_args:
            result = callback(callback_args, marker = marker_value)
        else:
            result = callback(marker = marker_value)
        for key in result_path:
            result = result[key]
        marker_value = result['marker'] if result['is_truncated'] != 'false' else None
        items = items + result[items_name]
        if marker_value is None:
            break
    return items

#
# List an IAM user's access keys
#
def list_access_keys(iam_connection, user_name):
    keys = handle_truncated_responses(iam_connection.get_all_access_keys, user_name, ['list_access_keys_response', 'list_access_keys_result'], 'access_key_metadata')
    print 'User \'%s\' currently has %s access keys:' % (user_name, len(keys))
    for key in keys:
        print '\t%s (%s)' % (key['access_key_id'], key['status'])

#
# Prompt for MFA code
#
def prompt_4_mfa_code():
    while True:
        sys.stdout.write('Enter your MFA code: ')
        mfa_code = raw_input()
        try:
            int(mfa_code)
            mfa_code[5]
            break
        except:
            print 'Error, your MFA code must only consist of digits and be at least 6 characters long'
    return mfa_code

#
# Read credentials from AWS config file
#
def read_creds_from_aws_credentials_file(profile_name, credentials_file = aws_credentials_file):
    key_id = None
    secret = None
    mfa_serial = None
    session_token = None
    re_use_profile = re.compile(r'\[%s\]' % profile_name)
    with open(credentials_file, 'rt') as credentials:
        for line in credentials:
            if re_use_profile.match(line):
                profile_found = True
            elif re_profile_name.match(line):
                profile_found = False
            if profile_found:
                if re.match(r'aws_access_key_id', line):
                    key_id = (line.split(' ')[2]).rstrip()
                elif re.match(r'aws_secret_access_key', line):
                    secret = (line.split(' ')[2]).rstrip()
                elif re_mfa_serial.match(line):
                    mfa_serial = (line.split(' ')[2]).rstrip()
                elif re.match(r'aws_session_token', line):
                    session_token = (line.split(' ')[2]).rstrip()
    return key_id, secret, mfa_serial, session_token

#
# Write credentials to AWS config file
#
def write_creds_to_aws_credentials_file(profile_name, key_id = None, secret = None, session_token = None, credentials_file = aws_credentials_file):
    re_profile = re.compile(r'\[%s\]' % profile_name)
    profile_found = False
    profile_ever_found = False
    session_token_written = False
    # Copy credentials.no-mfa if target file does not exist
    if not os.path.isfile(credentials_file):
        shutil.copyfile(aws_credentials_file_no_mfa, credentials_file)
    # Open and parse/edit file
    for line in fileinput.input(credentials_file, inplace=True):
        if re_profile_name.match(line):
            if profile_name in line:
                profile_found = True
                profile_ever_found = True
                session_token_written = False
            else:
                # If we were editing the profile and haven't found a session_token line, write it before closing the profile
                if profile_found and session_token and not session_token_written:
                    print 'aws_session_token = %s' % session_token
                profile_found = False
            print line.rstrip()
        elif profile_found:
            if re_access_key.match(line) and key_id:
                print 'aws_access_key_id = %s' % key_id
            elif re_secret_key.match(line) and secret:
                print 'aws_secret_access_key = %s' % secret
            elif re_session_token.match(line) and session_token:
                print 'aws_session_token = %s' % session_token
                session_token_written = True
            else:
                print line.rstrip()
        else:
            print line.rstrip()

    # Add new profile if only found in .no-mfa configuration file
    if not profile_ever_found:
        with open(credentials_file, 'a') as f:
            f.write('[%s]\n' % profile_name)
            f.write('aws_access_key_id = %s\n' % key_id) # sts_response.access_key)
            f.write('aws_secret_access_key = %s\n' % secret) # ts_response.secret_key)
            if session_token:
                f.write('aws_session_token = %s\n' % session_token) # sts_response.session_token)


########################################
##### IAM-related arguments
########################################

parser.add_argument('--profile',
                    dest='profile_name',
                    default= [ 'default' ],
                    nargs='+',
                    help='Name of the profile')
