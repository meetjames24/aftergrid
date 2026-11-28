// Aftergrid USB Maker: content packs (Wikipedia, maps, AI models, ...) and the VAULT partition.
// The pack list is the OS's own catalog.json (published next to latest.json), so the installer
// and Aftergrid Control -> Download always offer the same things and put them in the same folders.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

class Pack {
    public string Id, Label; public double Gb = -1; public object[] Items;
    public override string ToString() { return Label; }

    public static List<Pack> Load(string url) {
        var root = (Dictionary<string, object>)Json(Net.GetString(url));
        var list = new List<Pack>();
        foreach (var kv in (Dictionary<string, object>)root["tiers"]) {
            var t = (Dictionary<string, object>)kv.Value;
            var p = new Pack { Id = kv.Key, Label = (string)t["label"], Items = (object[])t["items"] };
            var m = Regex.Match(p.Label, @"~\s*([\d.]+)\s*GB");          // labels carry the size: "(~3.6 GB)"
            if (m.Success) p.Gb = double.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
            list.Add(p);
        }
        Kiwix = root.ContainsKey("base_kiwix") ? (string)root["base_kiwix"] : "https://download.kiwix.org/zim";
        return list;
    }
    public static string Kiwix = "https://download.kiwix.org/zim";
    public bool Measured;
    // Real size from the servers (labels are approximate and go stale). Maps can't be measured cheaply.
    public void Measure() {
        long sum = 0;
        foreach (Dictionary<string, object> it in Items) {
            if ((string)it["type"] == "pmtiles") return;
            var j = Job.From(it, "V:\\"); long n = Net.Size(j.Url); if (n <= 0) return; sum += n;
        }
        Gb = sum / 1e9; Measured = true;
    }
    public static object Json(string s) { return new JavaScriptSerializer { MaxJsonLength = 1 << 26 }.DeserializeObject(s); }
}

static class Net {
    static Net() { ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; ServicePointManager.DefaultConnectionLimit = 8; }
    public const string UA = "AftergridUsbMaker/3";
    public static HttpWebRequest Req(string url) {
        var r = (HttpWebRequest)WebRequest.Create(url); r.UserAgent = UA; r.Timeout = 30000; r.ReadWriteTimeout = 60000; return r;
    }
    public static string GetString(string url) {
        using (var resp = (HttpWebResponse)Req(url).GetResponse()) using (var rd = new StreamReader(resp.GetResponseStream())) return rd.ReadToEnd();
    }
    public static long Size(string url) {
        try { var r = Req(url); r.Method = "HEAD"; using (var resp = (HttpWebResponse)r.GetResponse()) return resp.ContentLength; } catch { return 0; }
    }
    // Resumable download to path (via path.part). progress(doneBytes, totalBytes).
    public static void Download(string url, string path, Action<long, long> progress) {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        if (File.Exists(path)) return;
        var part = path + ".part";
        for (int tries = 0; ; tries++) {
            try {
                long have = File.Exists(part) ? new FileInfo(part).Length : 0;
                var rq = Req(url); if (have > 0) rq.AddRange(have);
                using (var resp = (HttpWebResponse)rq.GetResponse()) {
                    if (have > 0 && resp.StatusCode != HttpStatusCode.PartialContent) have = 0;
                    long total = resp.ContentLength + have;
                    using (var src = resp.GetResponseStream())
                    using (var dst = new FileStream(part, have > 0 ? FileMode.Append : FileMode.Create, FileAccess.Write, FileShare.None, 1 << 20)) {
                        var buf = new byte[1 << 20]; int n; long done = have; var sw = Stopwatch.StartNew();
                        while ((n = src.Read(buf, 0, buf.Length)) > 0) {
                            dst.Write(buf, 0, n); done += n;
                            if (sw.ElapsedMilliseconds > 400) { progress(done, total); sw.Restart(); }
                        }
                    }
                }
                File.Move(part, path); return;
            } catch (Exception ex) {
                if (ex is IOException && ex.Message.Contains("space")) throw new Exception("The VAULT is full.");
                if (tries >= 8) throw new Exception("Download kept failing: " + Path.GetFileName(path) + " (" + ex.Message + ")");
                System.Threading.Thread.Sleep(Math.Min(30000, 1000 << tries));
            }
        }
    }
}

// What gets fetched for one catalog item: a URL to a file, or a map cut out of the Protomaps world build.
class Job {
    public string Url, Dest, Title; public Dictionary<string, object> Map;
    static readonly Dictionary<string, string> listing = new Dictionary<string, string>();

