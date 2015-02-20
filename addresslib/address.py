# coding:utf-8

"""
Public interface for addresslib (email or url) parsing and validation
capabilities.

Public Functions in addresslib.address module:

    * parse(address, addr_spec_only=False)

      Parse a single address.

    * validate_address(addr_spec)

      Validates (parse, plus dns, mx check, and custom grammar) a single
      address spec. In the case of a valid address returns an EmailAddress
      object, otherwise returns None.

When valid addresses are returned, they are returned as an instance of
EmailAddress in addresslib.address.

See the parser.py module for implementation details of the parser.
"""

import time
import addresslib.parser
from addresslib.quote import smart_unquote, smart_quote
import addresslib.validate

from addresslib.parser import MAX_ADDRESS_LENGTH
from addresslib.utils import is_pure_ascii
from addresslib.utils import metrics_wrapper
from urllib.parse import urlparse

@metrics_wrapper()
def parse(address, addr_spec_only=False, metrics=False):
    """
    Given a string, returns a scalar object representing an email address

    Returns an Address object and optionally metrics on processing
    time if requested.

    Examples:
        >>> print address.parse('john@smith.com', addr_spec_only=True)
        'john@smith.com'

        >>> print address.parse('foo')
        None
    """
    mtimes = {'parsing': 0}

    parser = addresslib.parser._AddressParser(False)

    try:
        # addr-spec only
        if addr_spec_only:
            bstart = time.time()
            retval = parser.address_spec(address)
            mtimes['parsing'] = time.time() - bstart
            return retval, mtimes

        # full address
        bstart = time.time()
        retval = parser.address(address)
        mtimes['parsing'] = time.time() - bstart
        return retval, mtimes

    # supress any exceptions and return None
    except addresslib.parser.ParserException:
        return None, mtimes


@metrics_wrapper()
def validate_address(addr_spec, metrics=False):
    """
    Given an addr-spec, runs the pre-parser, the parser, DNS MX checks,
    MX existence checks, and if available, ESP specific grammar for the
    local part.

    In the case of a valid address returns an EmailAddress object, otherwise
    returns None. If requested, will also return the parsing time metrics.

    Examples:
        >>> address.validate_address('john@non-existent-domain.com')
        None

        >>> address.validate_address('user@gmail.com')
        None

        >>> address.validate_address('user.1234@gmail.com')
        user.1234@gmail.com
    """
    mtimes = {'parsing': 0, 'mx_lookup': 0,
        'dns_lookup': 0, 'mx_conn':0 , 'custom_grammar':0}

    # sanity check
    if addr_spec is None:
        return None, mtimes
    if not is_pure_ascii(addr_spec):
        return None, mtimes

    # preparse address into its parts and perform any ESP specific pre-parsing
    addr_parts = addresslib.validate.preparse_address(addr_spec)
    if addr_parts is None:
        return None, mtimes

    # run parser against address
    bstart = time.time()
    paddr = parse('@'.join(addr_parts), addr_spec_only=True)
    mtimes['parsing'] = time.time() - bstart
    if paddr is None:
        return None, mtimes

    # lookup if this domain has a mail exchanger
    exchanger, mx_metrics = \
        addresslib.validate.mail_exchanger_lookup(addr_parts[-1], metrics=True)
    mtimes['mx_lookup'] = mx_metrics['mx_lookup']
    mtimes['dns_lookup'] = mx_metrics['dns_lookup']
    mtimes['mx_conn'] = mx_metrics['mx_conn']
    if exchanger is None:
        return None, mtimes

    # lookup custom local-part grammar if it exists
    bstart = time.time()
    plugin = addresslib.validate.plugin_for_esp(exchanger)
    mtimes['custom_grammar'] = time.time() - bstart
    if plugin and plugin.validate(addr_parts[0]) is False:
        return None, mtimes

    return paddr, mtimes

def is_email(string):
    if parse(string, True):
        return True
    return False

class EmailAddress(object):
    """
    Represents a fully parsed email address with built-in support for MIME
    encoding. Note, do not use EmailAddress class directly, use the parse()
    function to return a scalar or iterable list respectively.

    Examples:
       >>> addr = EmailAddress("bob@host.com")
       >>> addr.address
       'bob@host.com'
       >>> addr.hostname
       'host.com'
       >>> addr.mailbox
       'bob'

    Display name is always returned in Unicode, i.e. ready to be displayed on
    web forms:

       >>> addr.display_name
       u'Bob Silva'

    And full email spec is 100% ASCII, encoded for MIME:
       >>> addr.full_spec()
       'Bob Silva <bob@host.com>'
    """

    __slots__ = ['mailbox', 'hostname', 'address']

    def __init__(self, spec):

        assert(spec)

        parts = spec.rsplit('@', 1)
        self.mailbox = parts[0]
        self.hostname = parts[1].lower()
        self.address = self.mailbox + "@" + self.hostname

    def __str__(self):
        """
        >>> str(EmailAddress("boo@host.com"))
        'boo@host.com'
        """
        return self.address

    def __eq__(self, other):
        """
        Allows comparison of two addresses.
        """
        if other:
            if isinstance(other, str):
                other = parse(other)
                if not other:
                    return False
            return self.address.lower() == other.address.lower()
        return False

    def __hash__(self):
        """
        Hashing allows using Address objects as keys in collections and compare
        them in sets

            >>> a = Address.from_string("a@host")
            >>> b = Address.from_string("A@host")
            >>> hash(a) == hash(b)
            True
            >>> s = set()
            >>> s.add(a)
            >>> s.add(b)
            >>> len(s)
            1
        """
        return hash(self.address.lower())
