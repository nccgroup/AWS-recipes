#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from opinel.utils.aws import build_region_list, connect_service
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError, printException, prompt_4_yes_no
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements

from opinel.services.cloudformation import create_or_update_stack, make_awsrecipes_stack_name


########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('regions', help = 'Regions where the stack(s) will be created.')
    parser.add_argument('partition-name')
    parser.parser.add_argument('--template',
                               dest='template',
                               default=None,
                               required=True,
                               help='Path to the CloudFormation template.')
    parser.parser.add_argument('--parameters',
                               dest='parameters',
                               default=None,
                               nargs='+',
                               help='Optional parameters for the stack.')
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
    if __name__ == '__main__':
        if not credentials['AccessKeyId']:
            return 42

    # Validate the regions
    regions = build_region_list('cloudformation', args.regions, args.partition_name)
    if len(args.regions) == 0 and not prompt_4_yes_no('You didn\'t specify a region for this stack, do you want to create it in all regions ?'):
        return 42

    for region in regions:
        try:
            # Create stack
            api_client = connect_service('cloudformation', credentials, region)
            params = {}
            params['api_client'] = api_client
            if not args.template.startswith('/'):
                params['template_path'] = os.path.join((os.path.dirname(os.path.realpath(__file__))), args.template)
            else:
                params['template_path'] = args.template
            if args.parameters:
                params['template_parameters'] = args.parameters
            params['stack_name'] = make_awsrecipes_stack_name(params['template_path'])
            create_or_update_stack(**params)
        except Exception as e:
            printException(e)


if __name__ == '__main__':
    sys.exit(main())