    public static Job From(Dictionary<string, object> it, string vault) {
        var t = (string)it["type"];
        if (t == "kiwix") {
            string dir = (string)it["dir"], prefix = (string)it["prefix"];
            if (!listing.ContainsKey(dir)) listing[dir] = Net.GetString(Pack.Kiwix + "/" + dir + "/");
            var hits = Regex.Matches(listing[dir], "href=\"(" + Regex.Escape(prefix) + @"_(\d{4}-\d{2})\.zim)""").Cast<Match>()
                            .OrderBy(m => m.Groups[2].Value).ToList();
            if (hits.Count == 0) throw new Exception("No download found for " + prefix);
            var f = hits.Last().Groups[1].Value;
            return new Job { Url = Pack.Kiwix + "/" + dir + "/" + f, Dest = Path.Combine(vault, "zim", f), Title = f };
        }
        if (t == "hf") return new Job { Url = "https://huggingface.co/" + it["repo"] + "/resolve/main/" + it["file"],
                                        Dest = Path.Combine(vault, ((string)it["dest"]).Replace('/', '\\'), (string)it["file"]), Title = (string)it["file"] };
        if (t == "url") return new Job { Url = (string)it["url"], Dest = Path.Combine(vault, ((string)it["dest"]).Replace('/', '\\'), (string)it["name"]), Title = (string)it["name"] };
        if (t == "pmtiles") return new Job { Map = it, Dest = Path.Combine(vault, "maps", it["name"] + ".pmtiles"), Title = "map: " + it["name"] };
        throw new Exception("Unknown item type " + t);
    }

    public void Run(Action<string, double> report) {
        if (Map == null) { Net.Download(Url, Dest, (d, t) => report(Title + "   " + Drive.Gb(d) + " of " + Drive.Gb(t), t > 0 ? (double)d / t : 0)); return; }
        if (File.Exists(Dest)) return;
        report("Cutting " + Title + " out of the world map (can take a while)…", -1);
        var exe = PmtilesExe(); Directory.CreateDirectory(Path.GetDirectoryName(Dest));
        var args = string.Format("extract {0} \"{1}.part\" --bbox={2} --maxzoom={3}", LatestProtomaps(), Dest, Map["bbox"], Map["maxzoom"]);
        var p = Process.Start(new ProcessStartInfo(exe, args) { CreateNoWindow = true, UseShellExecute = false, RedirectStandardError = true, RedirectStandardOutput = true });
        p.OutputDataReceived += (s, e) => { };
        string err = p.StandardError.ReadToEnd(); p.WaitForExit();
        if (p.ExitCode != 0) throw new Exception("Map extract failed: " + err.Trim().Split('\n').Last());
        File.Move(Dest + ".part", Dest);
    }

    static string pmtiles;
    static string PmtilesExe() {                     // go-pmtiles (BSD-3), fetched once from its GitHub release
        if (pmtiles != null && File.Exists(pmtiles)) return pmtiles;
        var rel = Net.GetString("https://api.github.com/repos/protomaps/go-pmtiles/releases/latest");
        var m = Regex.Match(rel, "\"browser_download_url\"\\s*:\\s*\"([^\"]+_Windows_x86_64\\.zip)\"");
        if (!m.Success) throw new Exception("Couldn't find the map tool download.");
        var dir = Path.Combine(Path.GetTempPath(), "aftergrid-pmtiles"); Directory.CreateDirectory(dir);
        var zip = Path.Combine(dir, "pmtiles.zip"); if (File.Exists(zip)) File.Delete(zip);
        Net.Download(m.Groups[1].Value, zip, (a, b) => { });
        using (var z = ZipFile.OpenRead(zip)) {
            var e = z.Entries.First(x => x.Name.Equals("pmtiles.exe", StringComparison.OrdinalIgnoreCase));
            pmtiles = Path.Combine(dir, "pmtiles.exe"); if (File.Exists(pmtiles)) File.Delete(pmtiles); e.ExtractToFile(pmtiles);
        }
        File.Delete(zip); return pmtiles;
    }
    static string LatestProtomaps() {
        for (int i = 0; i < 15; i++) {
            var u = "https://build.protomaps.com/" + DateTime.UtcNow.AddDays(-i).ToString("yyyyMMdd") + ".pmtiles";
            if (Net.Size(u) > 0) return u;
        }
        throw new Exception("No recent Protomaps world map is reachable.");
    }
}

// Adds two partitions after the Aftergrid image: a blank partition reserved for encrypted saves
// (the OS encrypts it on first setup, see aftergrid-setup-stick) and the VAULT (exFAT, Windows-readable).
// Done by patching the image's first sector while it is written, so no extra raw write is needed later.
class StickLayout {
    public long SavesStart, SavesSectors, VaultStart, VaultSectors; public string Skip;
    public long VaultOffset { get { return VaultStart * 512; } }
    // Space kept for encrypted saves: 8/16/32 GB by stick size, but never more than a third of what's left after
    // the image, so a 16 GB stick still gets a VAULT big enough for the offline AI pack. (min 2 GB, MiB-aligned)
    public static long Reserve(long disk, long image) {
        long r = (disk < 40e9 ? 8L : disk < 100e9 ? 16L : 32L) << 30;
        r = Math.Min(r, Math.Max(2L << 30, (disk - image) / 3));
        return r / (1 << 20) * (1 << 20);
    }

