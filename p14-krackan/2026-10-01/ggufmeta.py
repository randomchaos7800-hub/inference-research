import struct, sys
f = open(sys.argv[1], "rb")
assert f.read(4) == b"GGUF"
ver, = struct.unpack("<I", f.read(4)); f.read(8)
nkv, = struct.unpack("<Q", f.read(8))
def rs():
    n, = struct.unpack("<Q", f.read(8)); return f.read(n).decode("utf-8", "replace")
T = {0:"<B",1:"<b",2:"<H",3:"<h",4:"<I",5:"<i",6:"<f",7:"<?",10:"<Q",11:"<q",12:"<d"}
def rv(t):
    if t == 8: return rs()
    if t == 9:
        et, = struct.unpack("<I", f.read(4)); n, = struct.unpack("<Q", f.read(8))
        vals = [rv(et) for _ in range(n)]
        return vals[:4] + (["...(%d total)" % n] if n > 4 else [])
    s = T[t]; return struct.unpack(s, f.read(struct.calcsize(s)))[0]
want = ("context_length", "rope", "block_count", "expert", "embedding_length", "head_count")
print("gguf v%d, %d kv pairs" % (ver, nkv))
for _ in range(nkv):
    k = rs(); t, = struct.unpack("<I", f.read(4)); v = rv(t)
    if any(w in k for w in want): print("  %-46s %s" % (k, v))
