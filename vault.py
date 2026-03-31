#!/usr/bin/env python3
"""
Secure Vault with 5‑day Delay and Architect Approval

Encrypt sensitive files, request access, and enforce a 5‑day waiting period
(or architect override). Decryption only after conditions are met.

Usage:
    ./vault.py encrypt <file>          # Encrypt file to <file>.enc
    ./vault.py request <file.enc>      # Request access (starts timer)
    ./vault.py approve <request_id>    # Architect approves early
    ./vault.py decrypt <file.enc>      # Decrypt after approval/5 days
    ./vault.py list                    # List all requests
"""

import os
import sys
import json
import time
import getpass
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

VAULT_DIR = ".vault"
REQUESTS_FILE = os.path.join(VAULT_DIR, "requests.json")

def init():
    if not os.path.exists(VAULT_DIR):
        os.makedirs(VAULT_DIR)
    if not os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'w') as f:
            json.dump([], f)

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_file(file_path):
    if not os.path.exists(file_path):
        print("File not found.")
        return
    password = getpass.getpass("Enter encryption password: ")
    salt = os.urandom(16)
    key = derive_key(password, salt)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    with open(file_path, 'rb') as f:
        plaintext = f.read()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    encrypted_data = salt + iv + ciphertext
    output_file = file_path + ".enc"
    with open(output_file, 'wb') as f:
        f.write(encrypted_data)
    print(f"Encrypted to {output_file}")

def request_access(enc_file):
    if not os.path.exists(enc_file):
        print("Encrypted file not found.")
        return
    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)
    for req in requests:
        if req['file'] == enc_file and req['status'] == 'pending':
            print("Access already requested. Waiting approval or 5 days.")
            return
    request_id = hashlib.sha256(f"{enc_file}{time.time()}".encode()).hexdigest()[:8]
    requests.append({
        'id': request_id,
        'file': enc_file,
        'request_time': time.time(),
        'status': 'pending',
        'approved': False,
        'architect_approval_time': None
    })
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests, f, indent=2)
    print(f"Request created. ID: {request_id}")
    print("Waiting for architect approval or 5 days.")

def approve_request(request_id):
    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)
    for req in requests:
        if req['id'] == request_id and req['status'] == 'pending':
            req['status'] = 'approved'
            req['architect_approval_time'] = time.time()
            req['approved'] = True
            with open(REQUESTS_FILE, 'w') as f:
                json.dump(requests, f, indent=2)
            print(f"Request {request_id} approved. Decryption now allowed.")
            return
    print("Request not found or already processed.")

def can_decrypt(enc_file):
    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)
    for req in requests:
        if req['file'] == enc_file:
            if req['status'] == 'approved':
                return True
            elif req['status'] == 'pending':
                if time.time() - req['request_time'] >= 5 * 24 * 3600:
                    req['status'] = 'approved'
                    req['approved'] = True
                    req['architect_approval_time'] = time.time()
                    with open(REQUESTS_FILE, 'w') as f:
                        json.dump(requests, f, indent=2)
                    return True
                else:
                    remaining = 5 * 24 * 3600 - (time.time() - req['request_time'])
                    days = remaining // (24*3600)
                    hours = (remaining % (24*3600)) // 3600
                    print(f"Access not yet allowed. Wait {days} days {hours} hours (or architect approval).")
                    return False
    print("No access request for this file. Please request first.")
    return False

def decrypt_file(enc_file):
    if not can_decrypt(enc_file):
        return
    password = getpass.getpass("Enter encryption password: ")
    with open(enc_file, 'rb') as f:
        data = f.read()
    salt = data[:16]
    iv = data[16:32]
    ciphertext = data[32:]
    key = derive_key(password, salt)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    try:
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        out_file = enc_file[:-4] if enc_file.endswith('.enc') else enc_file + '.dec'
        with open(out_file, 'wb') as f:
            f.write(plaintext)
        print(f"Decrypted to {out_file}")
    except Exception:
        print("Decryption failed (wrong password or corrupted file).")

def list_requests():
    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)
    for req in requests:
        status = "approved" if req['approved'] else "pending"
        print(f"{req['id']}: {req['file']} - {status}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: vault.py [encrypt|request|approve|decrypt|list] [file]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "encrypt" and len(sys.argv) == 3:
        encrypt_file(sys.argv[2])
    elif cmd == "request" and len(sys.argv) == 3:
        request_access(sys.argv[2])
    elif cmd == "approve" and len(sys.argv) == 3:
        approve_request(sys.argv[2])
    elif cmd == "decrypt" and len(sys.argv) == 3:
        decrypt_file(sys.argv[2])
    elif cmd == "list":
        list_requests()
    else:
        print("Invalid command or missing arguments.")
