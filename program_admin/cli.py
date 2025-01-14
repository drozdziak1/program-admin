import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict

import click
from loguru import logger
from solana.publickey import PublicKey

from program_admin import ProgramAdmin, instructions
from program_admin.keys import load_keypair, restore_symlink
from program_admin.parsing import (
    parse_permissions_with_overrides,
    parse_products_json,
    parse_publishers_json,
)
from program_admin.program_authority_escrow.instructions import propose


@click.group()
def cli():
    pass


@click.command()
@click.option("--network", help="Solana network", envvar="NETWORK")
@click.option("--rpc-endpoint", help="Solana RPC endpoint", envvar="RPC_ENDPOINT")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--keys", help="Path to keys directory", envvar="KEYS")
@click.option(
    "--commitment",
    help="Confirmation level to use",
    envvar="COMMITMENT",
    default="finalized",
)
@click.option("--product", help="Public key of the product account")
@click.option("--price", help="Public key of the price account")
@click.option(
    "--dump",
    help="Output instructions rather than transact",
    envvar="DUMP",
    default=False,
)
@click.option(
    "--outfile",
    help="File location to write instructions",
    envvar="OUTFILE",
    default="./instructions.json",
)
def delete_price(network, rpc_endpoint, program_key, keys, commitment, product, price):
    program_admin = ProgramAdmin(
        network=network,
        rpc_endpoint=rpc_endpoint,
        key_dir=keys,
        program_key=program_key,
        commitment=commitment,
    )
    funding_keypair = load_keypair("funding", key_dir=keys)
    product_keypair = load_keypair(PublicKey(product), key_dir=keys)
    price_keypair = load_keypair(PublicKey(price), key_dir=keys)
    instruction = instructions.delete_price(
        program_key,
        funding_keypair.public_key,
        product_keypair.public_key,
        price_keypair.public_key,
    )

    asyncio.run(
        program_admin.send_transaction(
            [instruction], [funding_keypair, product_keypair, price_keypair]
        )
    )


@click.command()
@click.option("--funding-key", help="Funding key", envvar="FUNDING_KEY")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--price-key", help="Price account key", envvar="PRICE_KEY")
@click.option("--value", help="New value for minimum publishers", type=int)
@click.option(
    "--outfile",
    help="File location to write instructions",
    envvar="OUTFILE",
    default=None,
)
def set_minimum_publishers(funding_key, program_key, price_key, value, outfile):
    funding = PublicKey(funding_key)
    program = PublicKey(program_key)
    price = PublicKey(price_key)
    instruction = instructions.set_minimum_publishers(program, funding, price, value)

    instruction_output = json.dumps(
        [
            {
                "program_id": str(program),
                "data": instruction.data.hex(),
                "accounts": [
                    {
                        "pubkey": str(account.pubkey),
                        "is_signer": account.is_signer,
                        "is_writable": account.is_writable,
                    }
                    for account in instruction.keys
                ],
            }
        ]
    )

    sys.stdout.write(instruction_output)
    if outfile:
        with open(outfile, "w", encoding="utf-8") as output_file:
            output_file.write(instruction_output)


@click.command()
@click.option("--funding-key", help="Funding key", envvar="FUNDING_KEY")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--product-key", help="Product account key", envvar="PRODUCT_KEY")
@click.option("--metadata", help="Metadata to add to product", type=dict)
@click.option(
    "--outfile",
    help="File location to write instructions",
    envvar="OUTFILE",
    default=None,
)
def update_product_metadata(funding_key, program_key, product_key, metadata, outfile):
    funding = PublicKey(funding_key)
    program = PublicKey(program_key)
    product = PublicKey(product_key)
    instruction = instructions.update_product(program, funding, product, metadata)

    instruction_output = json.dumps(
        [
            {
                "program_id": str(program),
                "data": instruction.data.hex(),
                "accounts": [
                    {
                        "pubkey": str(account.pubkey),
                        "is_signer": account.is_signer,
                        "is_writable": account.is_writable,
                    }
                    for account in instruction.keys
                ],
            }
        ]
    )

    sys.stdout.write(instruction_output)
    if outfile:
        with open(outfile, "w", encoding="utf-8") as output_file:
            output_file.write(instruction_output)


@click.command()
@click.option("--funding-key", help="Funding key", envvar="FUNDING_KEY")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--price-key", help="Price account key", envvar="PRICE_KEY")
@click.option("--publisher-key", help="Publisher account key", envvar="PUBLISHER_KEY")
@click.option("--status", help="Status of publisher", type=bool)
@click.option(
    "--outfile",
    help="File location to write instructions",
    envvar="OUTFILE",
    default=None,
)
def toggle_publisher(
    funding_key, program_key, price_key, publisher_key, status, outfile
):
    funding = PublicKey(funding_key)
    program = PublicKey(program_key)
    price = PublicKey(price_key)
    publisher = PublicKey(publisher_key)
    instruction = instructions.toggle_publisher(
        program, funding, price, publisher, status
    )

    instruction_output = json.dumps(
        [
            {
                "program_id": str(program),
                "data": instruction.data.hex(),
                "accounts": [
                    {
                        "pubkey": str(account.pubkey),
                        "is_signer": account.is_signer,
                        "is_writable": account.is_writable,
                    }
                    for account in instruction.keys
                ],
            }
        ]
    )

    sys.stdout.write(instruction_output)
    if outfile:
        with open(outfile, "w", encoding="utf-8") as output_file:
            output_file.write(instruction_output)


