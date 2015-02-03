#!/usr/bin/env python2

# Import third-party packages
import argparse
import boto
import fileinput
import os
import re
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


########################################
##### Read and write config files
########################################

def manage_creds_from_aws_credentials(profile_name, sts_response = None):

    # Init
    key_id = None
    secret = None
    mfa_serial = None
    re_profile = re.compile(r'\[%s\]' % profile_name)
    profile_found = False
    profile_ever_found = False
    session_token_written = False

    # Copy no-mfa configuration to regular
    if sts_response:
        credentials_file = aws_credentials_file
    else:
        credentials_file = aws_credentials_file_no_mfa

    # Copy credentials.no-mfa to credentials if file does not exist
    if not os.path.isfile(aws_credentials_file):
        shutil.copyfile(aws_credentials_file_no_mfa, aws_credentials_file)

    # Open and parse/edit file
    for line in fileinput.input(credentials_file, inplace=True):
        if re_profile_name.match(line):
            if profile_name in line:
                profile_found = True
                profile_ever_found = True
                session_token_written = False
            else:
                # If we were editing the profile and haven't found a session_token line, write it before closing the profile
                if profile_found and sts_response and not session_token_written:
                    print 'aws_session_token = %s' % sts_response.session_token
                profile_found = False
            print line.rstrip()
        elif profile_found:
            if sts_response:
                if re_access_key.match(line):
                    print 'aws_access_key_id = %s' % sts_response.access_key
                elif re_secret_key.match(line):
                    print 'aws_secret_access_key = %s' % sts_response.secret_key
                elif re_session_token.match(line):
                    print 'aws_session_token = %s' % sts_response.session_token
                    session_token_written = True
                else:
                    print line.rstrip()
            else:
                if re_access_key.match(line):
                    key_id = line.split(' ')[2].rstrip()
                elif re_secret_key.match(line):
                    secret = line.split(' ')[2].rstrip()
                elif re_mfa_serial.match(line):
                    mfa_serial = line.split(' ')[2].rstrip()
                print line.rstrip()
        else:
            print line.rstrip()

    # Add new profile if only found in .no-mfa configuration file
    if not profile_ever_found and sts_response:
        with open(credentials_file, 'a') as f:
            f.write('[%s]\n' % profile_name)
            f.write('aws_access_key_id = %s\n' % sts_response.access_key)
            f.write('aws_secret_access_key = %s\n' % sts_response.secret_key)
            f.write('aws_session_token = %s\n' % sts_response.session_token)

    if not sts_response:
        return key_id, secret, mfa_serial


########################################
##### Main
########################################

def main(args):

    # Arguments
    profile_name = args.profile[0]
    mfa_code = args.mfa_code[0]

    # Parse config
    key_id, secret, mfa_serial = manage_creds_from_aws_credentials(profile_name)
    if key_id == None or secret == None or mfa_serial == None:
        print 'Failed to read configuration for profile %s' % profile_name
        return

    try:
        # Fetch session token, set duration to 8 hours
        sts_connection = boto.connect_sts(key_id, secret)
        sts_response = sts_connection.get_session_token(mfa_serial_number = mfa_serial, mfa_token = mfa_code, duration = 28800)

        # Write config
        manage_creds_from_aws_credentials(profile_name, sts_response)
    except Exception, e:
        print 'Failed to retrieve the session token'
        print e
        return

    print 'Successfully configure the session token for %s profile' % profile_name
    return


########################################
##### Argument parser
########################################

parser = argparse.ArgumentParser()

parser.add_argument('--profile',
                    dest='profile',
                    default= [ 'default' ],
                    nargs='+',
                    help='Name of the profile')
parser.add_argument('--mfa_code',
                    dest='mfa_code',
                    default=None,
                    nargs='+',
                    required='True',
                    help='MFA code')

args = parser.parse_args()

if __name__ == '__main__':
    main(args)
