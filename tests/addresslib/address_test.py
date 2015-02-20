# coding:utf-8

from .. import *
from nose.tools import assert_equal, assert_not_equal

from addresslib.address import parse
from addresslib.address import EmailAddress

def test_address_compare():
    a = EmailAddress("a@host.com")
    b = EmailAddress("b@host.com")
    also_a = EmailAddress("A@host.com")

    ok_(a == also_a)
    #eq_(False, a != "I am also A <a@HOST.com>")
    ok_(a != 'crap')
    ok_(a != None)
    ok_(a != b)

    # make sure it works for sets:
    s = set()
    s.add(a)
    s.add(also_a)
    eq_(1, len(s))