@click.command()
@click.option("--network", help="Solana network", envvar="NETWORK")
@click.option("--rpc-endpoint", help="Solana RPC endpoint", envvar="RPC_ENDPOINT")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--keys", help="Path to keys directory", envvar="KEYS")
@click.option(
    "--commitment",
    help="Confirmation level to use",
    envvar="COMMITMENT",
    default="finalized",
)
@click.option("--mapping", help="Public key of the mapping account")
@click.option("--product", help="Public key of the product account")
@click.option(
    "--dump",
    help="Output instructions rather than transact",
    envvar="DUMP",
    default=False,
)
@click.option(
    "--outfile",
    help="File location to write instructions",
    envvar="OUTFILE",
    default="./instructions.json",
)
def delete_product(
    network, rpc_endpoint, program_key, keys, commitment, mapping, product
):
    program_admin = ProgramAdmin(
        network=network,
        rpc_endpoint=rpc_endpoint,
        key_dir=keys,
        program_key=program_key,
        commitment=commitment,
    )
    funding_keypair = load_keypair("funding", key_dir=keys)
    mapping_keypair = load_keypair(PublicKey(mapping), key_dir=keys)
    product_keypair = load_keypair(PublicKey(product), key_dir=keys)
    instruction = instructions.delete_product(
        program_key,
        funding_keypair.public_key,
        mapping_keypair.public_key,
        product_keypair.public_key,
    )

    asyncio.run(
        program_admin.send_transaction(
            [instruction], [funding_keypair, mapping_keypair, product_keypair]
        )
    )


@click.command()
@click.option("--network", help="Solana network", envvar="NETWORK")
@click.option("--rpc-endpoint", help="Solana RPC endpoint", envvar="RPC_ENDPOINT")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--keys", help="Path to keys directory", envvar="KEYS")
@click.option(
    "--publishers", help="Path to reference publishers file", envvar="PUBLISHERS"
)
@click.option(
    "--commitment",
    help="Confirmation level to use",
    envvar="COMMITMENT",
    default="finalized",
)
def list_accounts(network, rpc_endpoint, program_key, keys, publishers, commitment):
    program_admin = ProgramAdmin(
        network=network,
        rpc_endpoint=rpc_endpoint,
        key_dir=keys,
        program_key=program_key,
        commitment=commitment,
    )

    asyncio.run(program_admin.refresh_program_accounts())

    try:
        mapping_key = program_admin.get_first_mapping_key()
    except IndexError:
        print("Program has no mapping accounts")
        sys.exit(1)

    publishers_map = parse_publishers_json(Path(publishers))

    while mapping_key != PublicKey(0):
        mapping_account = program_admin.get_mapping_account(mapping_key)
        print(f"Mapping: {mapping_account.public_key}")

        for product_key in mapping_account.data.product_account_keys:
            product_account = program_admin.get_product_account(product_key)
            print(f"  Product: {product_account.data.metadata['symbol']}")

            if product_account.data.first_price_account_key != PublicKey(0):
                price_account = program_admin.get_price_account(
                    product_account.data.first_price_account_key
                )
                print(
                    f"    Price: {price_account.data.exponent} exponent ({price_account.data.components_count} components)"
                )

                for component in price_account.data.price_components:
                    try:
                        name = publishers_map["names"][component.publisher_key]
                    except KeyError:
                        name = f"??? ({component.publisher_key})"

                    print(f"      Publisher: {name}")

        mapping_key = mapping_account.data.next_mapping_account_key


