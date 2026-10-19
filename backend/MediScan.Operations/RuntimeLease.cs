namespace MediScan.Operations;

public sealed class RuntimeLease : IDisposable
{
    private readonly FileStream stream;
    private RuntimeLease(string root, bool maintenance)
    {
        var path = Path.Combine(Path.GetFullPath(root), ".auth", "runtime.lock");
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        if (!File.Exists(path))
        {
            try { using var created = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.ReadWrite); }
            catch (IOException) when (File.Exists(path)) { }
        }
        try { stream = new FileStream(path, FileMode.Open, maintenance ? FileAccess.ReadWrite : FileAccess.Read, maintenance ? FileShare.None : FileShare.Read); }
        catch (IOException) { throw new InvalidOperationException("API workers and backup/restore maintenance cannot run on this host simultaneously."); }
    }
    public static RuntimeLease Shared(string root) => new(root, false);
    public static RuntimeLease Maintenance(string root) => new(root, true);
    public void Dispose() => stream.Dispose();
}
