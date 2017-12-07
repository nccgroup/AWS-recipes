#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import pytz
import re
import sys
import time

import json
import yaml

from opinel.utils.aws import build_region_list, connect_service, get_aws_account_id, handle_truncated_response
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printInfo, printException, printDebug, printError, prompt_4_yes_no
from opinel.utils.credentials import read_creds
from opinel.utils.fs import load_data
from opinel.utils.globals import check_requirements, snake_to_camel, snake_to_words

from opinel.services.cloudformation import create_stack, create_stack_instances, create_stack_set, get_stackset_ready_accounts, make_awsrecipes_stack_name, update_stack, update_stack_set, create_or_update_stack

from opinel.services.cloudformation import create_or_update_stack, create_or_update_stack_set

from opinel.services.organizations import get_organization_account_ids

awsrecipes_cf_templates_dir = os.path.join((os.path.dirname(os.path.realpath(__file__))), '../CloudFormationTemplates')


def get_cloudformation_templates(stack_prefix):
    templates = {
        'master_stacks': {},
        'master_stack_sets': {},
        'target_stack_sets': {}
    }
    file_names = os.listdir(awsrecipes_cf_templates_dir)
    for file_name in file_names:
        unknown_template_type = False
        # Does the prefix match ?
        if not file_name.startswith('%s-' % stack_prefix):
            continue
        file_path = os.path.join(awsrecipes_cf_templates_dir, file_name)
        stack_name = 'AWSRecipes-%s' % file_name.split('.')[0].replace('-Global', '').replace('-Master', '').replace('-Wait', '')

        if re.match(r'.*?-Wait\..*?', file_name) == None:
            wait_for_completion = False
        else:
            wait_for_completion = True
        cf_name = file_name.replace('%s-' % stack_prefix, '')

        # Type of template
        if cf_name.startswith('Master'):
            if re.match(r'.*?-Global[-\.].*?', cf_name):
                templates['master_stacks'][stack_name] = {'file_path': file_path, 'wait_for_completion': wait_for_completion}
            elif re.match(r'.*?-Region[-\.].*?', cf_name):
                templates['master_stack_sets'][stack_name] = {'file_path': file_path, 'wait_for_completion': wait_for_completion}
            else:
                unknown_template_type = True
        elif cf_name.startswith('Target'):
            templates['target_stack_sets'][stack_name] = {'file_path': file_path, 'wait_for_completion': wait_for_completion}
#        elif cf_name.startswith('Nested'):
#            pass
        else:
            unknown_template_type = True
        if unknown_template_type:
            printError('Error: don\'t know how to process template with name %s' % file_name)
    return templates


def resource_older_than_template(resource_type, resource, template_filename):
    resource_modification_time = 0
    # Check if there is a need for an update
    if resource_type == 'stack':
        resource_modification_time = resource['LastUpdatedTime'] if 'LastUpdatedTime' in resource else resource['CreationTime']
        print('Resource time: %s' % resource_modification_time)
    else:
        printInfo(json.dumps(resource, indent = 4))
        for tag in resource['Tags']:
            if tag['Key'] == 'LastUpdatedTime':
                resource_modification_time = datetime.datetime.utcfromtimestamp(float(tag['Value'])).replace(tzinfo=pytz.utc)
                break
    print('Resource time: %s' % resource_modification_time)
    template_modification_time = get_template_modification_time(template_filename)
    print('Template time: %s' % template_modification_time)
    if resource_modification_time == 0 or resource_modification_time < template_modification_time:
        print('The template for %s was modified after the %s was last updated.' % (resource['%sName' % snake_to_camel(resource_type)], snake_to_words(resource_type)))
        return True
    else:
        return False


def get_template_modification_time(template_filename, return_timestamp = False):
    timestamp = os.path.getmtime(os.path.join(awsrecipes_cf_templates_dir, template_filename))
    if return_timestamp:
        return timestamp
    else:
        return datetime.datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)



