// retro-neon-ui for WinForms: loads the kit's TTF files so controls can use them without installing anything.
// MIT license. Written in C# 7.3: compile-tested as a .NET Framework 4.8 library
// and run-tested on .NET 8.
// Copy dotnet/fonts/*.ttf into the app's output folder under Fonts\ (in the .csproj:
// <None Include="Fonts\*.ttf" CopyToOutputDirectory="PreserveNewest" />), then call RetroFonts.Load() once at startup,
// before any form is created.
#if NETCOREAPP
#nullable disable
#endif
using System;
using System.Drawing;
using System.Drawing.Text;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;

namespace RetroNeon
{
    /// <summary>The kit's fonts for WinForms: Display (Exo 2), Body (Space Grotesk), Pixel (Press Start 2P), Terminal (VT323).</summary>
    public static class RetroFonts
    {
        // GDI+ (Graphics.DrawString) reads the PrivateFontCollection; GDI (TextRenderer, which most controls use) only
        // sees fonts registered with AddFontResourceEx. Both are needed, or labels silently fall back to a system font.
        [DllImport("gdi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern int AddFontResourceEx(string name, uint flags, IntPtr reserved);

        private const uint FR_PRIVATE = 0x10;

        private static PrivateFontCollection collection;

        // Families are read once per Load(): PrivateFontCollection.Families builds new GDI+ objects on every call.
        private static FontFamily[] families = new FontFamily[0];

        /// <summary>Folder the fonts were loaded from, or null before Load().</summary>
        public static string LoadedFrom { get; private set; }

        /// <summary>Family names found by Load() (empty before it).</summary>
        public static string[] FamilyNames => families.Select(f => f.Name).ToArray();

        /// <summary>Loads every .ttf in <paramref name="folder"/> (default: Fonts\ next to the executable). Returns the count.</summary>
        public static int Load(string folder = null)
        {
            folder = folder ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Fonts");
            if (!Directory.Exists(folder))
            {
                return 0;
            }

            var files = Directory.GetFiles(folder, "*.ttf");
            var pfc = new PrivateFontCollection();
            foreach (var file in files)
            {
                pfc.AddFontFile(file);
                AddFontResourceEx(file, FR_PRIVATE, IntPtr.Zero);
            }

            foreach (var family in families)
            {
                family.Dispose();
            }
            if (collection != null)
            {
                collection.Dispose();
            }
            collection = pfc;
            families = pfc.Families;
            LoadedFrom = folder;
            return files.Length;
        }

        /// <summary>Headings: Exo 2 Black Italic. Falls back to Segoe UI Bold Italic if the fonts are not loaded.</summary>
        public static Font Display(float size) => Make("Exo 2 Black", size, FontStyle.Italic, "Segoe UI", FontStyle.Bold | FontStyle.Italic);

        /// <summary>Buttons and subtitles: Exo 2 ExtraBold Italic.</summary>
        public static Font DisplayButton(float size) => Make("Exo 2 ExtraBold", size, FontStyle.Italic, "Segoe UI", FontStyle.Bold | FontStyle.Italic);

        /// <summary>Body text: Space Grotesk (Regular or Bold).</summary>
        public static Font Body(float size, bool bold = false) => Body(size, bold ? FontStyle.Bold : FontStyle.Regular);

        /// <summary>Body text in any style (bold, italic, underline, strikeout). Space Grotesk has no italic face;
        /// GDI+ slants the regular one, so italic text stays italic in the kit font.</summary>
        public static Font Body(float size, FontStyle style) => Make("Space Grotesk", size, style, "Segoe UI", style);

        /// <summary>Small caps labels: Press Start 2P (keep it 6 to 9 pt; it is a wide pixel font).</summary>
        public static Font Pixel(float size) => Make("Press Start 2P", size, FontStyle.Regular, "Consolas", FontStyle.Regular);

        /// <summary>Status lines, logs, code: VT323 (it reads small; 14 pt and up).</summary>
        public static Font Terminal(float size) => Make("VT323", size, FontStyle.Regular, "Consolas", FontStyle.Regular);

        /// <summary>A loaded family by name, or null.</summary>
        public static FontFamily Family(string name) =>
            families.FirstOrDefault(f => string.Equals(f.Name, name, StringComparison.OrdinalIgnoreCase));

        private static Font Make(string family, float size, FontStyle style, string fallback, FontStyle fallbackStyle)
        {
            var found = Family(family);
            if (found != null && found.IsStyleAvailable(style))
            {
                return new Font(found, size, style, GraphicsUnit.Point);
            }

            return new Font(fallback, size, fallbackStyle, GraphicsUnit.Point);
        }
    }
}
