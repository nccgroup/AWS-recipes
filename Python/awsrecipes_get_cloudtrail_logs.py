#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import sys

from opinel.services.iam import get_aws_account_id
from opinel.services.s3 import get_s3_bucket_location
from opinel.utils.aws import connect_service, build_region_list, handle_truncated_response
from opinel.utils.cli_parser import OpinelArgumentParser
from opinel.utils.console import configPrintException, printError, printException, printInfo
from opinel.utils.credentials import read_creds
from opinel.utils.globals import check_requirements, manage_dictionary
from opinel.utils.threads import thread_work


# Import stock packages
import datetime
from datetime import date, timedelta
import gzip
import os
from threading import Thread
# Python2 vs Python3
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

########################################
##### Globals
########################################

cloudtrail_log_path = 'AWSLogs/AWS_ACCOUNT_ID/CloudTrail/REGION/'
download_folder = 'trails'





########################################
##### Helpers
########################################

def show_current_count():
    show_current_count.counter += 1
    printInfo(str(show_current_count.counter))
show_current_count.counter = 0


def download_object(q, params):
    bucket_name = params['Bucket']
    s3_client = params['S3Client']
    while True:
        key, tries = q.get()
        filename = os.path.join(download_folder, key.split('/')[-1])
        dst = re.sub(r'\.(\w*)?$', '', filename)
        if (not os.path.exists(filename) and not os.path.exists(dst)) or (os.path.exists(filename) and os.path.getsize(filename) == 0) or (os.path.exists(dst) and os.path.getsize(dst) == 0):
            try:
                s3_client.download_file(bucket_name, key, filename)
            except Exception as e:
                if tries < 2:
                    q.put([key, tries + 1])
                    printInfo('Error downloading %s; re-queued.' % filename)
                else:
                    printException(e)
                    printInfo('Error downloading %s; discarded.' % filename)
        q.task_done()
        #show_current_count()

def gunzip_file(q, params):
    while True:
        src = q.get()
        src = os.path.join(download_folder, src)
        try:
            dst = re.sub(r'\.(\w*)?$', '', src)
            if src.endswith('.gz'):
              with gzip.open(src, 'rb') as f1:
                file_contents = f1.read()
                with open(dst, 'wt') as f2:
                    f2.write(file_contents)
              os.remove(src)
        except Exception as e:
            printException(e)
            pass
        finally:
            q.task_done()



########################################
##### Main
########################################

def main():

    # Parse arguments
    parser = OpinelArgumentParser()
    parser.add_argument('debug')
    parser.add_argument('profile')
    parser.add_argument('regions')
    parser.add_argument('partition-name')
    parser.add_argument('bucket-name')
    parser.parser.add_argument('--aws-account-id',
                                dest='aws_account_id',
                                default=[ None ],
                                nargs='+',
                                help='Bleh.')
    parser.parser.add_argument('--from',
                                dest='from_date',
                                default=[ None ],
                                nargs='+',
                                help='Bleh.')
    parser.parser.add_argument('--to',
                                dest='to_date',
                                default=[ None ],
                                nargs='+',
                                help='Bleh.')

    args = parser.parse_args()

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_requirements(os.path.realpath(__file__)):
        return 42



    # Arguments
    profile_name = args.profile[0]
    try:
        from_date = datetime.datetime.strptime(args.from_date[0], "%Y/%m/%d").date()
        to_date = datetime.datetime.strptime(args.to_date[0], "%Y/%m/%d").date()
        delta = to_date - from_date
    except Exception as e:
        printException(e)
        printError('Error: dates must be formatted of the following format YYYY/MM/DD')
        return 42
    if delta.days < 0:
        printError('Error: your \'to\' date is earlier than your \'from\' date')
        return 42

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Fetch AWS account ID
    if not args.aws_account_id[0]:
        printInfo('Fetching the AWS account ID...')
        aws_account_id = get_aws_account_id(connect_service('iam', credentials))
    else:
        aws_account_id = args.aws_account_id[0]
    global cloudtrail_log_path
    cloudtrail_log_path = cloudtrail_log_path.replace('AWS_ACCOUNT_ID', aws_account_id)

    # Create download dir
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Iterate through regions
    s3_clients = {}
    for region in build_region_list('cloudtrail', args.regions, args.partition_name):

        # Connect to CloudTrail
        cloudtrail_client = connect_service('cloudtrail', credentials, region)
        if not cloudtrail_client:
            continue

        # Get information about the S3 bucket that receives CloudTrail logs
        trails = cloudtrail_client.describe_trails()
        for trail in trails['trailList']:
            bucket_name = trail['S3BucketName']
            prefix = trail['S3KeyPrefix'] if 'S3KeyPrefix' in trail else ''

        # Connect to S3
        manage_dictionary(s3_clients, region, connect_service('s3', credentials, region))
        target_bucket_region = get_s3_bucket_location(s3_clients[region], bucket_name)
        manage_dictionary(s3_clients, target_bucket_region, connect_service('s3', credentials, target_bucket_region))
        s3_client = s3_clients[target_bucket_region]

        # Generate base path for files
        log_path = os.path.join(prefix, cloudtrail_log_path.replace('REGION', region))

        # Download files
        printInfo('Downloading log files in %s... ' % region, False)
        keys = []
        for i in range(delta.days + 1):
            day = from_date + timedelta(days=i)
            folder_path = os.path.join(log_path, day.strftime("%Y/%m/%d"))
            try:
                objects = handle_truncated_response(s3_client.list_objects, {'Bucket': bucket_name, 'Prefix': folder_path}, ['Contents'])
                for o in objects['Contents']:
                    keys.append([o['Key'], 0])
            except Exception as e:
                printException(e)
                pass
        thread_work(keys, download_object, params = {'Bucket': bucket_name, 'S3Client': s3_client}, num_threads = 100)
        printInfo('Done')

    # Iterate through files and gunzip 'em
    printInfo('Decompressing files...')
    gzlogs = []
    for root, dirnames, filenames in os.walk(download_folder):
        for filename in filenames:
            gzlogs.append(filename)
    thread_work(gzlogs, gunzip_file, num_threads = 30)


if __name__ == '__main__':
    main()
