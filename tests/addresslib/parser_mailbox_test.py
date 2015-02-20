# coding:utf-8

from nose.tools import nottest, assert_equal, assert_not_equal

from addresslib import address
from addresslib.address import EmailAddress
from addresslib.parser import ParserException

VALID_QTEXT         = [chr(x) for x in [0x21] + list(range(0x23, 0x5b)) + list(range(0x5d, 0x7e))]
VALID_QUOTED_PAIR   = [chr(x) for x in range(0x20, 0x7e)]

FULL_QTEXT = ''.join(VALID_QTEXT)
FULL_QUOTED_PAIR = '\\' + '\\'.join(VALID_QUOTED_PAIR)

CONTROL_CHARS = ''.join(map(chr, list(range(0, 9)) + list(range(14, 32)) + list(range(127, 160))))

@nottest
def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]

@nottest
def run_mailbox_test(string, expected_string):
    mbox = address.parse(string)
    if mbox:
        assert_equal(expected_string, mbox.address)
        return
    assert_equal(expected_string, mbox)


def test_mailbox():
    "Grammar: mailbox -> name-addr | addr-spec"

    # sanity
    run_mailbox_test('steve@apple.com', 'steve@apple.com')


def test_name_addr():
    "Grammar: name-addr -> [ display-name ] angle-addr"

    # sanity
    run_mailbox_test('Linus Torvalds', None)
    run_mailbox_test('Linus Torvalds <>', None)
    run_mailbox_test('linus@kernel.org', 'linus@kernel.org')
    try:
        run_mailbox_test(' ', None)
    except ParserException:
        pass

def test_addr_spec():
    "Grammar: addr-spec -> [ whitespace ] local-part @ domain [ whitespace ]"

    # pass addr-spec
    run_mailbox_test('linus@kernel.org', 'linus@kernel.org')
    run_mailbox_test(' linus@kernel.org', 'linus@kernel.org')
    run_mailbox_test('linus@kernel.org ', 'linus@kernel.org')
    run_mailbox_test(' linus@kernel.org ', 'linus@kernel.org')
    run_mailbox_test('linus@localhost', 'linus@localhost')

    # fail addr-spec
    run_mailbox_test('linus@', None)
    run_mailbox_test('linus@ ', None)
    run_mailbox_test('linus@;', None)
    run_mailbox_test('linus@@kernel.org', None)
    run_mailbox_test('linus@ @kernel.org', None)
    run_mailbox_test('linus@ @localhost', None)
    run_mailbox_test('linus-at-kernel.org', None)
    run_mailbox_test('linus at kernel.org', None)
    run_mailbox_test('linus kernel.org', None)


