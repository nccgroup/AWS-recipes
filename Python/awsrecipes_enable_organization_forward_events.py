#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time

from opinel.utils.aws import build_region_list, connect_service, get_aws_account_id, handle_truncated_response
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printInfo, printException, printDebug, printError
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements

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
    parser.parser.add_argument('--stack-set-region',
                               dest='stack_set_region',
                               default=None,
                               required=True,
                               help='Region where the stack set will be created.')
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

    # Validate the stack set region
    regions = build_region_list('events', args.regions, args.partition_name)
    if args.stack_set_region not in regions:
        printError('Error, the stack set region \'%s\' is not valid. Acceptable values are:' % args.stack_set_region)
        printError(', '.join(regions))
        return 42

    # Determine the master account id to exclude it from the list of accounts to be configured for event forwarding
    monitoring_account_id = get_aws_account_id(credentials)

    # Connect to the AWS Organizations API
    api_client = connect_service('organizations', credentials)

    # List all accounts in the organization
    org_account_ids = []
    org_accounts = handle_truncated_response(api_client.list_accounts, {}, ['Accounts'])['Accounts']
    org_account_ids = [ account['Id'] for account in org_accounts if account['Status'] == 'ACTIVE' and account['Id'] != monitoring_account_id ]
    printInfo('Found %d accounts in the organization.' % len(org_account_ids))
    printDebug(str(org_account_ids))

    # Verify that the account has been configured for stack sets by attempting to assume the stack set execution role
    api_client = connect_service('sts', credentials, silent = True)
    configured_org_account_ids = []
    for account_id in org_account_ids:
        try:
            role_arn = 'arn:aws:iam::%s:role/AWSCloudFormationStackSetExecutionRole' % account_id
            api_client.assume_role(RoleArn = role_arn, RoleSessionName = 'foobar')
            configured_org_account_ids.append(account_id)
        except Exception as e:
            pass
    if len(configured_org_account_ids) != len(org_account_ids):
        printInfo('Only %d of these accounts have the necessary stack set execution role:' % len(configured_org_account_ids))
        printInfo(str(configured_org_account_ids))

    # For each region with cloudwatch events, put a permission for each account
    printInfo('Adding permissions on the default event buses...')
    for region in regions:
        api_client = connect_service('events', credentials, region)
        for account in org_accounts:
            account_id = account['Id']
            if account_id not in configured_org_account_ids:
                continue
            account_name = account['Name']
            api_client.put_permission(Action = 'events:PutEvents', Principal = account_id, StatementId = 'AWSRecipesAllow%s' % account_id)

    # Create the stack set
    try:
        stack_set_region = 'us-east-1'
        stack_set_name = 'ConfigureCloudWatchEventsForwarding'
        api_client = connect_service('cloudformation', credentials, args.stack_set_region)
        # TBD:  need for the region where the stack set is created and the regions where the stack instances are created...
        template_path = os.path.join((os.path.dirname(os.path.realpath(__file__))), '../CloudFormationTemplates/ConfigureCloudWatchEventsForwarding.yml')
        with open(template_path, 'rt') as f:
            template_body = f.read()
        template_parameters = [ {'ParameterKey': 'EventsMonitoringAccountID', 'ParameterValue': get_aws_account_id(credentials) } ]
        printInfo('Creating the stack set...')
        response = api_client.create_stack_set(StackSetName = stack_set_name, TemplateBody = template_body, Parameters = template_parameters)
    except Exception as e:
        if e.response['Error']['Code'] != 'NameAlreadyExistsException':
            printException(e)
            printError('Failed to create the stack set.')
            return 42

    # Create the stack instances: one per region in every account
    operation_preferences = {
        'FailureTolerancePercentage': 100,
        'MaxConcurrentPercentage': 100
    }
    response = api_client.create_stack_instances(StackSetName = stack_set_name, Accounts = configured_org_account_ids, Regions = regions, OperationPreferences = operation_preferences)
    printInfo('Successfully started operation Id %s' % response['OperationId'])


if __name__ == '__main__':
    sys.exit(main())
