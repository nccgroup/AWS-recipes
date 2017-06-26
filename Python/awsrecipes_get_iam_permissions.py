#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
import sys

from iampoliciesgonewild import all_permissions, expand_policy

from opinel.utils.aws import connect_service, handle_truncated_response
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printInfo, printException
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements, manage_dictionary

########################################
##### Globals
########################################

PERMISSIONS_DIR = 'permissions'
re_arn = re.compile(r'^arn:(\w+?):(\w+?):(\w*?):(\d*?):(.*?)$')

########################################
##### Helpers
########################################

#
# Determine whether two statements can be merged
#
def can_merge_statements(s1, s2):
    # Action or NotAction ?
    s1_action_type = 'Action' if 'Action' in s1 else 'NotAction'
    s2_action_type = 'Action' if 'Action' in s2 else 'NotAction'
    # Resource or NotResource ?
    s1_resource_type = 'Resource' if 'Resource' in s1 else 'NotResource'
    s2_resource_type = 'Resource' if 'Resource' in s2 else 'NotResource'
    if s1['Effect'] == s2['Effect'] and s1_action_type == s2_action_type and s1_resource_type == s2_resource_type and s1[s1_resource_type] == s2[s2_resource_type]:
        if ((('Condition' in s1 and 'Condition' in s2) and s1['Condition'] == s2['Condition']) or ('Condition' not in s1 and 'Condition' not in s2)):
            return True
    return False



#
# Extract value from an ARN
#
def get_value_from_arn(field, arn):
    value = None
    arn_match = re_arn.match(arn)
    if arn_match:
        if field == 'account_id':
            value = arn_match.groups()[3]
        if field == 'resource':
            value = arn_match.groups()[4].split('/')
    return value

#
# Get managed policy
#
def get_managed_policy_document(iam_client, policy_arn, managed_policies):
    policy_document = None
    print('Fetching managed policy %s...' % policy_arn)
    # Check if we already downloaded that managed policy...
    if policy_arn in managed_policies:
        policy_document = managed_policies[policy_arn]
    else:
        try:
            policy = iam_client.get_policy(PolicyArn = policy_arn)['Policy']
            policy_document = iam_client.get_policy_version(PolicyArn = policy_arn, VersionId = policy['DefaultVersionId'])['PolicyVersion']['Document']
            # Cache managed policies to avoid multiple download when attached to multiple IAM resources
            manage_dictionary(managed_policies, policy_arn, policy_document)
        except Exception as e:
            printException(e)
    return policy_document

#
# Get all policies that apply to an IAM group, role, or user
#
def get_policies(iam_client, managed_policies, resource_type, resource_name):
    print('Fetching policies for IAM %s %s...' % (resource_type, resource_name))
    fetched_policies = []
    # Managed policies
    list_policy_method = getattr(iam_client, 'list_attached_' + resource_type + '_policies')
    policy_names = 'AttachedPolicies'
    args = {}
    args[resource_type.title() + 'Name'] = resource_name
    try:
        policies = list_policy_method(**args)[policy_names]
        for policy in policies:
            try:
                policy_arn = policy['PolicyArn']
                fetched_policies.append(get_managed_policy_document(iam_client, policy_arn, managed_policies))
            except Exception as e:
                printException(e)
    except Exception as e:
        printException(e)
    # Inline policies
    get_policy_method = getattr(iam_client, 'get_' + resource_type + '_policy')
    list_policy_method = getattr(iam_client, 'list_' + resource_type + '_policies')
    policy_names = 'PolicyNames'
    args = {}
    args[resource_type.title() + 'Name'] = resource_name
    try:
        policy_names = list_policy_method(**args)[policy_names]
    except Exception as e:
        printException(e)
    for policy_name in policy_names:
        try:
            args['PolicyName'] = policy_name
            policy_document = get_policy_method(**args)['PolicyDocument']
            fetched_policies.append(policy_document)
        except Exception as e:
            printException(e)
    # Group policies (for users only)
    if resource_type == 'user':
        groups = []
        for group in iam_client.list_groups_for_user(UserName = resource_name)['Groups']:
            fetched_policies = fetched_policies + get_policies(iam_client, managed_policies, 'group', group['GroupName'])
    return fetched_policies


def merge_policies(policy_documents):
    """
    Merge multiple policy documents into a single, combined policy
    Actions of allow statements defined with the same resources and conditions are combined into a unique list
                                        .
    :param policy_documents:            Policy documents to be merged (e.g. all user and group policies applying to a single user)
    :return:                            Combined policy
    """
    macro_policy = {'Version': '', 'Statement': []}
    for policy_document in policy_documents:
        if not policy_document:
            continue
        expand_policy(policy = policy_document)
        if 'Version' in policy_document:
            macro_policy['Version'] = policy_document['Version'] if policy_document['Version'] > macro_policy['Version'] else policy_document['Version']
        for s1 in policy_document['Statement']:
            merged = False
            s1_action_type, s1_resource_type = normalize_statement(s1)
            for s2 in macro_policy['Statement']:
                s2_action_type, s2_resource_type = normalize_statement(s2)
                if can_merge_statements(s1, s2):
                    s2[s2_action_type] = sorted(list(set(s1[s1_action_type] + s2[s2_action_type])))
                    merged = True
            if not merged:
                if 'Sid' in s1:
                    s1.pop('Sid')
                s1[s1_action_type] = sorted(list(set(s1[s1_action_type])))
                macro_policy['Statement'].append(s1)
    return macro_policy