def test_local_part():
    "Grammar: local-part -> dot-atom | quoted-string"

    # test length limits
    run_mailbox_test(''.join(['a'*128, '@b']), ''.join(['a'*128, '@b']))
    run_mailbox_test(''.join(['a'*1025, '@b']), None)

    # because qtext and quoted-pair are longer than 64 bytes (limit on local-part)
    # we use a sample in testing, every other for qtext and every fifth for quoted-pair
    sample_qtext = FULL_QTEXT[::2]
    sample_qpair = FULL_QUOTED_PAIR[::5]
    sample_qpair_without_slashes = sample_qpair[1::2]

    # pass dot-atom
    run_mailbox_test('ABCDEFGHIJKLMNOPQRSTUVWXYZ@apple.com', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ@apple.com')
    run_mailbox_test('abcdefghijklmnopqrstuvwzyz@apple.com', 'abcdefghijklmnopqrstuvwzyz@apple.com')
    run_mailbox_test('0123456789@apple.com', '0123456789@apple.com')
    run_mailbox_test('!#$%&\'*+-/=?^_`{|}~@apple.com', '!#$%&\'*+-/=?^_`{|}~@apple.com')
    run_mailbox_test('AZaz09!#$%&\'*+-/=?^_`{|}~@apple.com', 'AZaz09!#$%&\'*+-/=?^_`{|}~@apple.com')
    run_mailbox_test('steve@apple.com', 'steve@apple.com')
    run_mailbox_test(' steve@apple.com', 'steve@apple.com')
    run_mailbox_test('  steve@apple.com', 'steve@apple.com')

    # fail dot-atom
    run_mailbox_test('steve @apple.com', None)
    run_mailbox_test(' steve @apple.com', None)
    run_mailbox_test(', steve@apple.com', None)
    run_mailbox_test(';;steve@apple.com', None)
    run_mailbox_test('"steve@apple.com', None)
    run_mailbox_test('steve"@apple.com', None)
    run_mailbox_test('steve jobs @apple.com', None)
    run_mailbox_test(' steve jobs @apple.com', None)
    run_mailbox_test('steve..jobs@apple.com', None)

    # pass qtext
    for cnk in chunks(FULL_QTEXT, len(FULL_QTEXT)//2):
        run_mailbox_test('"{0}"@b'.format(cnk), '"{0}"@b'.format(cnk))
    run_mailbox_test('" {0}"@b'.format(sample_qtext), '" {0}"@b'.format(sample_qtext))
    run_mailbox_test('"{0} "@b'.format(sample_qtext), '"{0} "@b'.format(sample_qtext))
    run_mailbox_test('" {0} "@b'.format(sample_qtext), '" {0} "@b'.format(sample_qtext))

    # fail qtext
    run_mailbox_test('"{0}""{0}"@b'.format(sample_qtext), None)
    run_mailbox_test('"john""smith"@b'.format(sample_qtext), None)
    run_mailbox_test('"{0}" @b'.format(sample_qtext), None)
    run_mailbox_test(' "{0}" @b'.format(sample_qtext), None)
    run_mailbox_test('"{0}@b'.format(sample_qtext), None)
    run_mailbox_test('{0}"@b'.format(sample_qtext), None)
    run_mailbox_test('{0}@b'.format(sample_qtext), None)
    run_mailbox_test('"{0}@b"'.format(sample_qtext), None)

    # pass quoted-pair
    for cnk in chunks(FULL_QUOTED_PAIR, len(FULL_QUOTED_PAIR)//3):
        run_mailbox_test('"{0}"@b'.format(cnk), '"{0}"@b'.format(cnk))
    run_mailbox_test('" {0}"@b'.format(sample_qpair), '" {0}"@b'.format(sample_qpair))
    run_mailbox_test('"{0} "@b'.format(sample_qpair), '"{0} "@b'.format(sample_qpair))
    run_mailbox_test('" {0} "@b'.format(sample_qpair), '" {0} "@b'.format(sample_qpair))

    # fail quoted-pair
    run_mailbox_test('"{0}""{0}"@b'.format(sample_qpair), None)
    run_mailbox_test('"john""smith"@b'.format(sample_qpair), None)
    run_mailbox_test('"{0}" @b'.format(sample_qpair), None)
    run_mailbox_test(' "{0}" @b'.format(sample_qpair), None)
    run_mailbox_test('"{0}@b'.format(sample_qpair), None)
    run_mailbox_test('{0}"@b'.format(sample_qpair), None)
    run_mailbox_test('{0}@b'.format(sample_qpair), None)
    run_mailbox_test('"{0}@b"'.format(sample_qpair), None)


def test_domain():
    "Grammar: domain -> dot-atom"

    # test length limits
    max_domain_len = ''.join(['a'*62, '.', 'b'*62, '.', 'c'*63, '.', 'd'*63])
    overlimit_domain_one = ''.join(['a'*62, '.', 'b'*62, '.', 'c'*63, '.', 'd'*64])
    overlimit_domain_two = ''.join(['a'*62, '.', 'b'*62, '.', 'c'*63, '.', 'd'*63, '.', 'a'])
    run_mailbox_test(''.join(['b@', 'a'*63]), ''.join(['b@', 'a'*63]))
    run_mailbox_test(''.join(['b@', 'a'*64]), None)
    run_mailbox_test(''.join(['a@', max_domain_len]), ''.join(['a@', max_domain_len]))
    run_mailbox_test(''.join(['a@', overlimit_domain_one]), None)
    run_mailbox_test(''.join(['a@', overlimit_domain_two]), None)


    # pass dot-atom
    run_mailbox_test('bill@ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'bill@abcdefghijklmnopqrstuvwxyz')
    run_mailbox_test('bill@abcdefghijklmnopqrstuvwxyz', 'bill@abcdefghijklmnopqrstuvwxyz')
    run_mailbox_test('bill@0123456789', 'bill@0123456789')
    run_mailbox_test('bill@!#$%&\'*+-/=?^_`{|}~', 'bill@!#$%&\'*+-/=?^_`{|}~')
    run_mailbox_test('bill@microsoft.com', 'bill@microsoft.com')
    run_mailbox_test('bill@retired.microsoft.com', 'bill@retired.microsoft.com')
    run_mailbox_test('bill@microsoft.com ', 'bill@microsoft.com')
    run_mailbox_test('bill@microsoft.com  ', 'bill@microsoft.com')

    # fail dot-atom
    run_mailbox_test('bill@micro soft.com', None)
    run_mailbox_test('bill@micro. soft.com', None)
    run_mailbox_test('bill@micro .soft.com', None)
    run_mailbox_test('bill@micro. .soft.com', None)
    run_mailbox_test('bill@microsoft.com,', None)
    run_mailbox_test('bill@microsoft.com, ', None)
    run_mailbox_test('bill@microsoft.com, ', None)
    run_mailbox_test('bill@microsoft.com , ', None)
    run_mailbox_test('bill@microsoft.com,,', None)
    run_mailbox_test('bill@microsoft.com.', None)
    run_mailbox_test('bill@microsoft.com..', None)
    run_mailbox_test('bill@microsoft..com', None)
    run_mailbox_test('bill@retired.microsoft..com', None)
    run_mailbox_test('bill@.com', None)
    run_mailbox_test('bill@.com.', None)
    run_mailbox_test('bill@.microsoft.com', None)
    run_mailbox_test('bill@.microsoft.com.', None)
    run_mailbox_test('bill@"microsoft.com"', None)
    run_mailbox_test('bill@"microsoft.com', None)
    run_mailbox_test('bill@microsoft.com"', None)
