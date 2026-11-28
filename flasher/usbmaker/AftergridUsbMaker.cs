// Aftergrid USB Maker: writes the Aftergrid image to a USB stick on Windows and verifies it.
// Build (any OS with Mono):  mcs -target:winexe -win32icon:aftergrid.ico -r:System.Windows.Forms.dll -r:System.Drawing.dll
//                             -r:System.Management.dll -r:System.Web.Extensions.dll -r:System.IO.Compression.dll
//                             -r:System.IO.Compression.FileSystem.dll -out:"Aftergrid USB Maker.exe" AftergridUsbMaker.cs Packs.cs
// (see .github/workflows/release.yml for the exact command)
// Runs on Windows 10/11 with the built-in .NET Framework 4.x. Restarts itself as administrator.
//
// Image, in this order:
//   1. next to the .exe: aftergrid-image.json + its .part files, or a single Aftergrid*.iso (+ .sha256)
//   2. otherwise ONE-FILE MODE: download the edition catalog (CatalogUrl, or the URL in
//      aftergrid-catalog.txt next to the .exe, or the first command-line argument) and stream the
//      chosen edition's parts from the web straight onto the stick. No temporary disk space needed;
//      dropped connections resume where they stopped; every byte is fingerprint-checked.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Management;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;
using System.Net;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32.SafeHandles;

static class Native {
    public const uint GENERIC_READ = 0x80000000, GENERIC_WRITE = 0x40000000, FILE_SHARE_READ = 1, FILE_SHARE_WRITE = 2, OPEN_EXISTING = 3;
    public const uint FILE_FLAG_NO_BUFFERING = 0x20000000, FILE_FLAG_WRITE_THROUGH = 0x80000000;
    public const uint MEM_COMMIT = 0x1000, MEM_RESERVE = 0x2000, MEM_RELEASE = 0x8000, PAGE_READWRITE = 4;
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern SafeFileHandle CreateFile(string name, uint access, uint share, IntPtr sec, uint disp, uint flags, IntPtr tmpl);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool WriteFile(SafeFileHandle h, IntPtr buf, uint n, out uint written, IntPtr ovl);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool ReadFile(SafeFileHandle h, IntPtr buf, uint n, out uint read, IntPtr ovl);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool SetFilePointerEx(SafeFileHandle h, long dist, out long newPos, uint method);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool FlushFileBuffers(SafeFileHandle h);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern IntPtr VirtualAlloc(IntPtr addr, UIntPtr size, uint type, uint protect);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool VirtualFree(IntPtr addr, UIntPtr size, uint type);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}

class Drive {
    public int Index; public string Model; public long Size; public string Iface; public string Letters;
    public override string ToString() {
        return string.Format("{0}   {1}   ({2})   Disk {3}", Letters == "" ? "(no letter)" : Letters, Gb(Size), Model, Index);
    }
    public static string Gb(long b) { return (b / 1e9).ToString("0.0") + " GB"; }
}

class Image {
    public string Name; public long Size; public string Sha256; public List<string> Files = new List<string>();
    public string Title; public bool Remote;     // Remote: Files are URLs
    public override string ToString() { return (Title ?? Name) + "   (" + Drive.Gb(Size) + ")"; }

