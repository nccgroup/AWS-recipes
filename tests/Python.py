import json
import os
import shutil
from subprocess import Popen, PIPE

#
# Python AWS recipes test class
#
class TestPythonRecipesClass:

    #
    # Set up
    #
    def setUp(self):
        self.recipes_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../Python'))
        self.recipes = [f for f in os.listdir(self.recipes_dir) if os.path.isfile(os.path.join(self.recipes_dir, f)) and f.endswith('.py')]

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

    