    // GPT images (live-build's) get partitions 4+5 in the GPT, with the backup GPT moved to the end of
    // the stick; MBR images (Debian's official ISOs) get MBR entries 3+4. Same layout aftergrid-setup-stick makes.
    public bool Gpt; public long BackupOffset; public byte[] Backup;          // backup GPT, written at the end of the stick
    int slot; long diskSectors, lastUsable, entriesLba; int entries, entrySize, entrySectors;
    static long U64(byte[] b, int o) { return BitConverter.ToInt64(b, o); }
    static int U32(byte[] b, int o) { return BitConverter.ToInt32(b, o); }

    public static StickLayout Plan(byte[] b, long diskBytes, long imageBytes) {
        if (b[510] != 0x55 || b[511] != 0xAA) return new StickLayout { Skip = "the image has no partition table" };
        var L = new StickLayout { diskSectors = diskBytes / 512 };
        long lastEnd = (imageBytes + 511) / 512; int used = 0;
        for (int i = 0; i < 4; i++) if (b[446 + 16 * i + 4] == 0xEE) L.Gpt = true;
        if (L.Gpt) {
            if (System.Text.Encoding.ASCII.GetString(b, 512, 8) != "EFI PART") return new StickLayout { Skip = "GPT header missing" };
            L.entriesLba = U64(b, 512 + 72); L.entries = U32(b, 512 + 80); L.entrySize = U32(b, 512 + 84);
            if (L.entrySize != 128 || L.entriesLba * 512 + (long)L.entries * L.entrySize > b.Length) return new StickLayout { Skip = "unusual GPT" };
            for (int i = 0; i < L.entries; i++) {
                int o = (int)(L.entriesLba * 512) + i * L.entrySize; bool empty = true;
                for (int k = 0; k < 16; k++) if (b[o + k] != 0) { empty = false; break; }
                if (empty) continue;
                if (i != used) return new StickLayout { Skip = "unexpected partition layout" };
                used++; lastEnd = Math.Max(lastEnd, U64(b, o + 40) + 1);
            }
            if (used + 2 > L.entries) return new StickLayout { Skip = "no free partition slots" };
            L.entrySectors = (L.entries * L.entrySize + 511) / 512;
            L.lastUsable = L.diskSectors - 2 - L.entrySectors;              // backup entries + backup header at the very end
        } else {
            for (int i = 0; i < 4; i++) {
                int o = 446 + 16 * i; long start = BitConverter.ToUInt32(b, o + 8), n = BitConverter.ToUInt32(b, o + 12);
                if (n == 0) continue;
                if (i != used) return new StickLayout { Skip = "unexpected partition layout" };
                used++; lastEnd = Math.Max(lastEnd, start + n);
            }
            if (used > 2) return new StickLayout { Skip = "no free partition slots" };
            L.lastUsable = Math.Min(L.diskSectors - 1, uint.MaxValue);
        }
        const long A = 2048;                                     // 1 MiB alignment
        L.SavesStart = (lastEnd + A - 1) / A * A; L.SavesSectors = Reserve(diskBytes, imageBytes) / 512;
        L.VaultStart = L.SavesStart + L.SavesSectors;
        L.VaultSectors = (L.lastUsable + 1 - L.VaultStart) / A * A;
        if (L.VaultSectors * 512 < (2L << 30)) return new StickLayout { Skip = "the stick is too small for a VAULT (needs about " + Drive.Gb(imageBytes + (4L << 30)) + ")" };
        L.slot = used; return L;
    }