    public const string CatalogUrl = "https://github.com/Meet-James-App-Dev/aftergrid-os/releases/latest/download/latest.json";
    // Catalog: {"editions":[{"id","title","name","size","sha256","parts":[{"url"}]}]}; part URLs may be relative to the catalog.
    public static List<Image> Catalog(string url) {
        ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072;   // TLS 1.2 on .NET 4.x
        // Follow redirects (getaftergrid.com -> GitHub Releases) and resolve part URLs against where we landed.
        string j; Uri baseUri;
        var rq = (HttpWebRequest)WebRequest.Create(url); rq.UserAgent = "AftergridUsbMaker/2"; rq.Timeout = 30000;
        using (var resp = (HttpWebResponse)rq.GetResponse()) using (var rd = new StreamReader(resp.GetResponseStream())) { j = rd.ReadToEnd(); baseUri = resp.ResponseUri; }
        var root = (Dictionary<string, object>)new JavaScriptSerializer { MaxJsonLength = 1 << 24 }.DeserializeObject(j);
        var list = new List<Image>();
        foreach (Dictionary<string, object> e in (object[])root["editions"]) {
            var img = new Image { Remote = true, Name = (string)e["name"], Title = e.ContainsKey("title") ? (string)e["title"] : null,
                                  Size = Convert.ToInt64(e["size"]), Sha256 = ((string)e["sha256"]).ToUpperInvariant() };
            foreach (Dictionary<string, object> pt in (object[])e["parts"]) img.Files.Add(new Uri(baseUri, (string)pt["url"]).AbsoluteUri);
            list.Add(img);
        }
        return list;
    }
    public static Image Find(string dir) {
        var man = Path.Combine(dir, "aftergrid-image.json");
        if (File.Exists(man)) {
            var j = File.ReadAllText(man);
            var img = new Image();
            img.Name = Str(j, "name"); img.Sha256 = Str(j, "sha256").ToUpperInvariant();
            foreach (Match m in Regex.Matches(j, "\"file\"\\s*:\\s*\"([^\"]+)\"")) img.Files.Add(Path.Combine(dir, m.Groups[1].Value));
            foreach (var f in img.Files) if (!File.Exists(f)) throw new Exception("Missing part: " + Path.GetFileName(f) + "\nKeep all the .part files in the same folder as this program.");
            img.Size = img.Files.Sum(f => new FileInfo(f).Length);
            long want = long.Parse(Str(j, "size"));
            if (img.Size != want) throw new Exception("The image parts add up to " + img.Size + " bytes, expected " + want + ". A part may be incomplete: download it again.");
            return img;
        }
        var iso = Directory.GetFiles(dir, "*.iso").OrderByDescending(f => new FileInfo(f).Length).FirstOrDefault();
        if (iso != null) {
            var img = new Image(); img.Name = Path.GetFileName(iso); img.Files.Add(iso); img.Size = new FileInfo(iso).Length;
            var sha = iso + ".sha256";
            if (File.Exists(sha)) img.Sha256 = File.ReadAllText(sha).Trim().Split(new[]{' '})[0].ToUpperInvariant();
            return img;
        }
        return null;
    }
    static string Str(string json, string key) {
        var m = Regex.Match(json, "\"" + key + "\"\\s*:\\s*\"?([^\",}]+)\"?");
        return m.Success ? m.Groups[1].Value.Trim() : "";
    }
}

class MainForm : Form {
    static readonly Color Paper = Color.FromArgb(21, 23, 26), Ink = Color.FromArgb(233, 231, 225), Dim = Color.FromArgb(162, 158, 149), Field = Color.FromArgb(31, 35, 39);
    static readonly Color Amber = Color.FromArgb(242, 163, 58), Red = Color.FromArgb(194, 64, 44), Green = Color.FromArgb(47, 138, 87);
    ComboBox drives = new ComboBox(), editions = new ComboBox(); Button refresh = new Button(), make = new Button();
    Label imageInfo = new Label(), status = new Label(), detail = new Label(), packInfo = new Label();
    CheckedListBox packs = new CheckedListBox(); List<Pack> chosen = new List<Pack>(); string summary;
    ProgressBar bar = new ProgressBar(); BackgroundWorker worker = new BackgroundWorker();
    Image image; string baseDir = AppDomain.CurrentDomain.BaseDirectory;
    const int Block = 4 << 20;   // 4 MiB

    public MainForm() {
        Text = "Aftergrid USB Maker"; BackColor = Paper; ForeColor = Ink; Font = new Font("Segoe UI", 10f);
        FormBorderStyle = FormBorderStyle.FixedSingle; MaximizeBox = false; StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(620, 720); AutoScaleMode = AutoScaleMode.Dpi;
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }

