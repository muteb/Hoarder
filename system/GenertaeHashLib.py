import hashlib


def generate_hash(datafile):
    md5 = hashlib.md5(datafile)
    sha1 = hashlib.sha1(datafile)
    sha256 = hashlib.sha256(datafile)

    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()