#
# Make sure action and resource are formatted as a list
# Return type of policy: Action/NotAction + Resource/NotResource
#
def normalize_statement(statement):
    # Action or NotAction ?
    action_type = 'Action' if 'Action' in statement else 'NotAction'
    # Resource or NotResource ?
    resource_type = 'Resource' if 'Resource' in statement else 'NotResource'
    # Make sure action type is a list
    if type(statement[action_type]) != list:
        statement[action_type] = [ statement[action_type] ]
    # Make sure resource type is a list
    if type(statement[resource_type]) != list:
        statement[resource_type] = [ statement[resource_type] ]
    return action_type, resource_type

#
# Expand permissions and write the document to a file
#
def write_permissions(policy_document, resource_type, resource_name):
        #merged_policy_document = merge_policies(policy_documents, all_permissions)
        target_dir = os.path.join(PERMISSIONS_DIR, resource_type)
        if resource_type == 'policy':
            # Extract account ID from policy arn and make sub folder per account
            account_id = get_value_from_arn('account_id', resource_name)
            account_id = account_id if account_id else 'AWS'
            target_dir = os.path.join(target_dir, account_id)
            resource_name = resource_name.split('/')[-1]
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
        with open (os.path.join(target_dir, '%s.json' % resource_name), 'wt') as f:
            f.write(json.dumps(policy_document, indent = 4, sort_keys = True))


########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('user-name', help = 'Name of the IAM user(s).')
    parser.parser.add_argument('--all-users',
                               dest='all_users',
                               default=False,
                               action='store_true',
                               help='Go through all IAM users')
    parser.parser.add_argument('--arn',
                        dest='arn',
                        default=[],
                        nargs='+',
                        help='ARN of the target group(s), role(s), or user(s)')
    parser.parser.add_argument('--group-name',
                        dest='group_name',
                        default=[],
                        nargs='+',
                        help='Name of the IAM group(s)')
    parser.parser.add_argument('--all-groups',
                                dest='all_groups',
                               default=False,
                               action='store_true',
                               help='Go through all IAM groups')
    parser.parser.add_argument('--role-name',
                        dest='role_name',
                        default=[],
                        nargs='+',
                        help='Name of the IAM role(s)')
    parser.parser.add_argument('--all-roles',
                                dest='all_roles',
                               default=False,
                               action='store_true',
                               help='Go through all IAM roles')
    parser.parser.add_argument('--policy-arn',
                        dest='policy_arn',
                        default=[],
                        nargs='+',
                        help='ARN of the IAM policy/ies')
    parser.parser.add_argument('--all',
                        dest='all',
                        default=False,
                        action='store_true',
                        help='Go through all IAM resources')

    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Arguments
    profile_name = args.profile[0]

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Connect to IAM
    iam_client = connect_service('iam', credentials)
    if not iam_client:
        return 42

    # Normalize targets
    targets = []
    for arn in args.arn:
        arn_match = re_arn.match(arn)
        if arn_match:
            resource = arn_match.groups()[4].split('/')
            targets.append((resource[0], resource[-1]))
    for group_name in args.group_name:
        if group_name:
            targets.append(('group', group_name))
    for role_name in args.role_name:
        if role_name:
            targets.append(('role', role_name))
    for user_name in args.user_name:
        if user_name:
            targets.append(('user', user_name))
    if args.all or args.all_groups:
        printInfo('Fetching all IAM groups...')
        for group in handle_truncated_response(iam_client.list_groups, {}, ['Groups'])['Groups']:
            targets.append(('group', group['GroupName']))
    if args.all or args.all_roles:
        printInfo('Fetching all IAM roles...')
        for role in handle_truncated_response(iam_client.list_roles, {}, ['Roles'])['Roles']:
            targets.append(('role', role['RoleName']))
    if args.all or args.all_users:
        printInfo('Fetching all IAM users...')
        for user in handle_truncated_response(iam_client.list_users, {}, ['Users'])['Users']:
            targets.append(('user', user['UserName']))

    # Get all policies that apply to the targets and aggregate them into a single file
    printInfo('Fetching all inline and managed policies in use...')
    managed_policies = {}
    for resource_type, resource_name in targets:
        policy_documents = get_policies(iam_client, managed_policies, resource_type, resource_name)
        write_permissions(merge_policies(policy_documents), resource_type, resource_name)

    # Get requested managed policies
    for policy_arn in args.policy_arn:
        policy_documents = [ get_managed_policy_document(iam_client, policy_arn, managed_policies) ]
        write_permissions(merge_policies(policy_documents), 'policy', policy_arn)


########################################
##### Parse arguments and call main()
########################################




if __name__ == '__main__':
    sys.exit(main())