        var logo = new MarkPanel { Location = new Point(28, 24), Size = new Size(44, 44) };
        var title = new Label { Text = "AFTERGRID", Font = new Font("Segoe UI Black", 20f), Location = new Point(82, 22), AutoSize = true };
        var sub = new Label { Text = "USB Maker: puts Aftergrid on a USB stick so any PC can start from it.", ForeColor = Dim, Location = new Point(84, 58), AutoSize = true };
        var l1 = Step("1", "Plug in a USB stick (16 GB or larger). Everything on it will be erased.", 104);
        drives.DropDownStyle = ComboBoxStyle.DropDownList; drives.Location = new Point(60, 136); drives.Size = new Size(420, 28);
        refresh.Text = "Refresh"; refresh.Location = new Point(490, 135); refresh.Size = new Size(96, 30); refresh.FlatStyle = FlatStyle.System;
        var l2 = Step("2", "Aftergrid edition:", 186);
        editions.DropDownStyle = ComboBoxStyle.DropDownList; editions.Location = new Point(60, 214); editions.Size = new Size(526, 28); editions.Visible = false;
        editions.SelectedIndexChanged += (s, e) => { image = editions.SelectedItem as Image; if (image != null) imageInfo.Text = "Downloads " + Drive.Gb(image.Size) + " while writing (no extra disk space needed). Internet must stay on."; };
        imageInfo.Location = new Point(60, 214); imageInfo.Size = new Size(530, 40); imageInfo.ForeColor = Dim;
        foreach (var c in new Control[] { drives, editions }) { c.BackColor = Field; c.ForeColor = Ink; }
        var l3 = Step("3", "Add to the stick (optional, downloaded for you, added to Aftergrid's VAULT):", 290);
        packs.Location = new Point(60, 320); packs.Size = new Size(526, 172); packs.CheckOnClick = true; packs.BorderStyle = BorderStyle.FixedSingle;
        packs.BackColor = Field; packs.ForeColor = Ink; packs.IntegralHeight = false;
        packs.ItemCheck += (s, e) => BeginInvoke((Action)UpdatePackInfo);
        packInfo.Location = new Point(60, 496); packInfo.Size = new Size(530, 40); packInfo.ForeColor = Dim; packInfo.Text = "Looking up packs…";
        drives.SelectedIndexChanged += (s, e) => UpdatePackInfo();
        var l4 = Step("4", "Make the stick (writes, checks every byte, then adds your packs).", 546);
        make.Text = "Make Aftergrid USB"; make.Cursor = Cursors.Hand; make.Location = new Point(60, 576); make.Size = new Size(220, 40);
        make.FlatStyle = FlatStyle.Flat; make.BackColor = Amber; make.ForeColor = Color.FromArgb(42, 26, 4); make.Font = new Font("Segoe UI Semibold", 11f);
        make.FlatAppearance.BorderSize = 0;
        bar.Location = new Point(300, 588); bar.Size = new Size(286, 18); bar.Maximum = 1000;
        status.Location = new Point(60, 626); status.Size = new Size(526, 22); status.Font = new Font("Segoe UI Semibold", 10f);
        detail.Location = new Point(60, 650); detail.Size = new Size(540, 66); detail.ForeColor = Dim;
        Controls.AddRange(new Control[] { logo, title, sub, l1, drives, refresh, l2, editions, imageInfo, l3, packs, packInfo, l4, make, bar, status, detail });

