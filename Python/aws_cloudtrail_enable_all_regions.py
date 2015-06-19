#!/usr/bin/env python

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_cloudtrail import *

# Import third-party packages
from boto import cloudtrail

import sys

########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Read credentials
    key_id, secret, token = read_creds(args.profile[0])

    # Check arguments
    if not args.bucket_name[0]:
        print 'Error: you need to provide the name of the S3 bucket to deliver log files to.'
        return 42

    # Initialize various lists of regions
    regions = build_region_list(cloudtrail.regions(), args.region_name)
    disabled_regions = []
    stopped_regions = []
    global_enabled_regions = []

    # By default, we want to enable global services
    include_global_service_events = True

    # Iterate through regions and enable CloudTrail and get some info
    print 'Fetching CloudTrail status for all regions...'
    for region in regions:
        cloudtrail_connection = connect_cloudtrail(key_id, secret, token, region)
        trails = get_trails(cloudtrail_connection)
        if len(trails):
            status = cloudtrail_connection.get_trail_status(trails[0]['Name'])
            if status['IsLogging']:
                print 'CloudTrail is enabled in %s' % region
            else:
                stopped_regions.append((region, trails[0]['Name']))
            for trail in trails:
                if trail['IncludeGlobalServiceEvents'] == True:
                    include_global_service_events = False
                    global_enabled_regions.append((region, trails[0]['Name']))
        else:
            disabled_regions.append(region)

    # Enable CloudTrail
    if not args.dry_run:
        for region in disabled_regions:
            cloudtrail_connection = connect_cloudtrail(key_id, secret, token, region)
            # Enable CloudTrails if user says so
            if args.force or prompt_4_yes_no('CloudTrail is disabled in %s. Do you want to enabled it' % region):
                print 'Enabling CloudTrail in region %s...' % region
                name = 'Default'
                cloudtrail_connection.create_trail(name, args.bucket_name[0], args.s3_key_prefix[0], args.sns_topic_name[0], include_global_service_events)
                cloudtrail_connection.start_logging(name)
        for region, name in stopped_regions:
            cloudtrail_connection = connect_cloudtrail(key_id, secret, token, region) 
            if args.force or prompt_4_yes_no('CloudTrail is stopped in %s. Do you want to start it' % region):
                cloudtrail_connection.start_logging(name)

    # Fix global services logging enabled in multiple regions
    if not args.dry_run and len(global_enabled_regions) > 1:
        if prompt_4_yes_no('Warning, global services are included in more than one region. Do you want to fix this'):
            regions = []
            for region, name in global_enabled_regions:
                regions.append(region)            
            chosen_region = prompt_4_value('Which region ID do you want to enable global services logging in', regions, None, True, True, is_question = True)
            for region, name in global_enabled_regions:
                if region != chosen_region:
                    cloudtrail_connection = connect_cloudtrail(key_id, secret, token, region)
                    cloudtrail_connection.update_trail(name, include_global_service_events=False)


########################################
##### Additional arguments
########################################

parser.add_argument('--region',
                    dest='region_name',
                    default=[ ],
                    nargs='+',
                    help='Name of regions to enable CloudTrail in, defaults to all.')

parser.add_argument('--bucket',
                    dest='bucket_name',
                    default=[ None ],
                    nargs='+',
                    help='Name of the destination S3 bucket.')

parser.add_argument('--prefix',
                    dest='s3_key_prefix',
                    default=[ None ],
                    nargs='+',
                    help='Prefix (path) for the log files.')

parser.add_argument('--sns_topic',
                    dest='sns_topic_name',
                    default=[ None ],
                    nargs='+',
                    help='Prefix (path) for the log files.')
parser.add_argument('--force',
                    dest='force',
                    default=False,
                    action='store_true',
                    help='Automatically enable CloudTrail if it is not.')
parser.add_argument('--dry',
                    dest='dry_run',
                    default=False,
                    action='store_true',
                    help='Run the status checks but do not take action.')

########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
