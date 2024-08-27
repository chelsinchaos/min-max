from Crypto.PublicKey import RSA

# Generate a new RSA key pair
key = RSA.generate(4096)

# Export the private key to a file
with open("private.pem", "wb") as private_file:
    private_file.write(key.export_key())

# Export the public key to a file
with open("public.pem", "wb") as public_file:
    public_file.write(key.publickey().export_key())

print("RSA keys generated and saved to 'private.pem' and 'public.pem'")