        refresh.Click += (s, e) => LoadDrives();
        make.Click += (s, e) => Start();
        worker.WorkerReportsProgress = true; worker.DoWork += Work; worker.ProgressChanged += Progress; worker.RunWorkerCompleted += Done;
        Load += (s, e) => { LoadImage(); LoadDrives(); LoadPacks(); };
    }

    Label Step(string n, string text, int y) {
        var p = new Label { Text = n, TextAlign = ContentAlignment.MiddleCenter, BackColor = Amber, ForeColor = Color.White, Font = new Font("Segoe UI Black", 10f), Location = new Point(28, y), Size = new Size(24, 24) };
        Controls.Add(p);
        return new Label { Text = text, Location = new Point(60, y + 2), AutoSize = true, Font = new Font("Segoe UI Semibold", 10f) };
    }

    void LoadImage() {
        try {
            image = Image.Find(baseDir);
            if (image == null) { LoadCatalog(); return; }
            imageInfo.Text = image.Name + "   " + Drive.Gb(image.Size) + (image.Files.Count > 1 ? "   (" + image.Files.Count + " parts)" : "") + (image.Sha256 != null ? "\nFingerprint " + image.Sha256.Substring(0, 16) + "… (checked after writing)" : "");
        } catch (Exception ex) { imageInfo.Text = ex.Message; imageInfo.ForeColor = Red; image = null; }
    }

    string CatalogUrl() {
        var url = Image.CatalogUrl; var f = Path.Combine(baseDir, "aftergrid-catalog.txt");
        if (Environment.GetCommandLineArgs().Length > 1) url = Environment.GetCommandLineArgs()[1];
        else if (File.Exists(f)) url = File.ReadAllText(f).Trim();
        return url;
    }

    // Packs: the OS's catalog.json, published next to latest.json.
    void LoadPacks() {
        var url = new Uri(new Uri(CatalogUrl()), "catalog.json").AbsoluteUri;
        var bw = new BackgroundWorker();
        bw.DoWork += (s, e) => e.Result = Pack.Load(url);
        bw.RunWorkerCompleted += (s, e) => {
            if (e.Error != null) { packs.Enabled = false; packInfo.Text = "Packs need internet. You can also add them later: Aftergrid Control → Download."; return; }
            var list = (List<Pack>)e.Result;
            foreach (var p in list) packs.Items.Add(p, p.Id == "ai");      // the offline AI is ticked by default
            UpdatePackInfo();
            var m = new BackgroundWorker();                                // then measure the real sizes quietly
            m.DoWork += (s2, e2) => { foreach (var p in list) { try { p.Measure(); } catch { } } };
            m.RunWorkerCompleted += (s2, e2) => UpdatePackInfo();
            m.RunWorkerAsync();
        };
        bw.RunWorkerAsync();
    }

    void UpdatePackInfo() {
        chosen = packs.CheckedItems.Cast<Pack>().ToList();
        var d = drives.SelectedItem as Drive; double gb = chosen.Where(p => p.Gb > 0).Sum(p => p.Gb);
        string sizes = chosen.Count == 0 ? "Nothing ticked: you can add packs later in Aftergrid Control → Download." :
            chosen.Count + " pack(s), " + (chosen.All(p => p.Measured || p.Gb <= 0) ? "" : "about ") + gb.ToString("0.#") + " GB" + (chosen.Any(p => p.Gb <= 0) ? " + maps (size varies)" : "") + ".";
        if (d != null && image != null) {
            double free = (d.Size - image.Size - StickLayout.Reserve(d.Size)) / 1e9;
            sizes += "  Room on this stick: about " + Math.Max(0, free).ToString("0") + " GB.";
            packInfo.ForeColor = gb > free ? Red : Dim;
            if (gb > free) sizes += "  Too much for this stick.";
        } else packInfo.ForeColor = Dim;
        packInfo.Text = sizes;
    }

    void LoadCatalog() {
        var url = CatalogUrl();
        imageInfo.Text = "Looking up Aftergrid editions online…"; imageInfo.ForeColor = Dim;
        var bw = new BackgroundWorker();
        bw.DoWork += (s, e) => e.Result = Image.Catalog(url);
        bw.RunWorkerCompleted += (s, e) => {
            if (e.Error != null) { imageInfo.ForeColor = Red; imageInfo.Text = "Couldn't reach " + new Uri(url).Host + ". Connect to the internet and restart this program, or put a downloaded Aftergrid image next to it."; return; }
            var list = (List<Image>)e.Result; editions.Items.Clear(); foreach (var i in list) editions.Items.Add(i);
            if (list.Count == 0) { imageInfo.ForeColor = Red; imageInfo.Text = "No editions are published yet."; return; }
            editions.Visible = true; imageInfo.Top = 246; imageInfo.Height = 40; editions.SelectedIndex = list.Count - 1; UpdatePackInfo();
        };
        bw.RunWorkerAsync();
    }

    void LoadDrives() {
        drives.Items.Clear();
        int system = SystemDisk();
        var seen = new HashSet<int>();
        // Primary: Windows Storage API knows the real bus type (USB sticks behind UASP report "SCSI" to Win32_DiskDrive).
        try {
            using (var q = new ManagementObjectSearcher(@"root\Microsoft\Windows\Storage", "SELECT Number, BusType, Size, FriendlyName, IsBoot, IsSystem FROM MSFT_Disk"))
            foreach (ManagementObject d in q.Get()) {
                int bus = Convert.ToInt32(d["BusType"] ?? 0); int idx = Convert.ToInt32(d["Number"] ?? -1);
                bool boot = Convert.ToBoolean(d["IsBoot"] ?? false) || Convert.ToBoolean(d["IsSystem"] ?? false);
                if (bus != 7 || idx < 0 || boot || idx == system || d["Size"] == null) continue;     // 7 = USB
                seen.Add(idx);
                drives.Items.Add(new Drive { Index = idx, Model = (d["FriendlyName"] ?? "USB drive").ToString().Trim(), Size = Convert.ToInt64(d["Size"]), Iface = "USB", Letters = LettersFor(idx) });
            }
        } catch { }
        try {
            using (var q = new ManagementObjectSearcher("SELECT * FROM Win32_DiskDrive"))
            foreach (ManagementObject d in q.Get()) {
                var iface = (d["InterfaceType"] ?? "").ToString(); var media = (d["MediaType"] ?? "").ToString(); var pnp = (d["PNPDeviceID"] ?? "").ToString();
                int idx = Convert.ToInt32(d["Index"]);
                bool usb = iface == "USB" || media.Contains("Removable") || pnp.StartsWith("USBSTOR");
                if (!usb || idx == system || seen.Contains(idx) || d["Size"] == null) continue;     // never list internal disks or the Windows disk
                drives.Items.Add(new Drive { Index = idx, Model = (d["Model"] ?? "USB drive").ToString().Trim(), Size = Convert.ToInt64(d["Size"]), Iface = iface, Letters = Letters(d) });
            }
        } catch (Exception ex) { status.Text = "Couldn't list drives: " + ex.Message; }
        if (drives.Items.Count == 0) { status.ForeColor = Dim; status.Text = "No USB stick found. Plug one in and press Refresh."; }
        else { drives.SelectedIndex = 0; status.Text = ""; }
    }

    static string LettersFor(int idx) {
        try {
            using (var q = new ManagementObjectSearcher("SELECT * FROM Win32_DiskDrive WHERE Index=" + idx))
                foreach (ManagementObject d in q.Get()) return Letters(d);
        } catch { }
        return "";
    }

    static string Letters(ManagementObject disk) {
        var l = new List<string>();
        try {
            foreach (ManagementObject p in disk.GetRelated("Win32_DiskPartition"))
                foreach (ManagementObject v in p.GetRelated("Win32_LogicalDisk")) l.Add(v["DeviceID"].ToString());
        } catch { }
        return string.Join(" ", l.ToArray());
    }

    static int SystemDisk() {
        try {
            var sys = Path.GetPathRoot(Environment.SystemDirectory).TrimEnd('\\');
            using (var q = new ManagementObjectSearcher("ASSOCIATORS OF {Win32_LogicalDisk.DeviceID='" + sys + "'} WHERE AssocClass=Win32_LogicalDiskToPartition"))
                foreach (ManagementObject p in q.Get()) return Convert.ToInt32(p["DiskIndex"]);
        } catch { }
        return 0;
    }

    void Start() {
        if (image == null) { if (!editions.Visible) LoadImage(); return; }
        var d = drives.SelectedItem as Drive;
        if (d == null) { MessageBox.Show(this, "Plug in a USB stick and press Refresh.", Text); return; }
        if (d.Size < image.Size) { MessageBox.Show(this, "This stick is too small: " + Drive.Gb(d.Size) + ". Aftergrid needs at least " + Drive.Gb(image.Size) + " (16 GB or larger recommended).", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning); return; }
        if (d.Size > 600e9 && MessageBox.Show(this, "This looks like a large external hard drive (" + Drive.Gb(d.Size) + "), not a USB stick. Are you sure you want to erase it?", Text, MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes) return;
        // Typed confirmation: the size shown, so nobody erases the wrong drive by clicking through.
        var want = (d.Size / 1e9).ToString("0.0");
        var typed = Prompt.Show(this, "Everything on this drive will be erased:\n\n" + d + "\n\nType its size in GB (" + want + ") to continue:");
        if (typed == null) return;
        if (typed.Trim().Replace(',', '.') != want) { MessageBox.Show(this, "That didn't match " + want + ". Nothing was changed.", Text); return; }
        UpdatePackInfo();
        if (packInfo.ForeColor == Red && MessageBox.Show(this, "The ticked packs probably won't all fit on this stick. Continue anyway? (Packs that don't fit are skipped.)", Text, MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes) return;
        make.Enabled = drives.Enabled = refresh.Enabled = editions.Enabled = packs.Enabled = false; status.ForeColor = Ink; detail.Text = "";
        worker.RunWorkerAsync(d);
    }

    // ---------------------------------------------------------------- the work
    void Work(object sender, DoWorkEventArgs e) {
        var d = (Drive)e.Argument;
        Report(0, "Preparing the stick…", "Removing its partitions so Windows lets go of it.");
        Diskpart("select disk " + d.Index + "\r\nattributes disk clear readonly\r\nclean\r\nrescan\r\n");
        System.Threading.Thread.Sleep(2500);

        string path = @"\\.\PhysicalDrive" + d.Index;
        var sha = SHA256.Create(); var stick = SHA256.Create(); long total = image.Size, done = 0; var sw = Stopwatch.StartNew();
        bool hasPacks = chosen.Count > 0; double wW = hasPacks ? .5 : .7, wV = hasPacks ? .2 : .3;   // progress bar shares
        StickLayout layout = null;
        IntPtr buf = Native.VirtualAlloc(IntPtr.Zero, (UIntPtr)Block, Native.MEM_COMMIT | Native.MEM_RESERVE, Native.PAGE_READWRITE);
        var managed = new byte[Block];
        try {
            using (var h = Open(path, true)) {
                using (var src = image.Remote ? (Stream)new WebPartsStream(image.Files) : new PartsStream(image.Files)) {   // the parts, read as one continuous image
                    int n;
                    while ((n = Fill(src, managed)) > 0) {
                        sha.TransformBlock(managed, 0, n, null, 0);        // fingerprint of the image as published
                        if (done == 0) {                                     // first block: add the saves + VAULT partitions
                            layout = StickLayout.Plan(managed, d.Size, total);
                            if (layout.Skip == null) layout.Apply(managed);
                        }
                        stick.TransformBlock(managed, 0, n, null, 0);      // fingerprint of what the stick should hold
                        int len = (n + 4095) & ~4095;                        // raw disk writes must be whole sectors
                        if (len > n) Array.Clear(managed, n, len - n);
                        Marshal.Copy(managed, 0, buf, len);
                        uint w;
                        if (!Native.WriteFile(h, buf, (uint)len, out w, IntPtr.Zero) || w != len)
                            throw new Exception("Writing failed at " + Drive.Gb(done) + " (Windows error " + Marshal.GetLastWin32Error() + "). The stick may be faulty or was unplugged.");
                        done += n;
                        Report(Per(done, total) * wW, (image.Remote ? "Downloading and writing… " : "Writing… ") + Pct(done, total), Speed(done, total, sw));
                        if (worker.CancellationPending) return;
                    }
                }
                // Blank the start and end of the new partitions, so old data on the stick can't look like a file system.
                if (layout != null && layout.Skip == null) {
                    Array.Clear(managed, 0, 1 << 20); Marshal.Copy(managed, 0, buf, 1 << 20);
                    foreach (long off in new[] { layout.SavesStart * 512, (layout.SavesStart + layout.SavesSectors) * 512 - (1 << 20), layout.VaultOffset }) {
                        long np; uint w;
                        if (!Native.SetFilePointerEx(h, off, out np, 0) || !Native.WriteFile(h, buf, 1 << 20, out w, IntPtr.Zero))
                            throw new Exception("Couldn't prepare the VAULT area (Windows error " + Marshal.GetLastWin32Error() + ").");
                    }
                }
                Native.FlushFileBuffers(h);
            }
            sha.TransformFinalBlock(new byte[0], 0, 0);
            stick.TransformFinalBlock(new byte[0], 0, 0);
            string written = Hex(stick.Hash);
            if (image.Sha256 != null && image.Sha256 != "" && Hex(sha.Hash) != image.Sha256)
                throw new Exception(image.Remote ? "The download arrived damaged (fingerprint mismatch). Press Make again to retry." : "The image files themselves are damaged (fingerprint mismatch). Download them again.");

            // Verify: read everything back straight from the stick, bypassing Windows' cache.
            var check = SHA256.Create(); long left = total, got = 0; sw.Restart();
            using (var h = Open(path, false)) {
                while (left > 0) {
                    int want = (int)Math.Min(Block, (left + 4095) & ~4095L); uint r;
                    if (!Native.ReadFile(h, buf, (uint)want, out r, IntPtr.Zero) || r == 0) throw new Exception("Reading the stick back failed (Windows error " + Marshal.GetLastWin32Error() + ").");
                    int use = (int)Math.Min(r, left);
                    Marshal.Copy(buf, managed, 0, use); check.TransformBlock(managed, 0, use, null, 0);
                    left -= use; got += use;
                     Report(wW + Per(got, total) * wV, "Checking every byte… " + Pct(got, total), Speed(got, total, sw));
                }
            }
            check.TransformFinalBlock(new byte[0], 0, 0);
            if (Hex(check.Hash) != written) throw new Exception("The stick doesn't read back what was written. It is probably faulty: try another stick.");
            e.Result = d; summary = null;
            AddVault(d, layout, wW + wV);
        } finally { Native.VirtualFree(buf, UIntPtr.Zero, Native.MEM_RELEASE); }
    }

    // VAULT + packs. The stick already boots at this point, so problems here are reported, not fatal.
    void AddVault(Drive d, StickLayout layout, double from) {
        if (layout == null || layout.Skip != null) {
            summary = "No VAULT was added (" + (layout == null ? "unknown layout" : layout.Skip) + "). Aftergrid's setup creates it on first start; then use Aftergrid Control → Download.";
            return;
        }
        string vault;
        try {
            Report(from, "Creating the VAULT…", "A Windows-readable space for the library, maps and AI models.");
            vault = layout.FormatVault(d.Index);
            foreach (var f in new[] { "zim", "maps", "models", @"library\survival", @"library\medical", "backups" }) Directory.CreateDirectory(Path.Combine(vault, f));
        } catch (Exception ex) {
            summary = ex.Message + " The stick still works: Aftergrid sets up the VAULT on first start, then use Aftergrid Control → Download."; return;
        }
        if (chosen.Count == 0) { summary = "VAULT ready (" + vault + "). Add packs later from Aftergrid Control → Download."; return; }
        var failed = new List<string>(); int i = 0; double span = 1 - from;
        foreach (var p in chosen) {
            double a = from + span * i / chosen.Count, b = from + span * (i + 1) / chosen.Count; i++;
            try {
                foreach (Dictionary<string, object> it in p.Items) {
                    if (worker.CancellationPending) return;
                    Report(a, "Adding pack " + i + " of " + chosen.Count + ": " + p.Id, "Looking it up…");
                    var job = Job.From(it, vault);
                    job.Run((msg, f) => Report(f < 0 ? a : a + (b - a) * f, "Adding pack " + i + " of " + chosen.Count + ": " + p.Id, msg));
                }
            } catch (Exception ex) { failed.Add(p.Id + " (" + ex.Message + ")"); }
        }
        try { File.WriteAllText(Path.Combine(vault, "aftergrid-packs.txt"), "Added by Aftergrid USB Maker " + DateTime.Now.ToString("yyyy-MM-dd") + ":\r\n" + string.Join("\r\n", chosen.Select(p => p.Id).ToArray()) + "\r\n"); } catch { }
        summary = failed.Count == 0 ? "All " + chosen.Count + " pack(s) added to the VAULT." :
            "Some packs didn't finish: " + string.Join("; ", failed.ToArray()) + ". Add them later in Aftergrid Control → Download (it resumes).";
    }

    static SafeFileHandle Open(string path, bool write) {
        var h = Native.CreateFile(path, Native.GENERIC_READ | (write ? Native.GENERIC_WRITE : 0), Native.FILE_SHARE_READ | Native.FILE_SHARE_WRITE, IntPtr.Zero,
                                  Native.OPEN_EXISTING, Native.FILE_FLAG_NO_BUFFERING | (write ? Native.FILE_FLAG_WRITE_THROUGH : 0), IntPtr.Zero);
        if (h.IsInvalid) throw new Exception("Windows wouldn't open the stick (error " + Marshal.GetLastWin32Error() + "). Close any window showing the stick and try again.");
        return h;
    }
    static int Fill(Stream s, byte[] b) { int t = 0, n; while (t < b.Length && (n = s.Read(b, t, b.Length - t)) > 0) t += n; return t; }
    static double Per(long a, long b) { return b == 0 ? 0 : (double)a / b; }
    static string Pct(long a, long b) { return (100.0 * a / b).ToString("0") + "%"; }
    static string Hex(byte[] h) { var sb = new StringBuilder(); foreach (var x in h) sb.Append(x.ToString("X2")); return sb.ToString(); }
    static string Speed(long done, long total, Stopwatch sw) {
        double s = sw.Elapsed.TotalSeconds; if (s < 2 || done == 0) return Drive.Gb(done) + " of " + Drive.Gb(total);
        double mbps = done / 1e6 / s, rem = (total - done) / 1e6 / mbps;
        return Drive.Gb(done) + " of " + Drive.Gb(total) + "   ·   " + mbps.ToString("0") + " MB/s   ·   about " + Math.Ceiling(rem / 60) + " min left";
    }
    static void Diskpart(string script) {
        var f = Path.Combine(Path.GetTempPath(), "aftergrid-diskpart.txt"); File.WriteAllText(f, script);
        var p = Process.Start(new ProcessStartInfo("diskpart.exe", "/s \"" + f + "\"") { CreateNoWindow = true, UseShellExecute = false, RedirectStandardOutput = true });
        string o = p.StandardOutput.ReadToEnd(); p.WaitForExit(); File.Delete(f);
        if (p.ExitCode != 0) throw new Exception("Windows couldn't prepare the stick (diskpart):\n" + o.Trim().Split(new[]{'\n'}).Last());
    }
    void Report(double frac, string s, string d) { worker.ReportProgress((int)(frac * 1000), new[] { s, d }); }
    void Progress(object sender, ProgressChangedEventArgs e) {
        bar.Value = Math.Max(0, Math.Min(1000, e.ProgressPercentage)); var t = (string[])e.UserState; status.Text = t[0]; detail.Text = t[1];
    }
    void Done(object sender, RunWorkerCompletedEventArgs e) {
        make.Enabled = drives.Enabled = refresh.Enabled = editions.Enabled = true; packs.Enabled = packs.Items.Count > 0;
        if (e.Error != null) { status.ForeColor = Red; status.Text = "Not finished: " + e.Error.Message.Split(new[]{'\n'})[0]; detail.Text = e.Error.Message; bar.Value = 0; return; }
        bar.Value = 1000; status.ForeColor = Green; status.Text = "Done. The stick is ready and every byte checked out.";
        detail.Text = (summary != null ? summary + "\n" : "") + "To start: plug it in, restart, press the boot-menu key right away:\n" +
                      "F12 Dell / Lenovo / Acer,  F9 HP,  F8 ASUS,  F11 MSI,  Esc others,  Option on an Intel Mac.";
        LoadDrives();
    }

    // ---------------------------------------------------------------- entry
    [STAThread]
    static void Main(string[] args) {
        try { Native.SetProcessDPIAware(); } catch { }
        if (!new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator)) {
            try { Process.Start(new ProcessStartInfo(Application.ExecutablePath) { Verb = "runas", UseShellExecute = true }); }
            catch { MessageBox.Show("Aftergrid USB Maker needs administrator permission to write to a USB stick.", "Aftergrid USB Maker"); }
            return;
        }
        Application.EnableVisualStyles(); Application.Run(new MainForm());
    }
}

