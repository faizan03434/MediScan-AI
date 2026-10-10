using System.Text.RegularExpressions;

namespace MediScan.API.Services;

// A literal server-only dotenv reader: no interpolation, shell execution or secret logging.
public static class EnvFileConfiguration
{
    public static Dictionary<string, string?> Read(string path)
    {
        var result = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
        if (!File.Exists(path)) return result;
        var number = 0;
        foreach (var raw in File.ReadLines(path))
        {
            number++;
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;
            var separator = line.IndexOf('=');
            var key = separator < 0 ? "" : line[..separator].Trim();
            if (!Regex.IsMatch(key, "^[A-Za-z_][A-Za-z0-9_]*$"))
                throw new InvalidOperationException($"Invalid server .env syntax at line {number}.");
            var value = line[(separator + 1)..].Trim();
            if (value.StartsWith('"') || value.StartsWith('\''))
            {
                if (value.Length < 2 || value[^1] != value[0])
                    throw new InvalidOperationException($"Unclosed server .env quote at line {number}.");
                value = value[1..^1];
            }
            key = key.Replace("__", ":");
            if (!result.TryAdd(key, value))
                throw new InvalidOperationException($"Duplicate server .env key at line {number}.");
        }
        return result;
    }
}
