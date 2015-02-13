#!/usr/bin/env python2

# Import third-party packages
import argparse
import traceback


########################################
##### Debug-related functions
########################################

def printException(e):
    global verbose_exceptions
    if verbose_exceptions:
        print traceback.format_exc()
    else:
        print e

def configPrintException(enable):
    global verbose_exceptions
    verbose_exceptions = enable


########################################
##### Argument parser
########################################

parser = argparse.ArgumentParser()

parser.add_argument('--debug',
                    dest='debug',
                    default=False,
                    action='store_true',
                    help='Print the stack trace when exception occurs')
