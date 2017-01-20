# Import opinel
from opinel.utils import *

# Import stock packages
import os
from subprocess import Popen, PIPE

#
# AWS recipes test class (Python only)
#
class TestPythonRecipesClass:

    #
    # Implement cmp() for tests in Python3
    #
    def cmp(self, a, b):
        return (a > b) - (a < b)

    #
    # Set up
    #
    def setUp(self):
        self.recipes_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../Python'))
        self.recipes = [f for f in os.listdir(self.recipes_dir) if os.path.isfile(os.path.join(self.recipes_dir, f)) and f.endswith('.py')]
        self.data_dir = 'tests/data'
        self.result_dir = 'tests/results'

    #
    # Every Python recipe must run fine with --help
    #
    def test_all_recipes_help(self):
        successful_help_runs = True
        for recipe in self.recipes:
            recipe_path = os.path.join(self.recipes_dir, recipe)
            process = Popen(['python', recipe_path, '--help'], stdout=PIPE)
            (output, err) = process.communicate()
            exit_code = process.wait()
            if exit_code != 0:
                print('The recipe %s does not run properly.' % recipe)
                successful_help_runs = False
        assert successful_help_runs

    #
    # Every python recipe must have a test method
    #
    def all_recipes_test_function_must_exist(self):
        for recipe in self.recipes:
            methods = dir(self)
            method_name = 'test_%s' % recipe.replace('.py', '')
            if method_name not in methods:
                printError('%s does not exist.' % method_name)
            assert method_name in methods

    #
    # Test aws_cloudtrail_enable_all_regions
    #
    def test_aws_cloudtrail_enable_all_regions(self):
        print('a')

    #
    # Test aws_cloudtrail_get_logs
    #
    def test_aws_cloudtrail_get_logs(self):
        print('a')

    #
    #
    #
    def test_aws_ec2_empty_default_security_groups(self):
        print('a')
        # Add rule in default
        # Check that rule exists in non-default
        # Checkthat rule exists in default
        # run tool
        # check that rule stil exssis in non default
        # check that rule is gone in default

    #
    #
    #
    def test_aws_iam_create_assume_role_group(self):
        print('a')

    #
    #
    #
    def test_aws_iam_create_default_groups(self):
        print('a')

    #
    #
    #
    def test_aws_iam_create_policy(self):
        print('a')

    #
    #
    #
    def test_aws_iam_create_user(self):
        print('a')

    #
    #
    #
    def test_aws_iam_delete_user(self):
        print('a')

    #
    #
    #
    def test_aws_iam_enable_mfa(self):
        print('a')

    #
    #
    #
    def test_aws_iam_rotate_my_key(self):
        print('a')

    #
    #
    #
    def test_aws_iam_sort_users(self):
        print('a')

    #
    #
    #
    def test_aws_recipes_assume_role(self):
        print('a')

    #
    #
    #
    def test_aws_recipes_configure_iam(self):
        print('a')

    #
    # Test aws_recipes_create_ip_ranges.py
    #
    def test_aws_recipes_create_ip_ranges(self):
        successful_aws_recipes_create_ip_ranges_runs = True
        recipe = os.path.join(self.recipes_dir, 'aws_recipes_create_ip_ranges.py')
        test_cases = [
            # Matching header names, use all data
            ['--csv-ip-ranges tests/data/ip-ranges-1.csv --force', 'ip-ranges-1a.json'],
            # Matching header names, use partial data
            ['--csv-ip-ranges tests/data/ip-ranges-1.csv --force --attributes ip_prefix field_b --skip-first-line', 'ip-ranges-1b.json'],
            # Matching header names, use partial data with mappings (must skip first line)
            ['--csv-ip-ranges tests/data/ip-ranges-1.csv --force --attributes ip_prefix field_b --mappings 0 2 --skip-first-line', 'ip-ranges-1c.json'],
            # Matching header names but swap with mappings (must skip first line)
            ['--csv-ip-ranges tests/data/ip-ranges-1.csv --force --attributes ip_prefix field_a --mappings 0 2 --skip-first-line', 'ip-ranges-1d.json'],
            # No headers, use all data
            ['--csv-ip-ranges tests/data/ip-ranges-2.csv --force --attributes ip_prefix field_a, field_b --mappings 0 1 2', 'ip-ranges-2a.json'],
            # No headers, use partial data
            ['--csv-ip-ranges tests/data/ip-ranges-2.csv --force --attributes ip_prefix field_b --mappings 0 2', 'ip-ranges-2b.json'],
            # Different header names (must skip first line)
            ['--csv-ip-ranges tests/data/ip-ranges-3.csv --force --attributes ip_prefix new_field_b --mappings 0 2 --skip-first-line', 'ip-ranges-3a.json'],
            # Different header names with ip_prefix not in first column (must skip first line)
            ['--csv-ip-ranges tests/data/ip-ranges-4.csv --force --attributes ip_prefix new_field_a new_field_b --mappings 1 0 2 --skip-first-line', 'ip-ranges-4a.json'],
        ]
        for test_case in test_cases:
            args, result_file = test_case
            cmd =  ['python' , recipe] + args.split(' ')
            process = Popen(cmd, stdout=PIPE)
            exit_code = process.wait()
            if exit_code != 0:
                print('The recipe %s failed to run with arguments %s.' % (recipe, args))
                successful_aws_recipes_create_ip_ranges_runs = False
                continue
            test_results = read_ip_ranges('ip-ranges-default.json')
            known_results = read_ip_ranges(os.path.join(self.result_dir, result_file))
            if self.cmp(test_results, known_results) != 0:
                print('Failed when comparing:\n%s\n%s\n' % (test_results, known_results))
                successful_aws_recipes_create_ip_ranges_runs = False
            os.remove('ip-ranges-default.json')
        assert(successful_aws_recipes_create_ip_ranges_runs)

    #
    #
    #
    def test_aws_recipes_get_permissions(self):
        print('a')

    #
    #
    #
    def test_aws_recipes_init_sts_session(self):
        print('a')

