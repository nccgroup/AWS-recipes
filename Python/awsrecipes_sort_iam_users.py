#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.services.iam import create_groups, init_group_category_regex
from opinel.utils.aws import connect_service, handle_truncated_response
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError, printException, printInfo
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements
from opinel.utils.threads import thread_work


########################################
##### Helpers
########################################

def get_group_membership(q, params):
    iam_client = params['iam_client']
    user_info  = params['user_info']
    while True:
        try:
            user = q.get()
            user_name = user['UserName']
            groups = iam_client.list_groups_for_user(UserName = user_name)['Groups']
            user_info[user_name] = {}
            user_info[user_name]['groups'] = []
            for group in groups:
                user_info[user_name]['groups'].append(group['GroupName'])
            show_status(user_info, newline = False)
        except Exception as e:
            printException(e)
        finally:
            q.task_done()

def show_status(user_info, total = None, newline = True):
    if total != None:
        show_status.total = total
    current = len(user_info)
    sys.stdout.write("\r%d/%d" % (current, show_status.total))
    if newline:
        sys.stdout.write('\n')
    sys.stdout.flush()
show_status.total = 0

########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('common-groups',
                        default=[],
                        nargs='+',
                        help='List of groups each IAM user should belong to.')
    parser.add_argument('category-groups',
                        default=[],
                        nargs='+',
                        help='List of category groups; each IAM user must belong to one.')
    parser.add_argument('category-regex',
                        default=[],
                        nargs='+',
                        help='List of regex enabling auto-assigment of category groups.')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Read creds
    credentials = read_creds(args.profile[0])
    if not credentials['AccessKeyId']:
        return 42

    # Connect to IAM APIs
    iam_client = connect_service('iam', credentials)
    if not iam_client:
        return 42

    # Initialize and compile the list of regular expression for category groups
    category_regex = init_group_category_regex(args.category_groups, args.category_regex)

    # Ensure all default groups exist
    create_groups(iam_client, args.category_groups + args.common_groups)

    # Download IAM users and their group memberships
    printInfo('Downloading group membership information...')
    user_info = {}
    users = handle_truncated_response(iam_client.list_users, {}, [ 'Users' ])['Users']
    show_status(user_info, total = len(users), newline = False)
    thread_work(users, get_group_membership, {'iam_client': iam_client, 'user_info': user_info}, num_threads = 30)
    show_status(user_info)

    # Iterate through users
    for user in user_info:
        printInfo('Checking configuration of \'%s\'...' % user)
        for group in args.common_groups:
            if group not in user_info[user]['groups']:
                printInfo(' - Adding to common group: %s' % group)
                iam_client.add_user_to_group(UserName = user, GroupName = group)
        category_found = False
        for i, regex in enumerate(category_regex):
            if regex and regex.match(user):
                category_found = True
                group = args.category_groups[i]
                if group not in user_info[user]['groups']:
                    printInfo(' - Adding to category group: %s' % group)
                    iam_client.add_user_to_group(UserName = user, GroupName = group)
            elif not regex:
                default_group = args.category_groups[i]
        if not category_found and default_group not in user_info[user]['groups']:
            printInfo(' - Adding to default category group: %s' % default_group)
            iam_client.add_user_to_group(UserName = user, GroupName = default_group)


if __name__ == '__main__':
    sys.exit(main())