    public void Apply(byte[] b) {
        if (!Gpt) {
            Mbr(b, slot, 0x83, SavesStart, SavesSectors);        // Linux type: Windows leaves it alone
            Mbr(b, slot + 1, 0x07, VaultStart, VaultSectors);    // exFAT/NTFS type: Windows can format it
            return;
        }
        Gpe(b, slot, "0FC63DAF-8483-4772-8E79-3D69D8477DE4", SavesStart, SavesSectors, "Aftergrid saves");   // Linux filesystem
        Gpe(b, slot + 1, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", VaultStart, VaultSectors, "VAULT");         // Basic data
        int eo = (int)(entriesLba * 512), elen = entries * entrySize;
        uint ecrc = Crc32(b, eo, elen);
        // primary header (LBA 1): backup now at the end of the stick, usable space up to it
        BitConverter.GetBytes(diskSectors - 1).CopyTo(b, 512 + 32);
        BitConverter.GetBytes(lastUsable).CopyTo(b, 512 + 48);
        BitConverter.GetBytes(ecrc).CopyTo(b, 512 + 88);
        Seal(b, 512);
        // protective MBR covers the whole stick
        BitConverter.GetBytes((uint)Math.Min(diskSectors - 1, uint.MaxValue)).CopyTo(b, 446 + 12);
        // backup GPT: entries, then header (current = last sector, alternate = 1)
        Backup = new byte[(entrySectors + 1) * 512];
        Array.Copy(b, eo, Backup, 0, elen);
        int ho = entrySectors * 512; Array.Copy(b, 512, Backup, ho, 512);
        BitConverter.GetBytes(diskSectors - 1).CopyTo(Backup, ho + 24);
        BitConverter.GetBytes(1L).CopyTo(Backup, ho + 32);
        BitConverter.GetBytes(diskSectors - 1 - entrySectors).CopyTo(Backup, ho + 72);
        Seal(Backup, ho);
        BackupOffset = (diskSectors - 1 - entrySectors) * 512;
    }
    static void Seal(byte[] b, int h) {                       // recompute a GPT header's CRC
        int size = U32(b, h + 12); BitConverter.GetBytes(0u).CopyTo(b, h + 16);
        BitConverter.GetBytes(Crc32(b, h, size)).CopyTo(b, h + 16);
    }
    void Gpe(byte[] b, int i, string type, long start, long n, string name) {
        int o = (int)(entriesLba * 512) + i * entrySize; Array.Clear(b, o, entrySize);
        new Guid(type).ToByteArray().CopyTo(b, o); Guid.NewGuid().ToByteArray().CopyTo(b, o + 16);
        BitConverter.GetBytes(start).CopyTo(b, o + 32); BitConverter.GetBytes(start + n - 1).CopyTo(b, o + 40);
        var nm = System.Text.Encoding.Unicode.GetBytes(name); Array.Copy(nm, 0, b, o + 56, Math.Min(nm.Length, 72));
    }
    static void Mbr(byte[] m, int i, byte type, long start, long n) {
        int o = 446 + 16 * i;
        m[o] = 0; m[o + 1] = 0xFE; m[o + 2] = 0xFF; m[o + 3] = 0xFF; m[o + 4] = type; m[o + 5] = 0xFE; m[o + 6] = 0xFF; m[o + 7] = 0xFF;
        BitConverter.GetBytes((uint)start).CopyTo(m, o + 8); BitConverter.GetBytes((uint)n).CopyTo(m, o + 12);
    }
    static uint[] crcTable;
    static uint Crc32(byte[] b, int o, int n) {
        if (crcTable == null) { crcTable = new uint[256]; for (uint i = 0; i < 256; i++) { uint c = i; for (int k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xEDB88320 ^ (c >> 1) : c >> 1; crcTable[i] = c; } }
        uint crc = 0xFFFFFFFF; for (int i = o; i < o + n; i++) crc = crcTable[(crc ^ b[i]) & 0xFF] ^ (crc >> 8); return ~crc;
    }

    // Format the VAULT and give it a drive letter. Returns e.g. "E:\".
    public string FormatVault(int disk) {
        var ps = "$ErrorActionPreference='Stop'; Update-HostStorageCache; $p=$null; for($i=0;$i -lt 15 -and -not $p;$i++){ " +
                 "$p=Get-Partition -DiskNumber " + disk + " | ? { $_.Offset -eq " + VaultOffset + " }; if(-not $p){ Start-Sleep 1; Update-HostStorageCache } }; " +
                 "if(-not $p){ throw 'Windows does not see the new VAULT partition' }; " +
                 "$p | Format-Volume -FileSystem exFAT -NewFileSystemLabel VAULT -Force -Confirm:$false | Out-Null; " +
                 "$p=Get-Partition -DiskNumber " + disk + " | ? { $_.Offset -eq " + VaultOffset + " }; " +
                 "if(-not $p.DriveLetter -or [int][char]$p.DriveLetter -eq 0){ $p | Add-PartitionAccessPath -AssignDriveLetter; Start-Sleep 2; $p=Get-Partition -DiskNumber " + disk + " | ? { $_.Offset -eq " + VaultOffset + " } }; " +
                 "Write-Output $p.DriveLetter";
        var p = Process.Start(new ProcessStartInfo("powershell.exe", "-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"" + ps.Replace("\"", "\\\"") + "\"")
            { CreateNoWindow = true, UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true });
        string o = p.StandardOutput.ReadToEnd(), e = p.StandardError.ReadToEnd(); p.WaitForExit();
        var letter = o.Trim().Split('\n').Last().Trim();
        if (p.ExitCode != 0 || letter.Length != 1) throw new Exception("Couldn't format the VAULT: " + (e.Trim().Length > 0 ? e.Trim().Split('\n')[0] : o.Trim()));
        return letter + ":\\";
    }
}
