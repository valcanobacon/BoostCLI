from src.cli.commands.boost import SATOSHISTREAM_PUBKEYS, shorten


def test_shorten():
    pubkey = SATOSHISTREAM_PUBKEYS[0]
    assert shorten(pubkey) == "03c457fa ... 1a8ae1a4"
    assert shorten(pubkey, segment_length=6) == "03c457 ... 8ae1a4"
    assert shorten(pubkey, seperator="-") == "03c457fa-1a8ae1a4"
