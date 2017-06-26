#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_iam import *

# Import stock packages
import re
import sys


########################################
##### Helpers
########################################

def get_group_membership(iam_client, q, params):
    while True:
        try:
            user_info, user = q.get()
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

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_opinel_version('1.0.4'):
        return 42

    # Arguments
    profile_name = args.profile[0]

    # Initialize and compile the list of regular expression for category groups
    category_regex = init_iam_group_category_regex(args.category_groups, args.category_regex)

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Connect to IAM
    iam_client = connect_iam(credentials)
    if not iam_client:
        return 42

    # Create the groups
    if args.create_groups and not args.dry_run:
        for group in args.common_groups + args.category_groups:
            try:
                printInfo('Creating group \'%s\'...' % group)
                iam_client.create_group(GroupName = group)
            except Exception as e:
                printException(e)

    # Download IAM users and their group memberships
    printInfo('Downloading group membership information...')
    user_info = {}
    users = handle_truncated_responses(iam_client.list_users, {}, 'Users')
    show_status(user_info, total = len(users), newline = False)
    thread_work(iam_client, user_info, users, get_group_membership, num_threads = 30)
    show_status(user_info)

    # Output
    all_checked_groups = set(args.common_groups + args.category_groups)
    if args.output_file[0]:
        try:
            f = open(args.output_file[0], 'wt')
            f.write('username, %s\n' % (', '.join(all_checked_groups)))
        except Exception as e:
            printException(e)

    # Iterate through users
    test = 0
    for user in user_info:
        printInfo('Checking configuration of \'%s\'...' % user)
        add_user_to_common_group(iam_client, user_info[user]['groups'], args.common_groups, user, args.force_common_group, user_info, args.dry_run)
        add_user_to_category_group(iam_client, user_info[user]['groups'], args.category_groups, category_regex, user, user_info, args.dry_run)
        if args.output_file[0] and f:
            f.write('%s' % user)
            for g in all_checked_groups:
                f.write(', %s' % ('x' if g in user_info[user]['groups'] else ''))
            f.write('\n')
    if args.output_file[0] and f:
        f.close()


########################################
##### Parse arguments and call main()
########################################

default_args = read_profile_default_args(parser.prog)

parser.add_argument('--create-groups',
                    dest='create_groups',
                    default=set_profile_default(default_args, 'create_groups', False),
                    action='store_true',
                    help='Create the default groups if they do not exist')
parser.add_argument('--category-regex',
                    dest='category_regex',
                    default=set_profile_default(default_args, 'category_regex', []),
                    nargs='+',
                    help='Regex used to automatically add users to a category group.')
parser.add_argument('--force-common-group',
                    dest='force_common_group',
                    default=set_profile_default(default_args, 'force_common_group', False),
                    action='store_true',
                    help='Automatically add users to the common groups.')
parser.add_argument('--out',
                    dest='output_file',
                    default=[ None ],
                    nargs='+',
                    help='Name of the output file.')

add_common_argument(parser, default_args, 'dry-run')
add_iam_argument(parser, default_args, 'common-groups')
add_iam_argument(parser, default_args, 'category-groups')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
