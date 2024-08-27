# Copyright 2024 Chelsea Anne McElveen

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import csv
import os
import threading
from collections import defaultdict
import hashlib
from typing import Union, Tuple, List, Callable, Dict
import binascii
import json
import xml.etree.ElementTree as ET
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiofiles
import asyncio
import math
import lz4.frame as lz4
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes
import base64

class FlatFileDatabase:
    def __init__(self, filename: str, log_filename: str = 'db_log.csv', schema: Dict[str, type] = None, max_workers: int = 4, shard_size: int = 1000, wal_filename: str = 'db_wal.log'):
        self.filename = filename
        self.log_filename = log_filename
        self.global_lock = threading.Lock()  # Fallback global lock
        self.locks = defaultdict(threading.Lock)  # Lock per record ID or shard
        self.counter = 0
        self.deletion_counter = 0
        self.indexes = defaultdict(dict)  # Dictionary to hold indexes
        self.transaction_file = None  # File used during transactions
        self.users = {}  # Dictionary to store users and their roles
        self.logged_in_user = None  # Currently logged-in user
        self.schema = schema or {}  # Schema definition
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # Thread pool executor
        self.shard_size = shard_size  # Number of records per shard
        self.wal_filename = wal_filename  # Write-Ahead Log filename
        self.indexes = {}  # Assuming some index structure
        self.insertion_count = 0
        self.deletion_count = 0
        
        # Additional initialization for handling data types
        self.data_type_converters = {
            int: int,
            float: float,
            str: str,
            # Add more data types as needed
        }
        
        # Load RSA keys from files
        self.private_key = RSA.import_key(open("private.pem").read())
        self.public_key = RSA.import_key(open("public.pem").read())

        # Initialize the RSA cipher for encryption and decryption
        self.cipher_encrypt = PKCS1_OAEP.new(self.public_key)
        self.cipher_decrypt = PKCS1_OAEP.new(self.private_key)

        # Initialize the database file and log file if they don't exist
        self.create_database()
        self._initialize_log()
        self._initialize_wal()

    def _compress(self, data: bytes) -> bytes:
        """Compresses data using LZ4."""
        return lz4.compress(data)

    def _decompress(self, compressed_data: bytes) -> bytes:
        """Decompresses LZ4 compressed data."""
        return lz4.decompress(compressed_data)

    def _encrypt(self, data: bytes) -> bytes:
        """Encrypts data using RSA."""
        encrypted_data = self.cipher_encrypt.encrypt(data)
        return base64.b64encode(encrypted_data)  # Convert to base64 for storage

    def _decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypts data using RSA."""
        decoded_data = base64.b64decode(encrypted_data)
        return self.cipher_decrypt.decrypt(decoded_data)

    def _initialize_wal(self):
        """Initializes the write-ahead log file."""
        if not os.path.exists(self.wal_filename):
            with open(self.wal_filename, 'w') as f:
                f.write("")  # Create an empty WAL file

    def _write_to_wal(self, operation: str, details: str):
        """Writes an operation to the write-ahead log."""
        try:
            with self.global_lock:
                with open(self.wal_filename, 'a') as f:
                    timestamp = datetime.now().isoformat()
                    f.write(f"{timestamp},{operation},{details}\n")
        except Exception as e:
            self._handle_error(f"Error writing to WAL: {str(e)}")

    def _get_shard_filename(self, record_id: int) -> str:
        """Returns the filename of the shard containing the given record ID."""
        shard_number = record_id // self.shard_size
        return f"{self.filename}_shard_{shard_number}.csv"

    def begin_transaction(self):
        """Begins a transaction with a prepare phase."""
        async def _begin_transaction_task():
            try:
                self._check_permission('write')
                self._write_to_wal('begin_transaction', 'Preparing transaction')

                # In the prepare phase, validate and log all intended changes
                # (Implementation depends on the specific use case)

                self._log_operation('begin_transaction', 'Transaction preparation complete')
            except Exception as e:
                self._handle_error(f"Error in begin transaction: {str(e)}")
                raise

        future = self.executor.submit(asyncio.run, _begin_transaction_task())
        return future

    def commit_transaction(self):
        """Commits a transaction after the prepare phase."""
        async def _commit_transaction_task():
            try:
                self._check_permission('write')
                self._write_to_wal('commit_transaction', 'Committing transaction')

                # Apply all the changes that were logged in the WAL during the prepare phase
                # (Implementation depends on the specific use case)

                self._log_operation('commit_transaction', 'Transaction committed')
            except Exception as e:
                self._handle_error(f"Error in commit transaction: {str(e)}")
                raise

        future = self.executor.submit(asyncio.run, _commit_transaction_task())
        return future

    def rollback_transaction(self):
        """Rolls back a transaction, undoing all changes logged in the WAL."""
        async def _rollback_transaction_task():
            try:
                self._check_permission('write')
                self._write_to_wal('rollback_transaction', 'Rolling back transaction')

                # Undo all changes that were logged in the WAL during the prepare phase
                # (Implementation depends on the specific use case)

                self._log_operation('rollback_transaction', 'Transaction rolled back')
            except Exception as e:
                self._handle_error(f"Error in rollback transaction: {str(e)}")
                raise

        future = self.executor.submit(asyncio.run, _rollback_transaction_task())
        return future


    async def _async_insert(self, current_counter, value_type, bitstring_value):
        lock = self._get_lock(current_counter)
        shard_filename = self._get_shard_filename(current_counter)

        async with lock:
            async with aiofiles.open(shard_filename, mode='a') as f:
                writer = csv.writer(await f.__anext__())
                await writer.writerow([current_counter, value_type, bitstring_value])

    def insert(self, value: Union[str, float, int, list, tuple]):
        """Inserts a new value into the database and increments the counter."""
        async def _insert_task():
            try:
                self._check_permission('write')
                value_type = type(value).__name__
                self._validate_data(value, value_type)
                
                # Convert value to bitstring
                bitstring_value = self._convert_to_bitstring(value).encode('utf-8')

                # Compress and encrypt the value
                compressed_value = self._compress(bitstring_value)
                encrypted_value = self._encrypt(compressed_value)

                # Use a global lock for counter operations to ensure thread safety
                async with self.global_lock:
                    current_counter = self.counter
                    self.counter += 1

                # Write the operation to WAL
                self._write_to_wal('insert', f'ID: {current_counter}, Type: {value_type}, Value: {encrypted_value}')

                await self._async_insert(current_counter, value_type, encrypted_value.decode('utf-8'))

                # Update indexes
                for index_name, index in self.indexes.items():
                    index_key = self._hash_value(encrypted_value)
                    index[index_key] = current_counter

                self._log_operation('insert', f'ID: {current_counter}, Type: {value_type}, Value: {value}')
            except Exception as e:
                self._handle_error(f"Error inserting value: {str(e)}")
                raise
            
        future = self.executor.submit(asyncio.run, _insert_task())
        return future

    def _get_lock(self, identifier: int):
        """Get a lock specific to a record or shard."""
        return self.locks[identifier]

    def create_database(self):
        """Creates the database file if it doesn't exist."""
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Type", "Value"])

    def delete_database(self):
        """Deletes the database file."""
        try:
            self._check_permission('delete')
            self._log_operation('delete_database', None)
            with self.lock:
                if os.path.exists(self.filename):
                    os.remove(self.filename)
                    print(f"Database {self.filename} deleted.")
                else:
                    print(f"Database {self.filename} does not exist.")
        except Exception as e:
            self._handle_error(f"Error deleting database: {str(e)}")

    def _initialize_log(self):
        """Initializes the log file."""
        if not os.path.exists(self.log_filename):
            with open(self.log_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "User", "Operation", "Details"])

    def _log_operation(self, operation: str, details: str):
        """Logs an operation to the log file."""
        with self.global_lock:
            with open(self.log_filename, 'a', newline='') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().isoformat()
                user = self.logged_in_user or 'System'
                writer.writerow([timestamp, user, operation, details])

    def _handle_error(self, error_message: str):
        """Handles errors by logging them and printing the message."""
        self._log_operation('error', error_message)
        print(f"Error: {error_message}")

    def _hash_value(self, value: Union[str, float, int, list, tuple]) -> str:
        """Hashes the value using SHA256 and returns the hex digest."""
        if isinstance(value, (list, tuple)):
            value = str(value)
        return hashlib.sha256(str(value).encode('utf-8')).hexdigest()

    def _convert_to_bitstring(self, value: Union[str, float, int, list, tuple]) -> str:
        """Converts a value to a bitstring."""
        try:
            if isinstance(value, (str, list, tuple)):
                value = str(value)
            elif isinstance(value, (int, float)):
                value = bin(int(binascii.hexlify(bytes(str(value), 'utf-8')), 16))
            else:
                raise ValueError("Unsupported data type for conversion to bitstring.")
            return binascii.hexlify(bytes(value, 'utf-8')).decode('utf-8')
        except Exception as e:
            self._handle_error(f"Error converting value to bitstring: {str(e)}")
            raise

    def _convert_from_bitstring(self, bitstring: str, original_type: str) -> Union[str, float, int, list, tuple]:
        """Converts a bitstring back to the original data type."""
        try:
            decoded = binascii.unhexlify(bitstring.encode('utf-8')).decode('utf-8')
            if original_type == 'str':
                return decoded
            elif original_type == 'int':
                return int(decoded)
            elif original_type == 'float':
                return float(decoded)
            elif original_type == 'list' or original_type == 'tuple':
                return eval(decoded)
            else:
                raise ValueError("Unsupported data type for conversion from bitstring.")
        except Exception as e:
            self._handle_error(f"Error converting bitstring to value: {str(e)}")
            raise

    def _hash_password(self, password: str) -> str:
        """Hashes a password using SHA256."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def add_user(self, username: str, password: str, role: str):
        """Adds a new user to the system with a hashed password and role."""
        try:
            if username in self.users:
                raise Exception("User already exists.")
            hashed_password = self._hash_password(password)
            self.users[username] = {'password': hashed_password, 'role': role}
            self._log_operation('add_user', f'User: {username}, Role: {role}')
            print(f"User {username} added with role {role}.")
        except Exception as e:
            self._handle_error(f"Error adding user: {str(e)}")

    def authenticate_user(self, username: str, password: str):
        """Authenticates a user with their username and password."""
        try:
            if username not in self.users:
                raise Exception("User does not exist.")
            hashed_password = self._hash_password(password)
            if self.users[username]['password'] != hashed_password:
                raise Exception("Incorrect password.")
            self.logged_in_user = username
            self._log_operation('authenticate_user', f'User: {username}')
            print(f"User {username} authenticated successfully.")
        except Exception as e:
            self._handle_error(f"Error authenticating user: {str(e)}")
            raise

    def _check_permission(self, operation: str):
        """Checks if the logged-in user has permission to perform the operation."""
        try:
            if not self.logged_in_user:
                raise Exception("No user is currently logged in.")
            role = self.users[self.logged_in_user]['role']
            permissions = {
                'admin': ['read', 'write', 'delete', 'compact', 'verify', 'report'],
                'editor': ['read', 'write', 'compact', 'verify', 'report'],
                'viewer': ['read', 'report']
            }
            if operation not in permissions.get(role, []):
                raise Exception(f"User {self.logged_in_user} does not have permission to perform {operation}.")
        except Exception as e:
            self._handle_error(f"Permission error: {str(e)}")
            raise

    def _validate_data(self, value: Union[str, float, int, list, tuple], value_type: str):
        """Validates the data against the schema or type."""
        try:
            expected_type = self.schema.get(value_type, type(value))
            if not isinstance(value, expected_type):
                raise ValueError(f"Expected {expected_type} but got {type(value)} for value: {value}")
        except Exception as e:
            self._handle_error(f"Data validation error: {str(e)}")
            raise

    def insert(self, value: Union[str, float, int, list, tuple]):
        """Inserts a new value into the database and increments the counter."""
        def _insert_task():
            try:
                self._check_permission('write')
                value_type = type(value).__name__
                self._validate_data(value, value_type)
                bitstring_value = self._convert_to_bitstring(value)

                # Use a global lock for counter operations to ensure thread safety
                with self.global_lock:
                    current_counter = self.counter
                    self.counter += 1

                lock = self._get_lock(current_counter)

                # Lock on a per-record basis
                with lock:
                    with open(self.transaction_file or self.filename, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([current_counter, value_type, bitstring_value])
                        
                        # Update indexes
                        for index_name, index in self.indexes.items():
                            index_key = self._hash_value(bitstring_value)
                            index[index_key] = current_counter
                        
                        self._log_operation('insert', f'ID: {current_counter}, Type: {value_type}, Value: {value}')
            except Exception as e:
                self._handle_error(f"Error inserting value: {str(e)}")
                raise
        
        future = self.executor.submit(_insert_task)
        return future

    def batch_insert(self, values: List[Union[str, float, int, list, tuple]]):
        """Inserts multiple values into the database in a single batch."""
        async def _batch_insert_task():
            try:
                self._check_permission('write')
                with self.global_lock:
                    start_counter = self.counter
                    self.counter += len(values)

                rows = []
                for i, value in enumerate(values):
                    value_type = type(value).__name__
                    self._validate_data(value, value_type)
                    
                    # Convert value to bitstring
                    bitstring_value = self._convert_to_bitstring(value).encode('utf-8')

                    # Compress and encrypt the value
                    compressed_value = self._compress(bitstring_value)
                    encrypted_value = self._encrypt(compressed_value)
                    
                    current_counter = start_counter + i

                    rows.append([current_counter, value_type, encrypted_value.decode('utf-8')])

                    # Update indexes
                    for index_name, index in self.indexes.items():
                        index_key = self._hash_value(encrypted_value)
                        index[index_key] = current_counter

                lock = self._get_lock(start_counter)
                with lock:
                    shard_filename = self._get_shard_filename(start_counter)
                    async with aiofiles.open(shard_filename, mode='a') as f:
                        writer = csv.writer(await f.__anext__())
                        await writer.writerows(rows)
                        
                self._log_operation('batch_insert', f'{len(values)} records inserted starting at ID {start_counter}')
            except Exception as e:
                self._handle_error(f"Error in batch insert: {str(e)}")
                raise

        future = self.executor.submit(asyncio.run, _batch_insert_task())
        return future

    def query(self, identifier: int) -> Union[str, float, int, list, tuple, None]:
        """Queries the database for an entry by ID."""
        async def _query_task():
            try:
                self._check_permission('read')
                lock = self._get_lock(identifier)
                shard_filename = self._get_shard_filename(identifier)

                async with lock:
                    async with aiofiles.open(shard_filename, mode='r') as f:
                        reader = csv.reader(await f.__anext__())
                        next(reader)  # Skip header
                        for row in reader:
                            if int(row[0]) == identifier:
                                value_type = row[1]
                                encrypted_value = row[2].encode('utf-8')

                                # Decrypt and decompress the value
                                compressed_value = self._decrypt(encrypted_value)
                                bitstring_value = self._decompress(compressed_value)

                                self._log_operation('query', f'ID: {identifier}')
                                return self._convert_from_bitstring(bitstring_value.decode('utf-8'), value_type)
                return None
            except Exception as e:
                self._handle_error(f"Error querying value: {str(e)}")
                raise
        
        future = self.executor.submit(asyncio.run, _query_task())
        return future

    async def _async_update(self, identifier, rows, header):
        lock = self._get_lock(identifier)
        async with lock:
            async with aiofiles.open(self.transaction_file or self.filename, mode='w') as f:
                writer = csv.writer(await f.__anext__())
                await writer.writerow(header)
                await writer.writerows(rows)

    async def _async_update(self, identifier, rows, header):
        lock = self._get_lock(identifier)
        shard_filename = self._get_shard_filename(identifier)

        async with lock:
            async with aiofiles.open(shard_filename, mode='w') as f:
                writer = csv.writer(await f.__anext__())
                await writer.writerow(header)
                await writer.writerows(rows)

    def update(self, identifier: int, new_value: Union[str, float, int, list, tuple]) -> bool:
        """Updates an existing record by ID with a new value."""
        async def _update_task():
            try:
                self._check_permission('write')
                value_type = type(new_value).__name__
                self._validate_data(new_value, value_type)
                
                # Convert value to bitstring
                bitstring_value = self._convert_to_bitstring(new_value).encode('utf-8')

                # Compress and encrypt the new value
                compressed_value = self._compress(bitstring_value)
                encrypted_value = self._encrypt(compressed_value)

                updated = False
                rows = []
                lock = self._get_lock(identifier)
                shard_filename = self._get_shard_filename(identifier)

                async with lock:
                    async with aiofiles.open(shard_filename, mode='r') as f:
                        reader = csv.reader(await f.__anext__())
                        header = next(reader)
                        for row in reader:
                            if int(row[0]) == identifier:
                                old_value = row[2].encode('utf-8')  # Encrypted value
                                row[1] = value_type
                                row[2] = encrypted_value.decode('utf-8')
                                updated = True
                                
                                # Update indexes
                                for index_name, index in self.indexes.items():
                                    old_key = self._hash_value(old_value)
                                    new_key = self._hash_value(encrypted_value)
                                    if old_key in index:
                                        del index[old_key]
                                    index[new_key] = identifier
                            
                            rows.append(row)

                    if updated:
                        await self._async_update(identifier, rows, header)

                    self._log_operation('update', f'ID: {identifier}, Old Value: {old_value}, New Value: {encrypted_value}')
            
            except Exception as e:
                self._handle_error(f"Error updating value: {str(e)}")
                raise
        
        future = self.executor.submit(asyncio.run, _update_task())
        return future

    def batch_update(self, updates: List[Tuple[int, Union[str, float, int, list, tuple]]]):
        """Updates multiple records in the database in a single batch."""
        async def _batch_update_task():
            try:
                self._check_permission('write')
                rows = []
                updated_ids = []

                for identifier, new_value in updates:
                    value_type = type(new_value).__name__
                    self._validate_data(new_value, value_type)
                    
                    # Convert value to bitstring
                    bitstring_value = self._convert_to_bitstring(new_value).encode('utf-8')

                    # Compress and encrypt the new value
                    compressed_value = self._compress(bitstring_value)
                    encrypted_value = self._encrypt(compressed_value)
                    
                    lock = self._get_lock(identifier)
                    shard_filename = self._get_shard_filename(identifier)

                    async with lock:
                        async with aiofiles.open(shard_filename, mode='r') as f:
                            reader = csv.reader(await f.__anext__())
                            header = next(reader)
                            for row in reader:
                                if int(row[0]) == identifier:
                                    old_value = row[2].encode('utf-8')  # Encrypted value
                                    row[1] = value_type
                                    row[2] = encrypted_value.decode('utf-8')
                                    updated_ids.append(identifier)
                                    
                                    # Update indexes
                                    for index_name, index in self.indexes.items():
                                        old_key = self._hash_value(old_value)
                                        new_key = self._hash_value(encrypted_value)
                                        if old_key in index:
                                            del index[old_key]
                                        index[new_key] = identifier
                                rows.append(row)

                    async with lock:
                        async with aiofiles.open(shard_filename, mode='w') as f:
                            writer = csv.writer(await f.__anext__())
                            await writer.writerow(header)
                            await writer.writerows(rows)

                self._log_operation('batch_update', f'{len(updates)} records updated: {updated_ids}')
            except Exception as e:
                self._handle_error(f"Error in batch update: {str(e)}")
                raise

        future = self.executor.submit(asyncio.run, _batch_update_task())
        return future

    async def _async_delete(self, rows, header, shard_filename):
        async with aiofiles.open(shard_filename, mode='w') as f:
            writer = csv.writer(await f.__anext__())
            await writer.writerow(header)
            await writer.writerows(rows)

    def delete(self, identifier: int):
        """Deletes an entry by ID and increments the deletion counter."""
        async def _delete_task():
            try:
                self._check_permission('delete')
                rows = []
                deleted_value = None
                lock = self._get_lock(identifier)
                shard_filename = self._get_shard_filename(identifier)

                async with lock:
                    async with aiofiles.open(shard_filename, mode='r') as f:
                        reader = csv.reader(await f.__anext__())
                        header = next(reader)
                        for row in reader:
                            if int(row[0]) != identifier:
                                rows.append(row)
                            else:
                                deleted_value = row[2].encode('utf-8')  # Encrypted value
                                async with self.global_lock:
                                    self.deletion_counter += 1
                                
                                # Update indexes
                                for index_name, index in self.indexes.items():
                                    index_key = self._hash_value(deleted_value)
                                    if index_key in index:
                                        del index[index_key]

                    await self._async_delete(rows, header, shard_filename)

                    self._log_operation('delete', f'ID: {identifier}, Value: {deleted_value}')
            except Exception as e:
                self._handle_error(f"Error deleting value: {str(e)}")
                raise
        
        future = self.executor.submit(asyncio.run, _delete_task())
        return future

    def batch_delete(self, identifiers: List[int]):
        """Deletes multiple records from the database in a single batch."""
        async def _batch_delete_task():
            try:
                self._check_permission('delete')
                rows = []
                deleted_ids = []

                with self.global_lock:
                    self.deletion_counter += len(identifiers)

                locks = [self._get_lock(identifier) for identifier in identifiers]

                for lock in locks:
                    async with lock:
                        identifier = identifiers.pop(0)
                        shard_filename = self._get_shard_filename(identifier)
                        async with aiofiles.open(shard_filename, mode='r') as f:
                            reader = csv.reader(await f.__anext__())
                            header = next(reader)
                            for row in reader:
                                if int(row[0]) not in identifiers:
                                    rows.append(row)
                                else:
                                    deleted_ids.append(int(row[0]))
                                    
                                    # Update indexes
                                    for index_name, index in self.indexes.items():
                                        index_key = self._hash_value(row[2].encode('utf-8'))  # Encrypted value
                                        if index_key in index:
                                            del index[index_key]

                        async with lock:
                            async with aiofiles.open(shard_filename, mode='w') as f:
                                writer = csv.writer(await f.__anext__())
                                await writer.writerow(header)
                                await writer.writerows(rows)

                self._log_operation('batch_delete', f'{len(identifiers)} records deleted: {deleted_ids}')
            except Exception as e:
                self._handle_error(f"Error in batch delete: {str(e)}")
                raise

        future = self.executor.submit(asyncio.run, _batch_delete_task())
        return future

    def create_shard(self, shard_number: int):
        """Creates a new shard if it doesn't already exist."""
        shard_filename = f"{self.filename}_shard_{shard_number}.csv"
        if not os.path.exists(shard_filename):
            with open(shard_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Type", "Value"])
            self._log_operation('create_shard', f'Shard {shard_number} created.')

    def compact_shard(self, shard_number: int):
        """Compacts a shard by removing unused space left by deleted records."""
        shard_filename = f"{self.filename}_shard_{shard_number}.csv"
        temp_filename = shard_filename + ".compact"
        with open(shard_filename, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = [row for row in reader if int(row[0]) >= 0]
        
        with open(temp_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        
        os.replace(temp_filename, shard_filename)
        self._log_operation('compact_shard', f'Shard {shard_number} compacted.')

    def encode(self, Y, D):
        """Encode a value using an arbitrary-precision approach to avoid overflow."""
        return (Y * (2**D)) + (2**(D-1))

    def decode(self, X, D):
        """Decode the value using an arbitrary-precision approach."""
        return (X - (2**(D-1))) // (2**D)

    def ith_permutation(self, n, k, i):
        elements = list(range(n))
        perm = []
        for _ in range(k):
            if not elements:
                break
            index = int(i % len(elements))
            perm.append(elements[index])
            elements.remove(elements[index])
            if not elements:
                break
            i //= len(elements)
        return sum(perm)

    def reverse_engineer_encoded_value(self, value, layer_depth, n, k, target_index, timings, sizes):
        """Reverse engineer the encoded value, starting from the highest level down to 0."""

        if layer_depth == 0:
            print(f"Base case reached at recursion level: {layer_depth}")
            return self.ith_permutation(n, k, value)

        # Adjust comparison based on the desired target_index
        comparison = (target_index >> (layer_depth - 1)) % 2  # Shift right to get the bit corresponding to the current layer depth
        if comparison == 0:
            original_value = value - layer_depth // 2  # For < comparison
            operator = "<"
        else:
            original_value = value - layer_depth // 2  # For > comparison
            operator = ">"

        # Recursively call for the next lower layer
        result = self.reverse_engineer_encoded_value(original_value, layer_depth - 1, n, k, target_index, timings, sizes)

        return result

    def _convert_record_to_bitstring(self, record: List[str]) -> Tuple[str, Dict]:
        """Convert a database record to a bitstring and store metadata for reverse conversion."""
        bitstring = ""
        metadata = {}

        for i, value in enumerate(record):
            if isinstance(value, int):
                binary = bin(value)[2:]  # Convert to binary and remove the '0b' prefix
                bitstring += binary
                metadata[i] = ("int", len(binary))  # Store type and length
            elif isinstance(value, float):
                binary = ''.join(format(c, '08b') for c in bytearray(struct.pack("f", value)))
                bitstring += binary
                metadata[i] = ("float", len(binary))
            elif isinstance(value, str):
                binary = ''.join(format(ord(c), '08b') for c in value)
                bitstring += binary
                metadata[i] = ("str", len(binary))
            # Add more types if necessary

        return bitstring, metadata

    def _convert_bitstring_to_record(self, bitstring: str, metadata: Dict) -> List[str]:
        """Convert a bitstring back to a database record using stored metadata."""
        record = []
        current_position = 0

        for i in range(len(metadata)):
            data_type, length = metadata[i]
            binary_segment = bitstring[current_position:current_position + length]
            if data_type == "int":
                value = int(binary_segment, 2)
            elif data_type == "float":
                value = struct.unpack("f", bytearray(int(binary_segment[i:i+8], 2) for i in range(0, length, 8)))[0]
            elif data_type == "str":
                value = ''.join(chr(int(binary_segment[i:i+8], 2)) for i in range(0, length, 8))
            record.append(value)
            current_position += length

        return record

    def _calculate_k(self) -> int:
        """Calculate the value of k based on the current number of items in the database."""
        total_items = self.insertion_count - self.deletion_count
        if total_items <= 0:
            raise ValueError("The database must have at least one item.")
        return math.ceil(math.log2(total_items))

    def insert(self, record: List[str]):
        """Insert a new record into the database."""
        try:
            with self.global_lock:
                with open(self.filename, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(record)
                    self.insertion_count += 1
                    self._log_operation('insert', f"Record inserted. Total records: {self.insertion_count - self.deletion_count}")
        except Exception as e:
            self._handle_error(f"Error inserting record: {str(e)}")
            raise

    def delete(self, criteria: Callable[[List[str]], bool]):
        """Delete records from the database based on a criteria function."""
        try:
            with self.global_lock:
                temp_filename = self.filename + '.tmp'
                with open(self.filename, 'r', newline='') as f, open(temp_filename, 'w', newline='') as temp_f:
                    reader = csv.reader(f)
                    writer = csv.writer(temp_f)
                    deleted_count = 0
                    for row in reader:
                        if not criteria(row):
                            writer.writerow(row)
                        else:
                            deleted_count += 1
                            self.deletion_count += 1
                    os.replace(temp_filename, self.filename)
                self._log_operation('delete', f"Deleted {deleted_count} records. Total records: {self.insertion_count - self.deletion_count}")
        except Exception as e:
            self._handle_error(f"Error deleting records: {str(e)}")
            raise

    def search(self, target_index: int = 0, generate_random_values: bool = True) -> List[List[str]]:
        """Searches for the nth encoded value in the database using the reverse engineering technique."""
        try:
            self._check_permission('read')
            results = []
            timings = {}
            sizes = {}

            n = 2  # Fixed value as per the requirement
            k = self._calculate_k()  # Dynamically calculate k based on the database size

            l = math.ceil(k * math.log2(n))

            with self.global_lock:
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header

                    bitstring_values = []
                    bitstring_metadata = []

                    # Convert each record to a bitstring and store metadata
                    for row in reader:
                        bitstring, metadata = self._convert_record_to_bitstring(row)
                        bitstring_values.append(int(bitstring, 2))
                        bitstring_metadata.append(metadata)

                    # Perform the reverse engineering search
                    nth_value = self.reverse_engineer_encoded_value(
                        sum(bitstring_values), l, n, k, target_index, timings, sizes
                    )

                    # Convert the found integer value back to a bitstring
                    max_bit_length = max(len(bin(b)[2:]) for b in bitstring_values)  # Find the max bit length
                    nth_bitstring = bin(nth_value)[2:].zfill(max_bit_length)  # Ensure it has the correct length

                    # Find the matching record using the bitstring
                    for idx, original_bitstring in enumerate(bitstring_values):
                        if original_bitstring == nth_value:
                            result_record = self._convert_bitstring_to_record(nth_bitstring, bitstring_metadata[idx])
                            results.append(result_record)
                            break

            return results

        except Exception as e:
            self._handle_error(f"Error searching records: {str(e)}")
            raise

    # Logging operation for consistency
    def _log_operation(self, operation: str, message: str):
        with open(self.log_filename, 'a', newline='') as log_file:
            writer = csv.writer(log_file)
            writer.writerow([datetime.now(), operation, message])

    # Permission check stub
    def _check_permission(self, operation: str):
        # Implement permission checking as needed
        pass

    # Error handling stub
    def _handle_error(self, message: str):
        print(message)

    def list_records(self) -> List[List[str]]:
        """Lists all records in the database."""
        try:
            self._check_permission('read')
            records = []
            with self.lock:
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    records = list(reader)
            self._log_operation('list_records', 'All records listed')
            return records
        except Exception as e:
            self._handle_error(f"Error listing records: {str(e)}")
            raise

    def create_index(self, field: str):
        """Creates an index on a specified field."""
        try:
            self._check_permission('write')
            if field not in ["ID", "Type", "Value"]:
                raise ValueError("Indexing is only supported on 'ID', 'Type', or 'Value' fields.")
            
            with self.lock:
                index = {}
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    for row in reader:
                        index_key = self._hash_value(row[2]) if field == "Value" else row[0]
                        index[index_key] = int(row[0])
                
                self.indexes[field] = index
                self._log_operation('create_index', f'Field: {field}')
        except Exception as e:
            self._handle_error(f"Error creating index: {str(e)}")
            raise

    def drop_index(self, field: str):
        """Drops an existing index."""
        try:
            self._check_permission('write')
            with self.lock:
                if field in self.indexes:
                    del self.indexes[field]
                    self._log_operation('drop_index', f'Field: {field}')
                else:
                    print(f"No index found on '{field}'.")
        except Exception as e:
            self._handle_error(f"Error dropping index: {str(e)}")
            raise

    def search_by_index(self, field: str, value: Union[str, float, int, list, tuple]) -> Union[List[str], None]:
        """Searches for a record using an existing index."""
        try:
            self._check_permission('read')
            bitstring_value = self._convert_to_bitstring(value)
            index_key = self._hash_value(bitstring_value) if field == "Value" else str(value)
            
            with self.lock:
                if field in self.indexes and index_key in self.indexes[field]:
                    record_id = self.indexes[field][index_key]
                    self._log_operation('search_by_index', f'Field: {field}, Value: {value}')
                    return self.query(record_id)
            
            return None
        except Exception as e:
            self._handle_error(f"Error searching by index: {str(e)}")
            raise

    def begin_transaction(self):
        """Begins a transaction, creating a temporary file for operations."""
        try:
            self._check_permission('write')
            with self.lock:
                if self.transaction_file:
                    raise Exception("Transaction already in progress.")
                self.transaction_file = self.filename + ".tmp"
                with open(self.transaction_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Type", "Value"])
                self._log_operation('begin_transaction', None)
        except Exception as e:
            self._handle_error(f"Error beginning transaction: {str(e)}")
            raise

    def commit_transaction(self):
        """Commits the transaction, applying all changes to the main database file."""
        try:
            self._check_permission('write')
            with self.lock:
                if not self.transaction_file:
                    raise Exception("No transaction in progress.")
                os.replace(self.transaction_file, self.filename)
                self.transaction_file = None
                self._log_operation('commit_transaction', None)
        except Exception as e:
            self._handle_error(f"Error committing transaction: {str(e)}")
            raise

    def rollback_transaction(self):
        """Rolls back the transaction, discarding all changes."""
        try:
            self._check_permission('write')
            with self.lock:
                if not self.transaction_file:
                    raise Exception("No transaction in progress.")
                os.remove(self.transaction_file)
                self.transaction_file = None
                self._log_operation('rollback_transaction', None)
        except Exception as e:
            self._handle_error(f"Error rolling back transaction: {str(e)}")
            raise

    def export_to_csv(self, export_filename: str):
        """Exports the database records to a CSV file."""
        try:
            self._check_permission('read')
            with self.lock:
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    rows = list(reader)
                
                with open(export_filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(rows)
                self._log_operation('export_to_csv', f'Filename: {export_filename}')
        except Exception as e:
            self._handle_error(f"Error exporting to CSV: {str(e)}")
            raise

    def import_from_csv(self, import_filename: str):
        """Imports records from a CSV file into the database."""
        try:
            self._check_permission('write')
            with self.lock:
                with open(import_filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    for row in reader:
                        self.insert(self._convert_from_bitstring(row[2], row[1]))
                self._log_operation('import_from_csv', f'Filename: {import_filename}')
        except Exception as e:
            self._handle_error(f"Error importing from CSV: {str(e)}")
            raise

    def export_to_json(self, export_filename: str):
        """Exports the database records to a JSON file."""
        try:
            self._check_permission('read')
            with self.lock:
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    records = []
                    for row in reader:
                        records.append(dict(zip(header, row)))
                
                with open(export_filename, 'w') as f:
                    json.dump(records, f, indent=4)
                self._log_operation('export_to_json', f'Filename: {export_filename}')
        except Exception as e:
            self._handle_error(f"Error exporting to JSON: {str(e)}")
            raise

    def import_from_json(self, import_filename: str):
        """Imports records from a JSON file into the database."""
        try:
            self._check_permission('write')
            with self.lock:
                with open(import_filename, 'r') as f:
                    records = json.load(f)
                    for record in records:
                        self.insert(self._convert_from_bitstring(record['Value'], record['Type']))
                self._log_operation('import_from_json', f'Filename: {import_filename}')
        except Exception as e:
            self._handle_error(f"Error importing from JSON: {str(e)}")
            raise

    def export_to_xml(self, export_filename: str):
        """Exports the database records to an XML file."""
        try:
            self._check_permission('read')
            with self.lock:
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    
                    root = ET.Element("Records")
                    for row in reader:
                        record_elem = ET.SubElement(root, "Record")
                        for key, value in zip(header, row):
                            child = ET.SubElement(record_elem, key)
                            child.text = value
                    
                tree = ET.ElementTree(root)
                tree.write(export_filename)
                self._log_operation('export_to_xml', f'Filename: {export_filename}')
        except Exception as e:
            self._handle_error(f"Error exporting to XML: {str(e)}")
            raise

    def import_from_xml(self, import_filename: str):
        """Imports records from an XML file into the database."""
        try:
            self._check_permission('write')
            with self.lock:
                tree = ET.parse(import_filename)
                root = tree.getroot()
                for record_elem in root.findall('Record'):
                    record = {}
                    for child in record_elem:
                        record[child.tag] = child.text
                    self.insert(self._convert_from_bitstring(record['Value'], record['Type']))
                self._log_operation('import_from_xml', f'Filename: {import_filename}')
        except Exception as e:
            self._handle_error(f"Error importing from XML: {str(e)}")
            raise

    def backup_database(self, backup_filename: str):
        """Creates a backup of the database."""
        try:
            self._check_permission('read')
            with self.lock:
                shutil.copyfile(self.filename, backup_filename)
                self._log_operation('backup_database', f'Backup Filename: {backup_filename}')
        except Exception as e:
            self._handle_error(f"Error backing up database: {str(e)}")
            raise

    def restore_database(self, backup_filename: str):
        """Restores the database from a backup file."""
        try:
            self._check_permission('write')
            with self.lock:
                shutil.copyfile(backup_filename, self.filename)
                self._log_operation('restore_database', f'Backup Filename: {backup_filename}')
        except Exception as e:
            self._handle_error(f"Error restoring database: {str(e)}")
            raise

    def compact_database(self):
        """Compacts the database by removing unused space left by deleted records."""
        try:
            self._check_permission('compact')
            with self.lock:
                temp_filename = self.filename + ".compact"
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    rows = [row for row in reader if int(row[0]) < self.counter - self.deletion_counter]
                
                with open(temp_filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(rows)
                
                os.replace(temp_filename, self.filename)
                self._log_operation('compact_database', None)
        except Exception as e:
            self._handle_error(f"Error compacting database: {str(e)}")
            raise

    def verify_integrity(self) -> bool:
        """Verifies the integrity of the database, checking for inconsistencies or corruption."""
        try:
            self._check_permission('verify')
            with self.lock:
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    for row in reader:
                        if len(row) != len(header):
                            self._log_operation('verify_integrity', 'Integrity check failed')
                            print(f"Integrity check failed: Row {row[0]} is corrupted.")
                            return False
                self._log_operation('verify_integrity', 'Integrity check passed')
                print("Integrity check passed: No issues found.")
                return True
        except Exception as e:
            self._handle_error(f"Error verifying database integrity: {str(e)}")
            return False

    def generate_report(self):
        """Generates a report with summary statistics of the database."""
        try:
            self._check_permission('report')
            with self.lock:
                record_count = 0
                type_count = defaultdict(int)
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    for row in reader:
                        record_count += 1
                        type_count[row[1]] += 1
                
                self._log_operation('generate_report', None)
                print(f"Database Report:")
                print(f"Total Records: {record_count}")
                for data_type, count in type_count.items():
                    print(f"Type '{data_type}': {count} records")
        except Exception as e:
            self._handle_error(f"Error generating report: {str(e)}")

    def get_count(self) -> int:
        """Returns the total number of entries minus deletions."""
        try:
            self._check_permission('read')
            with self.lock:
                return self.counter - self.deletion_counter
        except Exception as e:
            self._handle_error(f"Error getting count: {str(e)}")
            return -1

    def shard(self, shard_size: int) -> List[str]:
        """Shards the database into smaller CSV files, each with a maximum of `shard_size` entries."""
        try:
            self._check_permission('read')
            shards = []
            shard_counter = 0
            shard_filename = f"{self.filename}_shard_{shard_counter}.csv"
            
            with self.lock:
                with open(self.filename, 'r', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    
                    shard_data = []
                    for i, row in enumerate(reader):
                        if i > 0 and i % shard_size == 0:
                            # Write the current shard to a file
                            shard_filename = f"{self.filename}_shard_{shard_counter}.csv"
                            with open(shard_filename, 'w', newline='') as shard_file:
                                writer = csv.writer(shard_file)
                                writer.writerow(header)
                                writer.writerows(shard_data)
                            shards.append(shard_filename)
                            shard_counter += 1
                            shard_data = []
                        
                        shard_data.append(row)
                    
                    # Write the last shard if any data remains
                    if shard_data:
                        shard_filename = f"{self.filename}_shard_{shard_counter}.csv"
                        with open(shard_filename, 'w', newline='') as shard_file:
                            writer = csv.writer(shard_file)
                            writer.writerow(header)
                            writer.writerows(shard_data)
                        shards.append(shard_filename)
            
            self._log_operation('shard_database', f'Shard size: {shard_size}, Number of shards: {len(shards)}')
            return shards
        except Exception as e:
            self._handle_error(f"Error sharding database: {str(e)}")
            return []