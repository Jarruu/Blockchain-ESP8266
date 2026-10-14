import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain import Block, Blockchain, REWARD


def test_genesis_is_single_and_valid():
    bc = Blockchain(difficulty=2)
    assert len(bc.chain) == 1
    assert bc.chain[0].index == 0
    assert bc.chain[0].previous_hash == "0"
    assert bc.is_chain_valid()


def test_mined_block_meets_pow():
    bc = Blockchain(difficulty=2)
    blk = bc.mine_block("minerA")
    assert blk.hash.startswith("00")
    assert blk.hash == blk.compute_hash()
    assert bc.is_chain_valid()


def test_tampering_is_detected():
    bc = Blockchain(difficulty=2)
    bc.mine_block("minerA")
    bc.chain[1].transactions[0]["amount"] = 999999
    assert bc.is_chain_valid() is False


def test_reward_goes_to_miner():
    bc = Blockchain(difficulty=2)
    bc.mine_block("minerA")
    bc.mine_block("minerA")
    assert bc.balances()["minerA"] == REWARD * 2


def test_transfer_moves_balance():
    bc = Blockchain(difficulty=2)
    bc.mine_block("minerA")                 # minerA punya 50
    bc.add_transaction("minerA", "esp01", 10)
    bc.mine_block("minerB")
    b = bc.balances()
    assert b["minerA"] == REWARD - 10
    assert b["esp01"] == 10


def test_replace_chain_accepts_longer_valid():
    bc = Blockchain(difficulty=2)
    other = Blockchain(difficulty=2)
    other.mine_block("m")
    other.mine_block("m")
    assert bc.replace_chain(other.chain) is True
    assert len(bc.chain) == len(other.chain)


def test_replace_chain_rejects_longer_invalid():
    bc = Blockchain(difficulty=2)
    bc.mine_block("m")
    other = Blockchain(difficulty=2)
    other.mine_block("m")
    other.mine_block("m")
    other.chain[1].transactions[0]["amount"] = 1  # rusak
    assert bc.replace_chain(other.chain) is False
    assert len(bc.chain) == 2


def test_replace_chain_rejects_shorter():
    bc = Blockchain(difficulty=2)
    bc.mine_block("m")
    bc.mine_block("m")
    other = Blockchain(difficulty=2)
    other.mine_block("m")
    assert bc.replace_chain(other.chain) is False


def test_add_transaction_rejects_nonpositive():
    bc = Blockchain(difficulty=2)
    for bad in (0, -5):
        try:
            bc.add_transaction("a", "b", bad)
            assert False, f"amount {bad} seharusnya ditolak"
        except ValueError:
            pass
