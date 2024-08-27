import time
import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from database import FlatFileDatabase  # Import your database class

# Function to generate RSA key pairs if they don't exist
def generate_rsa_keypair():
    if not os.path.exists("private.pem") or not os.path.exists("public.pem"):
        print("Generating RSA key pair...")
        key = RSA.generate(2048)
        
        private_key = key.export_key()
        with open("private.pem", "wb") as priv_file:
            priv_file.write(private_key)

        public_key = key.publickey().export_key()
        with open("public.pem", "wb") as pub_file:
            pub_file.write(public_key)
        
        print("RSA key pair generated and saved as private.pem and public.pem.")
    else:
        print("RSA key pair already exists.")

# Initialize database
def initialize_database():
    db = FlatFileDatabase('my_flatfile_db.csv')
    return db

def create_user():
    start_time = time.time_ns()
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key()

    cipher = PKCS1_OAEP.new(key)
    encrypted_private_key = cipher.encrypt(private_key)

    end_time = time.time_ns()
    print(f"User creation took {end_time - start_time} ns")
    return public_key, encrypted_private_key

def create_database(db):
    start_time = time.time_ns()
    db.create_database()  # Correct method for creating the database
    end_time = time.time_ns()
    print(f"Database creation took {end_time - start_time} ns")

def insert_dummy_data(db):
    start_time = time.time_ns()
    dummy_records = [["1", "int", "123"], ["2", "str", "test"], ["3", "float", "45.67"]]  # Sample records
    for record in dummy_records:
        encoded_record, metadata = db._convert_record_to_bitstring(record)
        db.insert([encoded_record, metadata])  # Store encoded record and metadata
    end_time = time.time_ns()
    print(f"Inserting dummy data took {end_time - start_time} ns")

def ith_search_function(db, index):
    start_time = time.time_ns()
    result = db.search(target_index=index)  # Use the search function to retrieve a record
    
    if result:
        encoded_record, metadata = result[0]  # Assuming the result returns a list with encoded record and metadata
        record = db._convert_bitstring_to_record(encoded_record, metadata)  # Decode the record
    else:
        record = []

    end_time = time.time_ns()
    print(f"Searching for record {index} took {end_time - start_time} ns")
    return record

def main():
    total_start_time = time.time_ns()
    
    # Generate RSA key pairs if needed
    generate_rsa_keypair()
    
    # Initialize database
    db = initialize_database()
    
    print("Creating database...")
    create_database(db)
    
    print("Inserting dummy data...")
    insert_dummy_data(db)
    
    print("Searching for the 1st record...")
    record = ith_search_function(db, 0)
    
    total_end_time = time.time_ns()
    print(f"Total execution time: {total_end_time - total_start_time} ns")
    print(f"Record found: {record}")

if __name__ == "__main__":
    main()