@click.command()
@click.option("--network", help="Solana network", envvar="NETWORK")
@click.option("--rpc-endpoint", help="Solana RPC endpoint", envvar="RPC_ENDPOINT")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--keys", help="Path to keys directory", envvar="KEYS")
@click.option("--products", help="Path to reference products file", envvar="PRODUCTS")
@click.option(
    "--commitment",
    help="Confirmation level to use",
    envvar="COMMITMENT",
    default="finalized",
)
def restore_links(network, rpc_endpoint, program_key, keys, products, commitment):
    program_admin = ProgramAdmin(
        network=network,
        rpc_endpoint=rpc_endpoint,
        key_dir=keys,
        program_key=program_key,
        commitment=commitment,
    )
    reference_products = parse_products_json(Path(products))
    mapping_account_counter = 0
    jump_symbols: Dict[str, str] = {}

    for jump_symbol, product in reference_products.items():
        jump_symbols[product["metadata"]["symbol"]] = jump_symbol

    asyncio.run(program_admin.refresh_program_accounts())

    try:
        mapping_key = program_admin.get_first_mapping_key()
    except IndexError:
        print("Program has no mapping accounts")
        sys.exit(1)

    while mapping_key != PublicKey(0):
        mapping_account = program_admin.get_mapping_account(mapping_key)

        restore_symlink(
            mapping_key, f"mapping_{mapping_account_counter}", program_admin.key_dir
        )

        for product_key in mapping_account.data.product_account_keys:
            product_account = program_admin.get_product_account(product_key)
            symbol = product_account.data.metadata["symbol"]
            jump_symbol = jump_symbols[symbol]

            restore_symlink(
                product_key, f"product_{jump_symbol}", program_admin.key_dir
            )

            # FIXME: Assumes there is only  a single first price account
            if product_account.data.first_price_account_key != PublicKey(0):
                restore_symlink(
                    product_account.data.first_price_account_key,
                    f"price_{jump_symbol}",
                    program_admin.key_dir,
                )

        mapping_key = mapping_account.data.next_mapping_account_key
        mapping_account_counter += 1


@click.command()
@click.option("--network", help="Solana network", envvar="NETWORK")
@click.option("--rpc-endpoint", help="Solana RPC endpoint", envvar="RPC_ENDPOINT")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option("--keys", help="Path to keys directory", envvar="KEYS")
@click.option("--products", help="Path to reference products file", envvar="PRODUCTS")
@click.option(
    "--publishers", help="Path to reference publishers file", envvar="PUBLISHERS"
)
@click.option(
    "--permissions", help="Path to reference permissions file", envvar="PERMISSIONS"
)
@click.option(
    "--overrides", help="Path to reference overrides file", envvar="OVERRIDES"
)
@click.option(
    "--commitment",
    help="Confirmation level to use",
    envvar="COMMITMENT",
    default="finalized",
)
@click.option(
    "--send-transactions",
    help="Whether to send transactions or just print instructions (set to 'true' or 'false')",
    envvar="SEND_TRANSACTIONS",
    default="true",
)
@click.option(
    "--generate-keys",
    help="If set to 'true', allow this command to generate new keypairs for new mapping/product/price accounts.",
    envvar="GENERATE_KEYS",
    default="false",
)
def sync(
    network,
    rpc_endpoint,
    program_key,
    keys,
    products,
    publishers,
    permissions,
    overrides,
    commitment,
    send_transactions,
    generate_keys,
):
    program_admin = ProgramAdmin(
        network=network,
        rpc_endpoint=rpc_endpoint,
        key_dir=keys,
        program_key=program_key,
        commitment=commitment,
    )

    ref_products = parse_products_json(Path(products))
    ref_publishers = parse_publishers_json(Path(publishers))
    ref_permissions = parse_permissions_with_overrides(
        Path(permissions), Path(overrides), network
    )

    asyncio.run(
        program_admin.sync(
            ref_products=ref_products,
            ref_publishers=ref_publishers,
            ref_permissions=ref_permissions,
            send_transactions=(send_transactions == "true"),
            generate_keys=(generate_keys == "true"),
        )
    )


@click.command()
@click.option("--network", help="Solana network", envvar="NETWORK")
@click.option("--rpc-endpoint", help="Solana RPC endpoint", envvar="RPC_ENDPOINT")
@click.option("--program-key", help="Pyth program key", envvar="PROGRAM_KEY")
@click.option(
    "--new-authority", help="New authority for the program", envvar="NEW_AUTHORITY"
)
@click.option("--keys", help="Path to keys directory", envvar="KEYS")
@click.option(
    "--commitment",
    help="Confirmation level to use",
    envvar="COMMITMENT",
    default="finalized",
)
def migrate_upgrade_authority(
    network,
    rpc_endpoint,
    program_key,
    new_authority,
    keys,
    commitment,
):
    program_admin = ProgramAdmin(
        network=network,
        rpc_endpoint=rpc_endpoint,
        key_dir=keys,
        program_key=program_key,
        commitment=commitment,
    )
    funding_keypair = load_keypair("funding", key_dir=keys)
    instruction = propose(
        {
            "current_authority": funding_keypair.public_key,
            "new_authority": PublicKey(new_authority),
            "program_account": PublicKey(program_key),
        }
    )
    asyncio.run(program_admin.send_transaction([instruction], [funding_keypair]))


cli.add_command(delete_price)
cli.add_command(delete_product)
cli.add_command(list_accounts)
cli.add_command(restore_links)
cli.add_command(sync)
cli.add_command(set_minimum_publishers)
cli.add_command(toggle_publisher)
cli.add_command(update_product_metadata)
cli.add_command(migrate_upgrade_authority)
logger.remove()
logger.add(sys.stdout, serialize=(not os.environ.get("DEV_MODE")))
