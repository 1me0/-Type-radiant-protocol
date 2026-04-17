#!/usr/bin/env python3
"""
Secure Vault with 5‑day Delay and Architect Approval
Uses AES‑256‑GCM (authenticated encryption) for maximum security.
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
from cryptography.hazmat.primitives import hashes

VAULT_DIR = ".vault"
REQUESTS_FILE = os.path.join(VAULT_DIR, "requests.json")


# ----------------------------------------------------------------------
# Initialisation
# ----------------------------------------------------------------------
def init():
    """Create the vault directory and requests file if they don't exist."""
    if not os.path.exists(VAULT_DIR):
        os.makedirs(VAULT_DIR)
    if not os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'w') as f:
            json.dump([], f)


# ----------------------------------------------------------------------
# Cryptographic helpers
# ----------------------------------------------------------------------
def derive_key(password: str, salt: bytes, iterations: int = 600_000) -> bytes:
    """Derive a 32‑byte AES key from a password using PBKDF2‑HMAC‑SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    return kdf.derive(password.encode())


def encrypt_file(file_path: str) -> None:
    """Encrypt a file using AES‑256‑GCM. Output is <file>.enc."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    password = getpass.getpass("Enter encryption password: ")
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = derive_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    with open(file_path, 'rb') as f:
        plaintext = f.read()

    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    tag = encryptor.tag

    # Format: salt (16) + iv (12) + tag (16) + ciphertext
    encrypted_data = salt + iv + tag + ciphertext
    output_file = file_path + ".enc"
    with open(output_file, 'wb') as f:
        f.write(encrypted_data)

    print(f"Encrypted to {output_file}")


def decrypt_file(enc_file: str) -> None:
    """Decrypt a .enc file if access is granted (architect approval or 5‑day delay)."""
    if not os.path.exists(enc_file):
        print(f"Error: File '{enc_file}' not found.")
        return

    # Check if decryption is allowed
    if not is_decryption_allowed(enc_file):
        return

    password = getpass.getpass("Enter encryption password: ")
    with open(enc_file, 'rb') as f:
        data = f.read()

    salt = data[:16]
    iv = data[16:28]
    tag = data[28:44]
    ciphertext = data[44:]

    key = derive_key(password, salt)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    try:
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        out_file = enc_file[:-4] if enc_file.endswith('.enc') else enc_file + '.dec'
        with open(out_file, 'wb') as f:
            f.write(plaintext)
        print(f"Decrypted to {out_file}")
    except Exception as e:
        print(f"Decryption failed (wrong password or corrupted file): {e}")


# ----------------------------------------------------------------------
# Access control (request / approval / delay)
# ----------------------------------------------------------------------
def request_access(enc_file: str) -> None:
    """Request permission to decrypt a file. Generates a request ID."""
    if not os.path.exists(enc_file):
        print(f"Error: File '{enc_file}' not found.")
        return

    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)

    # Check for existing pending request
    for req in requests:
        if req['file'] == enc_file and req['status'] == 'pending':
            print("Access already requested. Waiting for approval or 5 days.")
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


def approve_request(request_id: str) -> None:
    """Approve a pending request (architect action)."""
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


def is_decryption_allowed(enc_file: str) -> bool:
    """
    Check whether decryption of a file is allowed.
    If a request exists and is approved, returns True.
    If a request exists and is pending but the 5‑day delay has passed,
    automatically approves it and returns True.
    Otherwise prints a message and returns False.
    """
    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)

    for req in requests:
        if req['file'] == enc_file:
            if req['status'] == 'approved':
                return True
            elif req['status'] == 'pending':
                elapsed = time.time() - req['request_time']
                if elapsed >= 5 * 24 * 3600:
                    # Auto‑approve after 5 days
                    req['status'] = 'approved'
                    req['approved'] = True
                    req['architect_approval_time'] = time.time()
                    with open(REQUESTS_FILE, 'w') as f:
                        json.dump(requests, f, indent=2)
                    print("5‑day period elapsed. Decryption automatically allowed.")
                    return True
                else:
                    remaining = 5 * 24 * 3600 - elapsed
                    days = int(remaining // (24 * 3600))
                    hours = int((remaining % (24 * 3600)) // 3600)
                    print(f"Access not yet allowed. Wait {days} days {hours} hours (or architect approval).")
                    return False

    print("No access request found for this file. Please run 'request' first.")
    return False


def list_requests() -> None:
    """List all access requests with their status."""
    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)

    if not requests:
        print("No requests.")
        return

    for req in requests:
        status = "approved" if req['approved'] else "pending"
        print(f"{req['id']}: {req['file']} - {status}")


def status(enc_file: str) -> None:
    """Show the status of a specific file's access request."""
    init()
    with open(REQUESTS_FILE, 'r') as f:
        requests = json.load(f)

    for req in requests:
        if req['file'] == enc_file:
            if req['status'] == 'approved':
                print(f"Request approved (architect approved or delay passed).")
            else:
                elapsed = time.time() - req['request_time']
                remaining = 5 * 24 * 3600 - elapsed
                if remaining <= 0:
                    print("Request pending but already eligible (run decrypt).")
                else:
                    days = int(remaining // (24 * 3600))
                    hours = int((remaining % (24 * 3600)) // 3600)
                    print(f"Request pending. Auto‑approval in {days} days {hours} hours.")
            return
    print("No request found for this file.")


# ----------------------------------------------------------------------
# Command line interface
# ----------------------------------------------------------------------
def print_usage():
    print("""
Usage: vault.py <command> [arguments]

Commands:
  encrypt <file>          Encrypt a file (creates <file>.enc)
  request <file.enc>      Request access to decrypt a file
  approve <request_id>    Approve a pending request (architect)
  decrypt <file.enc>      Decrypt a file (if access granted)
  list                    List all access requests
  status <file.enc>       Show access status for a file

Note: All state is stored in the .vault/ directory.
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1].lower()

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
    elif cmd == "status" and len(sys.argv) == 3:
        status(sys.argv[2])
    elif cmd == "--help" or cmd == "-h":
        print_usage()
    else:
        print("Invalid command or missing arguments.")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