########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('regions', help = 'Regions where stack instances will be created.')
    parser.add_argument('partition-name')
    parser.parser.add_argument('--master-region',
                               dest='master_region',
                               default=None,
                               required=True,
                               help='Region where the global stacks and stack sets will be created.')
    parser.parser.add_argument('--stack-prefix',
                               dest='stack_prefix',
                               default=None,
                               required=True,
                               help='Prefix of the CF Templates to be used when creating/updating stacks.')
    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42

    # Get profile name
    profile_name = args.profile[0]

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Get the master AWS account ID
    master_account_id = get_aws_account_id(credentials)

    # Get list of accounts ready for Stack sets
    api_client = connect_service('organizations', credentials, silent = True)
    try:
        org_account_ids = get_organization_account_ids(api_client, quiet = False)
    except:
        org_account_ids = [ master_account_id ]
    configured_org_account_ids = get_stackset_ready_accounts(credentials, org_account_ids, quiet = False)

    # Validate the stack set region
    regions = build_region_list('cloudformation', args.regions, args.partition_name)
    if args.master_region not in regions:
        printError('Error, the stack set region \'%s\' is not valid. Acceptable values are:' % args.master_region)
        printError(', '.join(regions))
        return 42

    # Connect
    printInfo('')
    api_client = connect_service('cloudformation', credentials, args.master_region, silent = True)

    # Establish the list of existing stacks and stack sets
    deployed_resources = {'stacks': {}, 'stack_sets': {}}
    printInfo('Fetching existing stacks and stack sets in %s in %s...' % (args.master_region, master_account_id))
    for stack in handle_truncated_response(api_client.list_stacks, {}, ['StackSummaries'])['StackSummaries']:
        if stack['StackStatus'] not in ['CREATE_FAILED', 'DELETE_COMPLETE']:
            deployed_resources['stacks'][stack['StackName']] = stack
    for stack_set in handle_truncated_response(api_client.list_stack_sets, {'Status': 'ACTIVE'}, ['Summaries'])['Summaries']:
        stack_set = api_client.describe_stack_set(StackSetName = stack_set['StackSetName'])['StackSet']
        deployed_resources['stack_sets'][stack_set['StackSetName']] = stack_set
    printInfo(' - Found %d stacks.' % len(deployed_resources['stacks']))
    for stack_name in deployed_resources['stacks']:
        printInfo('   - %s' %stack_name)
    printInfo(' - Found %d stacks sets.' % len(deployed_resources['stack_sets']))
    for stack_set_name in deployed_resources['stack_sets']:
        printInfo('   - %s' % stack_set_name)

    # Create the list of stacks to deploy
    templates = get_cloudformation_templates(args.stack_prefix)	

    # Master stacks
    for stack_name in sorted(templates['master_stacks'].keys()):
        if stack_name not in deployed_resources['stacks']:
            create_stack(api_client, stack_name, templates['master_stacks'][stack_name]['file_path'], wait_for_completion = templates['master_stacks'][stack_name]['wait_for_completion'])
        elif resource_older_than_template('stack', deployed_resources['stacks'][stack_name], templates['master_stacks'][stack_name]['file_path']):
            update_stack(api_client, stack_name, templates['master_stacks'][stack_name]['file_path'], wait_for_completion = templates['master_stacks'][stack_name]['wait_for_completion'])

    if len(configured_org_account_ids) == 0:
        printInfo('\nNo account IDs that support stack sets were found, skipping stack set configuration.')
        return

    return

    # Stack sets
    for stack_set_name in sorted(templates['master_stack_sets'].keys()):
        if stack_set_name not in deployed_resources['stack_sets']:
            create_stack_set(api_client, stack_set_name, templates['master_stack_sets'][stack_set_name]['file_path'], wait_for_completion = True)
        elif resource_older_than_template('stack_set', deployed_resources['stack_sets'][stack_set_name], templates['master_stack_sets'][stack_set_name]['file_path']):
            update_stack_set(api_client, stack_set_name, templates['master_stack_sets'][stack_set_name]['file_path'], wait_for_completion = True)

        # Then create instances without waiting for completion...
        # TODO make it a create_or_update ....
        #create_stack_instances(api_client, stack_set_name, configured_org_account_ids, regions)
        # TODO : -Wait on a stack set means wait for the stack instances...
    
    
