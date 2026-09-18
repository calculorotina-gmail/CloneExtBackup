"""
Military-Grade AES-256-GCM Encryption Engine for Chrome Extension Backups.
Adheres strictly to requirement 18:
- Modern authenticated encryption: AES-256-GCM
- Secure key derivation: PBKDF2-HMAC-SHA256 with 100,000 iterations
- Cryptographic random 16-byte salt and 12-byte nonce
- Password never stored in plaintext
- Integrity validation during decryption (tamper detection)
- Informative error when decryption key/password is invalid
"""

import os
import hashlib
from typing import Tuple

MAGIC_HEADER = b"CRXENC01"
SALT_LEN = 16
NONCE_LEN = 12
PBKDF2_ITERATIONS = 100000


def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a 256-bit (32 bytes) encryption key from password and salt using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations=PBKDF2_ITERATIONS,
        dklen=32
    )


def is_file_encrypted(file_path: str) -> bool:
    """Checks whether the given file has the CRXENC01 magic header."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) < len(MAGIC_HEADER):
        return False
    try:
        with open(file_path, "rb") as f:
            header = f.read(len(MAGIC_HEADER))
            return header == MAGIC_HEADER
    except Exception:
        return False


def encrypt_file(source_path: str, target_encrypted_path: str, password: str) -> dict:
    """
    Encrypts source_path using AES-256-GCM and writes to target_encrypted_path.
    Format: [CRXENC01 (8b)] + [Salt (16b)] + [Nonce (12b)] + [AES-256-GCM Ciphertext + Tag]
    """
    if not password:
        raise ValueError("A palavra-passe de encriptação não pode ser vazia.")

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    with open(source_path, "rb") as f_in:
        plaintext = f_in.read()

    # Associated authenticated data includes the magic header
    ciphertext = aesgcm.encrypt(nonce, plaintext, MAGIC_HEADER)

    os.makedirs(os.path.dirname(os.path.abspath(target_encrypted_path)), exist_ok=True)
    with open(target_encrypted_path, "wb") as f_out:
        f_out.write(MAGIC_HEADER)
        f_out.write(salt)
        f_out.write(nonce)
        f_out.write(ciphertext)

    return {
        "success": True,
        "algorithm": "AES-256-GCM",
        "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": PBKDF2_ITERATIONS,
        "encrypted_size": os.path.getsize(target_encrypted_path)
    }


def decrypt_file(encrypted_path: str, target_decrypted_path: str, password: str) -> dict:
    """
    Decrypts an AES-256-GCM encrypted backup archive.
    Validates password and payload authenticity.
    """
    if not os.path.exists(encrypted_path):
        raise FileNotFoundError(f"Ficheiro encriptado não encontrado: {encrypted_path}")

    if not is_file_encrypted(encrypted_path):
        raise ValueError("O ficheiro fornecido não é um arquivo encriptado válido (cabeçalho CRXENC01 em falta).")

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    with open(encrypted_path, "rb") as f:
        header = f.read(len(MAGIC_HEADER))
        salt = f.read(SALT_LEN)
        nonce = f.read(NONCE_LEN)
        ciphertext = f.read()

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, MAGIC_HEADER)
    except InvalidTag:
        raise PermissionError("Palavra-passe incorreta ou ficheiro de backup corrompido/adulterado.")

    os.makedirs(os.path.dirname(os.path.abspath(target_decrypted_path)), exist_ok=True)
    with open(target_decrypted_path, "wb") as f_out:
        f_out.write(plaintext)

    return {
        "success": True,
        "decrypted_size": len(plaintext),
        "target_path": target_decrypted_path
    }
