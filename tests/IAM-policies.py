import json
import os
import shutil

#
# Validate the contents of the IAM policies folder
#
class TestIAMPoliciesClass:

    #
    # Set up
    #
    def setUp(self):
        self.iam_policy_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../IAM-Policies'))
        self.description_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../IAM-Policies/descriptions'))

    #
    # Every file in the IAM policy directory must have a json extension
    #
    def test_policy_file_extension(self):
        files = [f for f in os.listdir(self.iam_policy_dir) if os.path.isfile(os.path.join(self.iam_policy_dir, f))]
        has_json_extension = True
        for filename in files:
            if not filename.endswith('.json'):
                has_json_extension = False
                print 'Files under the IAM-policies directory must have a .json extension; %s does not.' %filename
        assert has_json_extension
    
    #
    # Every IAM policy must be a valid JSON payload
    #
    def test_policy_is_valid_json(self):
        files = [f for f in os.listdir(self.iam_policy_dir) if os.path.isfile(os.path.join(self.iam_policy_dir, f))]
        json_load_success = True
        for filename in files:
            try:
                with open(os.path.join(self.iam_policy_dir, filename), 'rt') as f:
                    policy = json.load(f)
            except:
                print '%s is not a valid JSON file' % filename
                json_load_success = False
                pass
        assert json_load_success
    
    #
    # Every IAM policy must have a corresponding description text file
    #
    def test_policy_description_exists(self):
        files = [f for f in os.listdir(self.iam_policy_dir) if os.path.isfile(os.path.join(self.iam_policy_dir, f))]
        all_policies_have_a_description = True
        for filename in files:
            basename = os.path.splitext(filename)[0]
            description_filename = os.path.join(self.description_dir, '%s.txt' % basename)
            if not os.path.isfile(description_filename):
                print 'IAM policy %s does not have a corresponding description file.' % basename
                all_policies_have_a_description = False
        assert all_policies_have_a_description
    
    #
    # Every description must have a corresponding IAM policy
    #
    def test_description_policy_exists(self):
        files = [f for f in os.listdir(self.description_dir) if os.path.isfile(os.path.join(self.description_dir, f))]
        all_descriptions_have_a_policy = True
        for filename in files:
            basename = os.path.splitext(filename)[0]
            policy_filename = os.path.join(self.iam_policy_dir, '%s.json' % basename)
            if not os.path.isfile(policy_filename):
                print 'Description file %s does not have a corresponding IAM policy.' % basename
                all_descriptions_have_a_policy = False
        assert all_descriptions_have_a_policy