// Reads several files one after another as a single stream.
class PartsStream : Stream {
    readonly List<string> files; int i = -1; FileStream cur;
    public PartsStream(List<string> f) { files = f; Next(); }
    bool Next() { if (cur != null) cur.Dispose(); cur = null; if (++i >= files.Count) return false; cur = new FileStream(files[i], FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20); return true; }
    public override int Read(byte[] b, int o, int n) {
        while (cur != null) { int r = cur.Read(b, o, n); if (r > 0) return r; if (!Next()) break; }
        return 0;
    }
    protected override void Dispose(bool d) { if (cur != null) cur.Dispose(); base.Dispose(d); }
    public override bool CanRead { get { return true; } } public override bool CanSeek { get { return false; } } public override bool CanWrite { get { return false; } }
    public override long Length { get { throw new NotSupportedException(); } } public override long Position { get { throw new NotSupportedException(); } set { throw new NotSupportedException(); } }
    public override void Flush() { } public override long Seek(long o, SeekOrigin s) { throw new NotSupportedException(); }
    public override void SetLength(long v) { throw new NotSupportedException(); } public override void Write(byte[] b, int o, int n) { throw new NotSupportedException(); }
}

// Reads several URLs one after another as a single stream; a dropped connection resumes with a Range request.
class WebPartsStream : Stream {
    readonly List<string> urls; int i = 0; long pos = 0; Stream cur; HttpWebResponse resp;
    public WebPartsStream(List<string> u) { urls = u; ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; ServicePointManager.DefaultConnectionLimit = 4; }
    void Open() {
        Close1();
        var rq = (HttpWebRequest)WebRequest.Create(urls[i]); rq.UserAgent = "AftergridUsbMaker/2"; rq.Timeout = 30000; rq.ReadWriteTimeout = 60000;
        if (pos > 0) rq.AddRange(pos);
        resp = (HttpWebResponse)rq.GetResponse();
        if (pos > 0 && resp.StatusCode != HttpStatusCode.PartialContent) throw new IOException("server can't resume");
        cur = resp.GetResponseStream();
    }
    void Close1() { if (cur != null) cur.Dispose(); if (resp != null) resp.Close(); cur = null; resp = null; }
    public override int Read(byte[] b, int o, int n) {
        for (int tries = 0; ; ) {
            if (i >= urls.Count) return 0;
            try {
                if (cur == null) Open();
                int r = cur.Read(b, o, n);
                if (r > 0) { pos += r; return r; }
                Close1(); i++; pos = 0;                                   // this part is done: next one
            } catch (Exception ex) {
                Close1();
                if (++tries > 8) throw new Exception("The download keeps failing (" + ex.Message + "). Check the internet connection and press Make again.");
                System.Threading.Thread.Sleep(Math.Min(30000, 1000 << tries));
            }
        }
    }
    protected override void Dispose(bool d) { Close1(); base.Dispose(d); }
    public override bool CanRead { get { return true; } } public override bool CanSeek { get { return false; } } public override bool CanWrite { get { return false; } }
    public override long Length { get { throw new NotSupportedException(); } } public override long Position { get { throw new NotSupportedException(); } set { throw new NotSupportedException(); } }
    public override void Flush() { } public override long Seek(long o, SeekOrigin s) { throw new NotSupportedException(); }
    public override void SetLength(long v) { throw new NotSupportedException(); } public override void Write(byte[] b, int o, int n) { throw new NotSupportedException(); }
}

