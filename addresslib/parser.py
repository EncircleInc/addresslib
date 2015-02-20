# coding:utf-8

"""
_AddressParser is an implementation of a recursive descent parser for email
addresses and urls. While _AddressParser can be used directly it is not
recommended, use the the parse() method which is provided in the address
module for convenience.

The grammar supported by the parser (as well as other limitations) are
outlined below. Plugins are also supported to allow for custom more
restrictive grammar that is typically seen at large Email Service Providers
(ESPs).

For email addresses, the grammar tries to stick to RFC 5322 as much as
possible, but includes relaxed (lax) grammar as well to support for common
realistic uses of email addresses on the Internet.

Grammar:


    address-list      ->    address { delimiter address }
    mailbox           ->    name-addr-rfc | name-addr-lax | addr-spec | url

    name-addr-rfc     ->    [ display-name-rfc ] angle-addr-rfc
    display-name-rfc  ->    [ whitespace ] word { whitespace word }
    angle-addr-rfc    ->    [ whitespace ] < addr-spec > [ whitespace ]

    name-addr-lax     ->    [ display-name-lax ] angle-addr-lax
    display-name-lax  ->    [ whitespace ] word { whitespace word } whitespace
    angle-addr-lax    ->    addr-spec [ whitespace ]

    addr-spec         ->    [ whitespace ] local-part @ domain [ whitespace ]
    local-part        ->    dot-atom | quoted-string
    domain            ->    dot-atom

    word              ->    word-ascii | word-unicode
    word-ascii        ->    atom | quoted-string
    word-unicode      ->    unicode-atom | unicode-qstring
    whitespace        ->    whitespace-ascii | whitespace-unicode


Additional limitations on email addresses:

    1. local-part:
        * Must not be greater than 64 octets

    2. domain:
        * No more than 127 levels
        * Each level no more than 63 octets
        * Texual representation can not exceed 253 characters
        * No level can begin or end with -

    3. Maximum mailbox length is len(local-part) + len('@') + len(domain) which
       is 64 + 1 + 253 = 318 characters. Allow 194 characters for a display
       name and the (very generous) limit becomes 512 characters. Allow 1024
       mailboxes and the total limit on a mailbox-list is 524288 characters.
"""

import re
import addresslib.address

from addresslib.tokenizer import TokenStream
from addresslib.tokenizer import LBRACKET
from addresslib.tokenizer import AT_SYMBOL
from addresslib.tokenizer import RBRACKET
from addresslib.tokenizer import DQUOTE
from addresslib.tokenizer import BAD_DOMAIN
from addresslib.tokenizer import DELIMITER
from addresslib.tokenizer import RELAX_ATOM
from addresslib.tokenizer import WHITESPACE
from addresslib.tokenizer import UNI_WHITE
from addresslib.tokenizer import ATOM
from addresslib.tokenizer import UNI_ATOM
from addresslib.tokenizer import UNI_QSTR
from addresslib.tokenizer import DOT_ATOM
from addresslib.tokenizer import QSTRING
from addresslib.tokenizer import URL

from .utils import is_pure_ascii
from .utils import contains_control_chars
from .utils import cleanup_display_name
from .utils import cleanup_email


