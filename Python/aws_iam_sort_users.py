#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *

# Import third-party packages
import re


########################################
##### Helpers
########################################

def get_group_membership(iam_connection, q, params):
    while True:
        try:
            user_info, user = q.get()
            user_name = user['user_name']
            groups = iam_connection.get_groups_for_user(user_name)
            groups = groups['list_groups_for_user_response']['list_groups_for_user_result']['groups']
            user_info[user_name] = {}
            user_info[user_name]['groups'] = []
            for group in groups:
                user_info[user_name]['groups'].append(group['group_name'])
            show_status(user_info, newline = False)
        except Exception, e:
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

    # Arguments
    profile_name = args.profile[0]

    # Initialize and compile the list of regular expression for category groups
    category_regex = init_iam_group_category_regex(args.category_groups, args.category_regex)

    # Connect to IAM
    key_id, secret, session_token = read_creds(profile_name)
    if not key_id:
        print 'Error: could not find AWS credentials. Use the --help option for more information.'
        return 42
    iam_connection = connect_iam(key_id, secret, session_token)
    if not iam_connection:
        print 'Error: could not connect to IAM.'
        return 42

    # Create the groups
    if args.create_groups and not args.dry_run:
        for group in args.common_groups + args.category_groups:
            try:
                print 'Creating group \'%s\'...' % group
                iam_connection.create_group(group)
            except Exception, e:
                printException(e)

    # Download IAM users and their group memberships
    print 'Downloading group membership information...'
    user_info = {}
    users = handle_truncated_responses(iam_connection.get_all_users, None, ['list_users_response', 'list_users_result'], 'users')
    show_status(user_info, total = len(users), newline = False)
    thread_work(iam_connection, user_info, users, get_group_membership, num_threads = 30)
    show_status(user_info)

    # Output
    all_checked_groups = set(args.common_groups + args.category_groups)
    if args.output_file[0]:
        try:
            f = open(args.output_file[0], 'wt')
            f.write('username, %s\n' % (', '.join(all_checked_groups)))
        except Exception, e:
            printException(e)

    # Iterate through users
    test = 0
    for user in user_info:
        print 'Checking configuration of \'%s\'...' % user
        add_user_to_common_group(iam_connection, user_info[user]['groups'], args.common_groups, user, args.force_common_group, user_info, args.dry_run)
        add_user_to_category_group(iam_connection, user_info[user]['groups'], args.category_groups, category_regex, user, user_info, args.dry_run)
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

init_parser()
saved_args = read_profile_default_args(parser.prog)

parser.add_argument('--create_groups',
                    dest='create_groups',
                    default=set_profile_default(saved_args, 'create_groups', False),
                    action='store_true',
                    help='Create the default groups if they do not exist')
parser.add_argument('--common_groups',
                    dest='common_groups',
                    default=set_profile_default(saved_args, 'common_groups', []),
                    nargs='+',
                    help='Groups that all IAM users should belong to.')
parser.add_argument('--category_groups',
                    dest='category_groups',
                    default=set_profile_default(saved_args, 'category_groups', []),
                    nargs='+',
                    help='Choice of groups that all IAM users should belong to.')
parser.add_argument('--category_regex',
                    dest='category_regex',
                    default=set_profile_default(saved_args, 'category_regex', []),
                    nargs='+',
                    help='Regex used to automatically add users to a category group.')
parser.add_argument('--force_common_group',
                    dest='force_common_group',
                    default=set_profile_default(saved_args, 'force_common_group', False),
                    action='store_true',
                    help='Automatically add users to the common groups.')
parser.add_argument('--dry',
                    dest='dry_run',
                    default=set_profile_default(saved_args, 'dry_run', False),
                    action='store_true',
                    help='Check the status for user but do not take action.')
parser.add_argument('--out',
                    dest='output_file',
                    default=[ None ],
                    nargs='+',
                    help='Name of the output file.')

args = parser.parse_args()

if __name__ == '__main__':
    main(args)
