#!/usr/bin/env python2

# Import AWS utils
from AWSUtils.utils import *
from AWSUtils.utils_iam import *

# Import third-party modules
import os
import boto3


########################################
##### Globals
########################################

re_aws_account_id = re.compile('AWS_ACCOUNT_ID', re.DOTALL|re.MULTILINE)


########################################
##### Helpers
########################################

#
# Get AWS account ID of authenticated user
#
def get_aws_account_id(iam_connection):
    result = iam_connection.get_all_users(max_items = 1)
    user_arn = result['list_users_response']['list_users_result']['users'][0]['arn']
    return user_arn.split(':')[4]


########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Arguments
    profile_name = args.profile[0]
    target_type = args.type[0]
    if not args.is_managed and target_type == None:
        print 'Error: you must either create a managed policy or specify the type of IAM entity the policy will be attached to.'
        return 42
    if not args.is_managed and target_type == None and len(args.targets) < 1:
        print 'Error: you must provide the name of at least one IAM %s you will attach this inline policy to.' % target_type
        return 42

    # Read credentials
    key_id, secret, token = read_creds(args.profile[0])
    if not key_id:
        print 'Error: could not find AWS credentials.'
        return 42

    # Connect to IAM
    iam_connection = connect_iam(key_id, secret, token)
    if not iam_connection:
        return 42

    # Use boto3 to work with policies...
    if args.is_managed:
        boto3_session = boto3.session.Session(aws_access_key_id = key_id, aws_secret_access_key = secret, aws_session_token = token)

    # Get AWS account ID
    aws_account_id = get_aws_account_id(iam_connection)

    # Create the policies
    for template in args.templates:
        if not os.path.isfile(template):
            print 'Error: file \'%s\' does not exist.' % template
            continue
        with open(template, 'rt') as f:
            policy = f.read()  # json.load(f)
        policy = re_aws_account_id.sub(aws_account_id, policy)
        policy_name = os.path.basename(template).split('.')[0]
        if not args.is_managed:
            callback = getattr(iam_connection, 'put_' + target_type + '_policy')
            for target in args.targets:
                try:
                    print 'Creating policy \'%s\' for the \'%s\' IAM %s...' % (policy_name, target, target_type)
                    if not args.dry_run:
                        callback(target, policy_name, policy)
                except Exception, e:
                    printException(e)
                    pass
        else:
            iam_connection3 = boto3_session.resource('iam')
            params = {}
            params['PolicyDocument'] = policy
            params['PolicyName'] = policy_name
            description = ''
            # Search for a description file
            descriptions_dir = os.path.join(os.path.dirname(template), 'descriptions')
            if os.path.exists(descriptions_dir):
                description_file = os.path.join(descriptions_dir, os.path.basename(template).replace('.json', '.txt'))
                if os.path.isfile(description_file):
                    with open(description_file, 'rt') as f:
                        params['Description'] = f.read()
            elif prompt_4_yes_no('Do you want to add a description to the \'%s\' policy' % policy_name):
                params['Description'] = prompt_4_value('Enter the policy description:')
            if not args.dry_run:
                print 'Creating policy \'%s\'...' % (policy_name)
                new_policy = iam_connection3.meta.client.create_policy(**params)
                if len(args.targets):
                    callback = getattr(iam_connection3.meta.client, 'attach_' + target_type + '_policy')
                    for target in args.targets:
                        print 'Attaching policy to the \'%s\' IAM %s...' % (target, target_type)
                        params = {}
                        params['PolicyArn'] = new_policy['Policy']['Arn']
                        params[target_type.title() + 'Name'] = target
                        callback(**params)

        if args.save_locally:
            with open('%s-%s.json' % (policy_name, profile_name), 'wt') as f:
                f.write(policy)
                f.close()


########################################
##### Parse arguments and call main()
########################################

parser.add_argument('--managed',
                    dest='is_managed',
                    default=False,
                    action='store_true',
                    help='Create a managed policy.')
parser.add_argument('--type',
                    dest='type',
                    default=[ None ],
                    nargs='+',
                    choices=['group', 'managed', 'role', 'user'],
                    help='Type of target that the policy will apply or be attached to.')
parser.add_argument('--targets',
                    dest='targets',
                    default=[],
                    nargs='+',
                    help='Name of the IAM entity the policy will be added to (required for inline policies).')
parser.add_argument('--templates',
                    dest='templates',
                    default=[],
                    nargs='+',
                    required=True,
                    help='Path to the template IAM policies that will be created.')
parser.add_argument('--dry',
                    dest='dry_run',
                    default=False,
                    action='store_true',
                    help='Perform only read access.')
parser.add_argument('--save',
                    dest='save_locally',
                    default=False,
                    action='store_true',
                    help='Generates the policies and store them locally.')

args = parser.parse_args()

if __name__ == '__main__':
    main(args)
