from typing import Dict, List

from solana.blockhash import Blockhash
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.transaction import Transaction

from program_admin.types import (
    Network,
    PythMappingAccount,
    ReferenceOverrides,
    ReferencePermissions,
)

MAPPING_ACCOUNT_SIZE = 20536  # https://github.com/pyth-network/pyth-client/blob/b49f73afe32ce8685a3d05e32d8f3bb51909b061/program/src/oracle/oracle.h#L88
MAPPING_ACCOUNT_PRODUCT_LIMIT = 640
PRICE_ACCOUNT_SIZE = 3312
PRODUCT_ACCOUNT_SIZE = 512
SOL_LAMPORTS = pow(10, 9)


async def recent_blockhash(client: AsyncClient) -> Blockhash:
    blockhash_response = await client.get_latest_blockhash(
        commitment=Commitment("finalized")
    )

    if not blockhash_response.value:
        raise RuntimeError("Failed to get recent blockhash")

    return Blockhash(str(blockhash_response.value.blockhash))


async def account_exists(rpc_endpoint: str, key: PublicKey) -> bool:
    client = AsyncClient(rpc_endpoint)
    response = await client.get_account_info(key)

    return bool(response.value)


def compute_transaction_size(transaction: Transaction) -> int:
    """
    Returns the total over-the-wire size of a transaction
    """

    return len(transaction.serialize())


def encode_product_metadata(data: Dict[str, str]) -> bytes:
    buffer = b""

    for key, value in data.items():
        key_bytes = key.encode("utf8")
        key_len = len(key_bytes).to_bytes(1, byteorder="little")
        value_bytes = value.encode("utf8")
        value_len = len(value_bytes).to_bytes(1, byteorder="little")

        buffer += key_len + key_bytes + value_len + value_bytes

    return buffer


def sort_mapping_account_keys(accounts: List[PythMappingAccount]) -> List[PublicKey]:
    """
    Takes a list of mapping accounts and returns a list of mapping account keys
    matching the order of the mapping linked list
    """
    if not accounts:
        return []

    # We can easily tell which is the last key (its next key is 0), so start
    # from it and build a reverse linked list as a "previous keys" dict.
    previous_keys = {}
    last_key = None

    for account in accounts:
        this_key = account.public_key
        next_key = account.data.next_mapping_account_key

        if next_key == PublicKey(0):
            last_key = this_key

        previous_keys[next_key] = this_key

    if not last_key:
        raise RuntimeError("The linked list has no end")

    # Now traverse the inverted linked list and build a list in the right order
    sorted_keys: List[PublicKey] = []
    current: PublicKey = last_key

    while len(accounts) != len(sorted_keys):
        sorted_keys.insert(0, current)

        # There is no previous key to the first key
        if previous_keys.get(current):
            current = previous_keys[current]

    return sorted_keys


def apply_overrides(
    ref_permissions: ReferencePermissions,
    ref_overrides: ReferenceOverrides,
    network: Network,
) -> ReferencePermissions:
    network_overrides = ref_overrides.get(network, {})

    overridden_permissions: ReferencePermissions = {}
    for key, value in ref_permissions.items():
        if key in network_overrides and not network_overrides[key]:
            # Remove all publishers from all account types for this symbol
            overridden_permissions[key] = {k: [] for k in value.keys()}
        else:
            overridden_permissions[key] = value
    return overridden_permissions


def get_actual_signers(
    signers: List[Keypair], transaction: Transaction
) -> List[Keypair]:
    """
    Given a list of keypairs and a transaction, returns the keypairs that actually need to sign the transaction,
    i.e. those whose pubkey appears in at least one of the instructions as a signer.
    """
    actual_signers = []
    for signer in signers:
        instruction_has_signer = [
            any(
                signer.public_key == account.pubkey and account.is_signer
                for account in instruction.keys
            )
            for instruction in transaction.instructions
        ]
        if any(instruction_has_signer):
            actual_signers.append(signer)

    return actual_signers