// The Aftergrid mark: 3x3 grid, top-right square lit amber.
class MarkPanel : Panel {
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
        float c = Width / 3.4f, g = c * .2f;
        for (int r = 0; r < 3; r++) for (int k = 0; k < 3; k++)
            using (var b = new SolidBrush(r == 0 && k == 2 ? Color.FromArgb(242, 163, 58) : Color.FromArgb(58, 68, 76)))
                e.Graphics.FillRectangle(b, k * (c + g), r * (c + g), c, c);
    }
}

static class Prompt {
    public static string Show(IWin32Window owner, string text) {
        var f = new Form { Text = "Confirm", ClientSize = new Size(460, 230), FormBorderStyle = FormBorderStyle.FixedDialog, StartPosition = FormStartPosition.CenterParent, MinimizeBox = false, MaximizeBox = false, Font = new Font("Segoe UI", 10f) };
        var l = new Label { Text = text, Location = new Point(16, 14), Size = new Size(430, 120) };
        var t = new TextBox { Location = new Point(16, 140), Size = new Size(140, 26) };
        var ok = new Button { Text = "Erase and write", DialogResult = DialogResult.OK, Location = new Point(220, 184), Size = new Size(130, 32) };
        var no = new Button { Text = "Cancel", DialogResult = DialogResult.Cancel, Location = new Point(356, 184), Size = new Size(90, 32) };
        f.Controls.AddRange(new Control[] { l, t, ok, no }); f.AcceptButton = ok; f.CancelButton = no;
        return f.ShowDialog(owner) == DialogResult.OK ? t.Text : null;
    }
}