class _AddressParser(object):
    """
    Do not use _AddressParser directly because it heavily relies on other
    private classes and methods and its interface is not guaranteed. It
    will change in the future and possibly break your application.

    Instead use the parse() function in the address.py module which will
    always return a scalar or iterable respectively.
    """

    def __init__(self, strict=False):
        self.stream = None
        self.strict = strict

    def address_list(self, stream):
        """
        Extract a mailbox and/or url list from a stream of input, operates in
        strict and relaxed modes.
        """
        # sanity check
        if not stream:
            raise ParserException('No input provided to parser.')
        if isinstance(stream, str) and not is_pure_ascii(stream):
            raise ParserException('ASCII string contains non-ASCII chars.')

        # to avoid spinning here forever, limit address list length
        if len(stream) > MAX_ADDRESS_LIST_LENGTH:
            raise ParserException('Stream length exceeds maximum allowable ' + \
                'address list length of ' + str(MAX_ADDRESS_LIST_LENGTH) + '.')

        # set stream
        self.stream = TokenStream(stream)

        if self.strict is True:
            return self._address_list_strict()
        return self._address_list_relaxed()

    def address(self, stream):
        """
        Extract a single address or url from a stream of input, always
        operates in strict mode.
        """
        # sanity check
        if not stream:
            raise ParserException('No input provided to parser.')
        if isinstance(stream, str) and not is_pure_ascii(stream):
            raise ParserException('ASCII string contains non-ASCII chars.')

        # to avoid spinning here forever, limit mailbox length
        if len(stream) > MAX_ADDRESS_LENGTH:
            raise ParserException('Stream length exceeds maximum allowable ' + \
                'address length of ' + str(MAX_ADDRESS_LENGTH) + '.')

        self.stream = TokenStream(stream)

        addr = self._address()
        if addr:
            # optional whitespace
            self._whitespace()

            # if we hit the end of the stream, we have a valid inbox
            if self.stream.end_of_stream():
                return addr

        return None

    def address_spec(self, stream):
        """
        Extract a single address spec from a stream of input, always
        operates in strict mode.
        """
        # sanity check
        if stream is None:
            raise ParserException('No input provided to parser.')
        if isinstance(stream, str) and not is_pure_ascii(stream):
            raise ParserException('ASCII string contains non-ASCII chars.')

        # to avoid spinning here forever, limit mailbox length
        if len(stream) > MAX_ADDRESS_LENGTH:
            raise ParserException('Stream length exceeds maximum allowable ' + \
                'address length of ' + str(MAX_ADDRESS_LENGTH) + '.')

        self.stream = TokenStream(stream)

        addr = self._addr_spec()
        if addr:
            # optional whitespace
            self._whitespace()

            # if we hit the end of the stream, we have a valid inbox
            if self.stream.end_of_stream():
                return addr

        return None


    def _mailbox_post_processing_checks(self, address):
        """
        Additional post processing checks to ensure mailbox is valid.
        """
        parts = address.split('@')

        # check if local part is less than 1024 octets, the actual
        # limit is 64 octets but we allow 16x that size here because
        # unsubscribe links are frequently longer
        lpart = parts[0]
        if len(lpart) > 1024:
            return False

        # check if the domain is less than 255 octets
        domn = parts[1]
        if len(domn) > 253:
            return False

        # number of labels can not be over 127
        labels = domn.split('.')
        if len(labels) > 127:
            return False

        for label in labels:
            # check the domain doesn't start or end with - and
            # the length of each label is no more than 63 octets
            if BAD_DOMAIN.search(label) or len(label) > 63:
                return False

        return True

    def _address_list_relaxed(self):
        """
        Grammar: address-list-relaxed -> address { delimiter address }
        """
        #addrs = []
        addrs = addresslib.address.AddressList()
        unparsable = []

        # address
        addr = self._address()
        if addr is None:
            # synchronize to the next delimiter (or end of line)
            # append the skipped over text to the unparsable list
            skip = self.stream.synchronize()
            if skip:
                unparsable.append(skip)

            # if no mailbox and end of stream, we were unable
            # return the unparsable stream
            if self.stream.end_of_stream():
                return [], unparsable
        else:
            # if we found a delimiter or end of stream, we have a
            # valid mailbox, add it
            if self.stream.peek(DELIMITER) or self.stream.end_of_stream():
                addrs.append(addr)
            else:
                # otherwise snychornize and add it the unparsable array
                skip = self.stream.synchronize()
                if skip:
                    pre = self.stream.stream[:self.stream.stream.index(skip)]
                    unparsable.append(pre + skip)
                # if we hit the end of the stream, return the results
                if self.stream.end_of_stream():
                    return [], [self.stream.stream]

        while True:
            # delimiter
            dlm = self.stream.get_token(DELIMITER)
            if dlm is None:
                skip = self.stream.synchronize()
                if skip:
                    unparsable.append(skip)
                if self.stream.end_of_stream():
                    break

            # address
            start_pos = self.stream.position
            addr = self._address()
            if addr is None:
                skip = self.stream.synchronize()
                if skip:
                    unparsable.append(skip)

                if self.stream.end_of_stream():
                    break
            else:
                # if we found a delimiter or end of stream, we have a
                # valid mailbox, add it
                if self.stream.peek(DELIMITER) or self.stream.end_of_stream():
                    addrs.append(addr)
                else:
                    # otherwise snychornize and add it the unparsable array
                    skip = self.stream.synchronize()
                    if skip:
                        sskip = self.stream.stream[start_pos:self.stream.position]
                        unparsable.append(sskip)
                    # if we hit the end of the stream, return the results
                    if self.stream.end_of_stream():
                        return addrs, unparsable

        return addrs, unparsable

    def _address_list_strict(self):
        """
        Grammar: address-list-strict -> address { delimiter address }
        """
        #addrs = []
        addrs = addresslib.address.AddressList()

        # address
        addr = self._address()
        if addr is None:
            return addrs
        if self.stream.peek(DELIMITER):
            addrs.append(addr)

        while True:
            # delimiter
            dlm = self.stream.get_token(DELIMITER)
            if dlm is None:
                break

            # address
            addr = self._address()
            if addr is None:
                break
            addrs.append(addr)

        return addrs

    def _address(self):
        """
        Grammar: address -> name-addr-rfc | name-addr-lax | addr-spec | url
        """
        start_pos = self.stream.position

        addr = self._addr_spec()

        # if email address, check that it passes post processing checks
        if addr and isinstance(addr, addresslib.address.EmailAddress):
            if self._mailbox_post_processing_checks(addr.address) is False:
                # roll back
                self.stream.position = start_pos
                return None

        return addr

    def _addr_spec(self, as_string=False):
        """
        Grammar: addr-spec -> [ whitespace ] local-part @ domain [ whitespace ]
        """
        start_pos = self.stream.position

        # optional whitespace
        self._whitespace()

        lpart = self._local_part()
        if lpart is None:
            # rollback
            self.stream.position = start_pos
            return None

        asym = self.stream.get_token(AT_SYMBOL)
        if asym is None:
            # rollback
            self.stream.position = start_pos
            return None

        domn = self._domain()
        if domn is None:
            # rollback
            self.stream.position = start_pos
            return None

        # optional whitespace
        self._whitespace()

        aspec = cleanup_email(''.join([lpart, asym, domn]))
        if as_string:
            return aspec
        return addresslib.address.EmailAddress(aspec)

    def _local_part(self):
        """
        Grammar: local-part -> dot-atom | quoted-string
        """
        return self.stream.get_token(DOT_ATOM) or \
            self.stream.get_token(QSTRING)

    def _domain(self):
        """
        Grammar: domain -> dot-atom
        """
        return self.stream.get_token(DOT_ATOM)

    def _word(self):
        """
        Grammar: word -> word-ascii | word-unicode
        """
        start_pos = self.stream.position

        # ascii word
        ascii_wrd = self._word_ascii()
        if ascii_wrd and not self.stream.peek(UNI_ATOM):
            return ascii_wrd

        # didn't get an ascii word, rollback to try again
        self.stream.position = start_pos

        # unicode word
        return self._word_unicode()

    def _word_ascii(self):
        """
        Grammar: word-ascii -> atom | qstring
        """
        wrd = self.stream.get_token(RELAX_ATOM) or self.stream.get_token(QSTRING)
        if wrd and not contains_control_chars(wrd):
            return wrd

        return None

    def _word_unicode(self):
        """
        Grammar: word-unicode -> unicode-atom | unicode-qstring
        """
        start_pos = self.stream.position

        # unicode atom
        uwrd = self.stream.get_token(UNI_ATOM)
        if uwrd and isinstance(uwrd, str) and not contains_control_chars(uwrd):
            return uwrd

        # unicode qstr
        uwrd = self.stream.get_token(UNI_QSTR, 'qstr')
        if uwrd and isinstance(uwrd, str) and not contains_control_chars(uwrd):
            return '"{0}"'.format(encode_string(None, uwrd))

        # rollback
        self.stream.position = start_pos
        return None


    def _whitespace(self):
        """
        Grammar: whitespace -> whitespace-ascii | whitespace-unicode
        """
        return self._whitespace_ascii() or self._whitespace_unicode()

    def _whitespace_ascii(self):
        """
        Grammar: whitespace-ascii -> whitespace-ascii
        """
        return self.stream.get_token(WHITESPACE)

    def _whitespace_unicode(self):
        """
        Grammar: whitespace-unicode -> whitespace-unicode
        """
        uwhite = self.stream.get_token(UNI_WHITE)
        if uwhite and not is_pure_ascii(uwhite):
            return uwhite
        return None


class ParserException(Exception):
    """
    Exception raised when the parser encounters some parsing exception.
    """
    def __init__(self, reason='Unknown parser error.'):
        self.reason = reason

    def __str__(self):
        return self.reason



MAX_ADDRESS_LENGTH = 1280
MAX_ADDRESS_NUMBER = 1024
MAX_ADDRESS_LIST_LENGTH = MAX_ADDRESS_LENGTH * MAX_ADDRESS_NUMBER
