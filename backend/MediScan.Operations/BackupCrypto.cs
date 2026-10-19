using System.Security.Cryptography;
using System.Text;

namespace MediScan.Operations;

// Streaming encrypt-then-MAC: independent HKDF-derived AES-256 and HMAC-SHA256 keys.
// Authentication covers the version, salt, IV and complete ciphertext before any decryption.
public static class BackupCrypto
{
    private static readonly byte[] Magic = Encoding.ASCII.GetBytes("MSCANB01");
    public static byte[] ReadKey(string? encoded)
    {
        try { var key = Convert.FromBase64String(encoded ?? ""); if (key.Length == 32) return key; }
        catch (FormatException) { }
        throw new ArgumentException("Provide a Base64-encoded random 32-byte backup key through the environment.");
    }

    public static void Encrypt(string path, byte[] key, Action<Stream> writePlaintext)
    {
        if (key.Length != 32) throw new ArgumentException("A 32-byte key is required.");
        var salt = RandomNumberGenerator.GetBytes(16); var iv = RandomNumberGenerator.GetBytes(16);
        var derived = HKDF.DeriveKey(HashAlgorithmName.SHA256, key, 64, salt, Magic);
        var created = false;
        try
        {
            using var output = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
            created = true;
            if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            var header = Magic.Concat(salt).Concat(iv).ToArray(); output.Write(header);
            using var mac = IncrementalHash.CreateHMAC(HashAlgorithmName.SHA256, derived.AsSpan(32, 32)); mac.AppendData(header);
            using var aes = Aes.Create(); aes.Key = derived.AsSpan(0, 32).ToArray(); aes.IV = iv; aes.Mode = CipherMode.CBC; aes.Padding = PaddingMode.PKCS7;
            using var authenticated = new MacWriter(output, mac);
            using (var encrypted = new CryptoStream(authenticated, aes.CreateEncryptor(), CryptoStreamMode.Write, leaveOpen: true))
            { writePlaintext(encrypted); encrypted.FlushFinalBlock(); }
            output.Write(mac.GetHashAndReset()); output.Flush(flushToDisk: true);
        }
        catch { if (created) File.Delete(path); throw; }
        finally { CryptographicOperations.ZeroMemory(derived); }
    }

    public static void DecryptTo(string source, string destination, byte[] key)
    {
        if (key.Length != 32) throw new ArgumentException("A 32-byte key is required.");
        using var input = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (input.Length < 88) throw new CryptographicException("Backup authentication failed.");
        var header = new byte[40]; input.ReadExactly(header);
        if (!header.AsSpan(0, 8).SequenceEqual(Magic)) throw new CryptographicException("Unsupported backup or authentication failure.");
        var derived = HKDF.DeriveKey(HashAlgorithmName.SHA256, key, 64, header.AsSpan(8, 16).ToArray(), Magic);
        var created = false;
        try
        {
            var length = input.Length - 40 - 32;
            if (length % 16 != 0) throw new CryptographicException("Backup authentication failed.");
            using var mac = IncrementalHash.CreateHMAC(HashAlgorithmName.SHA256, derived.AsSpan(32, 32)); mac.AppendData(header);
            var buffer = new byte[81920]; var remaining = length;
            while (remaining > 0) { var count = input.Read(buffer, 0, (int)Math.Min(buffer.Length, remaining)); if (count == 0) throw new EndOfStreamException(); mac.AppendData(buffer, 0, count); remaining -= count; }
            var tag = new byte[32]; input.ReadExactly(tag);
            if (!CryptographicOperations.FixedTimeEquals(mac.GetHashAndReset(), tag)) throw new CryptographicException("Backup authentication failed.");
            input.Position = 40;
            using var limited = new CipherReader(input, length);
            using var aes = Aes.Create(); aes.Key = derived.AsSpan(0, 32).ToArray(); aes.IV = header.AsSpan(24, 16).ToArray();
            aes.Mode = CipherMode.CBC; aes.Padding = PaddingMode.PKCS7;
            using var decrypted = new CryptoStream(limited, aes.CreateDecryptor(), CryptoStreamMode.Read);
            using var output = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None); created = true;
            if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(destination, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            decrypted.CopyTo(output); output.Flush(flushToDisk: true);
        }
        catch { if (created) File.Delete(destination); throw; }
        finally { CryptographicOperations.ZeroMemory(derived); }
    }

    private sealed class MacWriter(Stream output, IncrementalHash mac) : Stream
    {
        public override bool CanRead => false; public override bool CanSeek => false; public override bool CanWrite => true;
        public override long Length => throw new NotSupportedException(); public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override void Write(byte[] buffer, int offset, int count) { output.Write(buffer, offset, count); mac.AppendData(buffer, offset, count); }
        public override void Flush() => output.Flush(); public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException(); public override void SetLength(long value) => throw new NotSupportedException();
    }
    private sealed class CipherReader(Stream source, long length) : Stream
    {
        private long remaining = length;
        private readonly long totalLength = length;
        public override bool CanRead => true; public override bool CanSeek => false; public override bool CanWrite => false;
        public override long Length => totalLength; public override long Position { get => totalLength - remaining; set => throw new NotSupportedException(); }
        public override int Read(byte[] buffer, int offset, int count) { var read = source.Read(buffer, offset, (int)Math.Min(count, remaining)); remaining -= read; return read; }
        public override void Flush() { } public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException(); public override void SetLength(long value) => throw new NotSupportedException();
    }
}
