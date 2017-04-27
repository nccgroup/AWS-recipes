#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import os
import sys
import tempfile
import webbrowser

# Import third-party packages
_fabulous_available = True
try:
    import fabulous.utils
    import fabulous.image
    # fabulous does not import its PIL dependency on import time, so
    # force it to check them now so we know whether it's really usable
    # or not.  If it can't import PIL it raises ImportError.
    fabulous.utils.pil_check()
except ImportError:
    _fabulous_available = False
    pass

from opinel.utils.aws import connect_service
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError, printException, printInfo, prompt_4_mfa_code
from opinel.utils.credentials import read_creds, write_creds_to_aws_credentials_file
from opinel.utils.globals import check_requirements


########################################
##### Helpers
########################################

def delete_virtual_mfa_device(iam_client, mfa_serial):
    """
    Delete a vritual MFA device given its serial number

    :param iam_client:
    :param mfa_serial:
    :return:
    """
    try:
        printInfo('Deleting MFA device %s...' % mfa_serial)
        iam_client.delete_virtual_mfa_device(SerialNumber = mfa_serial)
    except Exception as e:
        printException(e)
        printError('Failed to delete MFA device %s' % mfa_serial)
        pass


def display_qr_code(png, seed):
    """
    Display MFA QR code
    :param png:
    :param seed:
    :return:
    """
    # This NamedTemporaryFile is deleted as soon as it is closed, so
    # return it to caller, who must close it (or program termination
    # could cause it to be cleaned up, that's fine too).
    # If we don't keep the file around until after the user has synced
    # his MFA, the file will possibly be already deleted by the time
    # the operating system gets around to execing the browser, if
    # we're using a browser.
    qrcode_file = tempfile.NamedTemporaryFile(suffix='.png', delete=True, mode='wt')
    qrcode_file.write(png)
    qrcode_file.flush()
    if _fabulous_available:
        fabulous.utils.term.bgcolor = 'white'
        with open(qrcode_file.name, 'rb') as png_file:
            print(fabulous.image.Image(png_file, 100))
    else:
        graphical_browsers = [webbrowser.BackgroundBrowser,
                              webbrowser.Mozilla,
                              webbrowser.Galeon,
                              webbrowser.Chrome,
                              webbrowser.Opera,
                              webbrowser.Konqueror]
        if sys.platform[:3] == 'win':
            graphical_browsers.append(webbrowser.WindowsDefault)
        elif sys.platform == 'darwin':
            graphical_browsers.append(webbrowser.MacOSXOSAScript)

        browser_type = None
        try:
            browser_type = type(webbrowser.get())
        except webbrowser.Error:
            pass

        if browser_type in graphical_browsers:
            printError("Unable to print qr code directly to your terminal, trying a web browser.")
            webbrowser.open('file://' + qrcode_file.name)
        else:
            printInfo("Unable to print qr code directly to your terminal, and no graphical web browser seems available.")
            printInfo("But, the qr code file is temporarily available as this file:")
            printInfo("\n    %s\n" % qrcode_file.name)
            printInfo("Alternately, if you feel like typing the seed manually into your MFA app:")
            # this is a base32-encoded binary string (for case
            # insensitivity) which is then dutifully base64-encoded by
            # amazon before putting it on the wire.  so the actual
            # secret is b32decode(b64decode(seed)), and what users
            # will need to type in to their app is just
            # b64decode(seed).  print that out so users can (if
            # desperate) type in their MFA app.
            printInfo("\n    %s\n" % base64.b64decode(seed))
    return qrcode_file


def enable_mfa(iam_client, user, qrcode_file = None):
    """
    Create and activate an MFA virtual device

    :param iam_client:
    :param user:
    :param qrcode_file:
    :return:
    """
    mfa_serial = ''
    tmp_qrcode_file = None
    try:
        printInfo('Enabling MFA for user \'%s\'...' % user)
        mfa_device = iam_client.create_virtual_mfa_device(VirtualMFADeviceName = user)['VirtualMFADevice']
        mfa_serial = mfa_device['SerialNumber']
        mfa_png = mfa_device['QRCodePNG']
        mfa_seed = mfa_device['Base32StringSeed']
        tmp_qrcode_file = display_qr_code(mfa_png, mfa_seed)
        if qrcode_file != None:
            with open(qrcode_file, 'wt') as f:
                f.write(mfa_png)
        while True:
            mfa_code1 = prompt_4_mfa_code()
            mfa_code2 = prompt_4_mfa_code(activate = True)
            if mfa_code1 == 'q' or mfa_code2 == 'q':
                try:
                    delete_virtual_mfa_device(iam_client, mfa_serial)
                except Exception as e:
                    printException(e)
                    pass
                raise Exception
            try:
                iam_client.enable_mfa_device(UserName = user, SerialNumber = mfa_serial, AuthenticationCode1= mfa_code1, AuthenticationCode2 = mfa_code2)
                printInfo('Succesfully enabled MFA for for \'%s\'. The device\'s ARN is \'%s\'.' % (user, mfa_serial))
                break
            except Exception as e:
                printException(e)
                pass
    except Exception as e:
        printException(e)
        # We shouldn't return normally because if we've gotten here
        # the user has potentially not set up the MFA device
        # correctly, so we don't want to e.g. write the .no-mfa
        # credentials file or anything.
        raise
    finally:
        if tmp_qrcode_file is not None:
            # This is a tempfile.NamedTemporaryFile, so simply closing
            # it will also unlink it.
            tmp_qrcode_file.close()
    return mfa_serial

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('user-name', help_string = 'Your username (automatically fetched using iam:GetUser if not provided).')

    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Arguments
    profile_name = args.profile[0]
    user_name = args.user_name[0]

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Connect to IAM
    iam_client = connect_service('iam', credentials)
    if not iam_client:
        printError('Error: failed to create IAM API client.')
        return 42

    # Set the user name
    if not user_name:
        try:
            printInfo('Searching for username...')
            user_name = iam_client.get_user()['User']['UserName']
            if not user_name:
                printInfo('Error: could not find user name to enable MFA for.')
                return 42
        except Exception as e:
            configPrintException(e)

    # Create and activate the MFA device
    credentials['SerialNumber'] = enable_mfa(iam_client, user_name)

    # Update the credentials file
    write_creds_to_aws_credentials_file(profile_name, credentials)
    sample_command = 'awsrecipes_init_sts_session.py %s' % (('--profile %s' % profile_name) if profile_name != 'default' else '')
    printInfo('Your credentials file has been updated.\n' \
              'You may now initiate STS sessions to access the AWS APIs with the following command:\n' \
              '\n    %s\n' % sample_command)

if __name__ == '__main__':
    sys.exit(main())
