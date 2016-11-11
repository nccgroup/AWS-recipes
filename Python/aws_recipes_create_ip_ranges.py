#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_ec2 import *

# Import stock packages
import datetime
import sys


########################################
##### Helpers
########################################

def new_ip_info(region, instance_id, is_elastic):
    ip_info = {}
    ip_info['region'] = region
    ip_info['instance_id'] = instance_id
    ip_info['is_elastic'] = is_elastic
    return ip_info

def new_prefix(ip_prefix, obj):
    obj['ip_prefix'] = ip_prefix
    return obj




########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_opinel_version('1.0.4'):
        return 42

    # Get the environment name
    profile_names = get_environment_name(args)

    # Initialize the list of regions to work with
    regions = build_region_list('ec2', args.regions, args.with_gov, args.with_cn)

    # For each profile/environment...
    for profile_name in profile_names:

        # Interactive mode
        if args.interactive:

            # Initalize prefixes
            attributes = args.attributes
            filename = 'ip-ranges-%s.json' % profile_name
            if os.path.isfile(filename):
                printInfo('Loading existing IP ranges from %s' % filename)
                prefixes = read_ip_ranges(filename)
                # Initialize attributes from existing values
                if attributes == []:
                    for prefix in prefixes:
                        for key in prefix:
                            if key not in attributes:
                                attributes.append(key)
            else:
                prefixes = []

            # IP prefix does not need to be specified as an attribute
            attributes = [a for a in attributes if a != 'ip_prefix']

            # Prompt for new entries
            while prompt_4_yes_no('Add a new IP prefix to the ip ranges'):
                ip_prefix = prompt_4_value('Enter the new IP prefix:')
                obj = {}
                for a in attributes:
                    obj[a] = prompt_4_value('Enter the \'%s\' value:' % a)
                prefixes.append(new_prefix(ip_prefix, obj))

        # Support loading from CSV file
        elif len(args.csv_ip_ranges) > 0:

            # Initalize prefixes
            prefixes = []

            # Load CSV file contents
            for filename in args.csv_ip_ranges:
                with open(filename, 'rt') as f:
                    csv_contents = f.readlines()

                # Initialize mappings
                attributes = args.attributes
                mappings = {}
                if attributes == []:
                    # Follow structure of first line
                    headers = csv_contents.pop(0).strip().split(',')
                    for index, attribute in enumerate(headers):
                        mappings[attribute] = index
                elif attributes and args.mappings == []:
                    # Follow structure of first line but only map a subset of fields
                    headers = csv_contents.pop(0).strip().split(',')
                    attributes.append('ip_prefix')
                    for attribute in set(attributes):
                        mappings[attribute] = headers.index(attribute)
                else:
                    # Indices of columns are provided as an argument
                    for index, attribute in enumerate(attributes):
                        mappings[attribute] = int(args.mappings[index])
                    if args.skip_first_line:
                        csv_contents.pop(0)

                # For each line...
                for line in csv_contents:
                    ip_prefix = {}
                    values = line.strip().split(',')
                    if len(values) < len(mappings):
                        continue
                    for attribute in mappings:
                        ip_prefix[attribute] = values[mappings[attribute]]
                    if 'ip_prefix' in mappings and 'mask' in mappings:
                        ip = ip_prefix.pop('ip_prefix')
                        mask = ip_prefix.pop('mask')
                        ip_prefix['ip_prefix'] = '%s/%s' % (ip, mask.replace('/',''))
                    prefixes.append(ip_prefix)

        # AWS mode
        else:

            # Initialize IP addresses
            printInfo('Fetching public IP information for the \'%s\' environment...' % profile_name)
            ip_addresses = {}

            # Search for AWS credentials
            credentials = read_creds(profile_name)
            if not credentials['AccessKeyId']:
                return 42

            # For each region...
            for region in regions:

                # Connect to EC2
                ec2_client = connect_ec2(credentials, region)
                if not ec2_client:
                    continue

                # Get public IP addresses associated with EC2 instances
                printInfo('...in %s: EC2 instances' % region)
                reservations = handle_truncated_response(ec2_client.describe_instances, {}, 'NextToken', ['Reservations'])
                for reservation in reservations['Reservations']:
                    for i in reservation['Instances']:
                        if 'PublicIpAddress' in i:
                            ip_addresses[i['PublicIpAddress']] = new_ip_info(region, i['InstanceId'], False)
                            get_name(ip_addresses[i['PublicIpAddress']], i, 'InstanceId')
                        if 'NetworkInterfaces' in i:
                            for eni in i['NetworkInterfaces']:
                                if 'Association' in eni:
                                    ip_addresses[eni['Association']['PublicIp']] = new_ip_info(region, i['InstanceId'], False) # At that point, we don't know whether it's an EIP or not...
                                    get_name(ip_addresses[eni['Association']['PublicIp']], i, 'InstanceId')

                # Get all EIPs (to handle unassigned cases)
                printInfo('...in %s: Elastic IP addresses' % region)
                eips = handle_truncated_response(ec2_client.describe_addresses, {}, 'NextToken', ['Addresses'])
                for eip in eips['Addresses']:
                    instance_id = eip['InstanceId'] if 'InstanceId' in eip else None
                    # EC2-Classic non associated EIPs have an empty string for instance ID (instead of lacking the attribute in VPC)
                    if instance_id == '':
                        instance_id = None
                    ip_addresses[eip['PublicIp']] = new_ip_info(region, instance_id, True)
                    ip_addresses[eip['PublicIp']]['name'] = instance_id

                # Format
                prefixes = []
                for ip in ip_addresses:
                    prefixes.append(new_prefix(ip, ip_addresses[ip]))

        # Generate an ip-ranges-<profile>.json file
        save_ip_ranges(profile_name, prefixes, args.force_write, args.debug)


########################################
##### Parse arguments and call main()
########################################

default_args = read_profile_default_args(parser.prog)

add_common_argument(parser, default_args, 'regions')
add_common_argument(parser, default_args, 'with-gov')
add_common_argument(parser, default_args, 'with-cn')
add_common_argument(parser, default_args, 'force')
add_common_argument(parser, default_args, 'dry-run')

parser.add_argument('--interactive',
                    dest='interactive',
                    default=False,
                    action='store_true',
                    help='Interactive prompt to manually enter CIDRs.')
parser.add_argument('--csv-ip-ranges',
                    dest='csv_ip_ranges',
                    default=[],
                    nargs='+',
                    help='CSV file(s) containing CIDRs information.')
parser.add_argument('--skip-first-line',
                    dest='skip_first_line',
                    default=False,
                    action='store_true',
                    help='Skip first line when parsing CSV file.')
parser.add_argument('--attributes',
                    dest='attributes',
                    default=[],
                    nargs='+',
                    help='Name of the attributes to enter for each CIDR.')
parser.add_argument('--mappings',
                    dest='mappings',
                    default=[],
                    nargs='+',
                    help='Column number matching attributes when headers differ.')

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
