# coding:utf-8

from os.path import join, abspath, dirname, exists
from nose.tools import *
import codecs

def fixtures_path():
    return join(abspath(dirname(__file__)), "fixtures")

def fixture_file(name):
    return join(fixtures_path(), name)

def skip_if_asked():
    from nose import SkipTest
    import sys
    if "--no-skip" not in sys.argv:
        raise SkipTest()

# addresslib fixture files
MAILBOX_VALID_TESTS = open(fixture_file("mailbox_valid.txt")).read()
MAILBOX_INVALID_TESTS = open(fixture_file("mailbox_invalid.txt")).read()
ABRIDGED_LOCALPART_VALID_TESTS = open(fixture_file("abridged_localpart_valid.txt")).read()
ABRIDGED_LOCALPART_INVALID_TESTS = open(fixture_file("abridged_localpart_invalid.txt")).read()
URL_VALID_TESTS = codecs.open(fixture_file("url_valid.txt"), encoding='utf-8', mode='r').read()
URL_INVALID_TESTS = codecs.open(fixture_file("url_invalid.txt"), encoding='utf-8', mode='r').read()

DOMAIN_TYPO_VALID_TESTS = open(fixture_file("domain_typos_valid.txt")).read()
DOMAIN_TYPO_INVALID_TESTS = open(fixture_file("domain_typos_invalid.txt")).read()
