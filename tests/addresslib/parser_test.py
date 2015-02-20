# coding:utf-8

import email.header

from addresslib.address import is_email
from mock import patch, Mock
from nose.tools import assert_equal, assert_not_equal
from nose.tools import assert_true, assert_false


def test_is_email():
    assert_true(is_email("ev@host"))
    assert_true(is_email("ev@host.com.com.com"))

    assert_false(is_email("evm"))
    assert_false(is_email(None))
