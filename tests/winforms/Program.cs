// Loads the fonts, checks every family is present and that GDI text really uses them (not a silent fallback),
// themes a sample form, renders it offscreen and saves a PNG. Exit 1 on any failure.
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using RetroNeon;

namespace WinFormsSmoke
{
    internal sealed class TestCombo : ComboBox
    {
        public void Draw(DrawItemEventArgs e) => OnDrawItem(e);
    }

    public static class Program
    {
        [STAThread]
        public static int Main(string[] args)
        {
            var outPath = args.Length > 0 ? args[0] : "winforms-smoke.png";
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            var failures = 0;
            var count = RetroFonts.Load();
            Console.WriteLine($"loaded {count} font files from {RetroFonts.LoadedFrom}: {string.Join(", ", RetroFonts.FamilyNames)}");
            foreach (var family in new[] { "Exo 2 Black", "Exo 2 ExtraBold", "Space Grotesk", "Space Grotesk Medium", "Press Start 2P", "VT323" })
            {
                var ok = RetroFonts.FamilyNames.Contains(family);
                Console.WriteLine($"{(ok ? "PASS" : "FAIL")}  family {family}");
                failures += ok ? 0 : 1;
            }

            // GDI (TextRenderer, used by Label and Button) must draw the private font, not its fallback.
            foreach (var (name, font, fallback) in new[]
                     {
                         ("Pixel", RetroFonts.Pixel(12f), new Font("Consolas", 12f)),
                         ("Display", RetroFonts.Display(16f), new Font("Segoe UI", 16f, FontStyle.Bold | FontStyle.Italic)),
                         ("Terminal", RetroFonts.Terminal(16f), new Font("Consolas", 16f)),
                     })
            {
                var differs = !SameRender(font, fallback);
                Console.WriteLine($"{(differs ? "PASS" : "FAIL")}  GDI draws {name} with {font.Name} (differs from {fallback.Name})");
                failures += differs ? 0 : 1;
            }

            using var form = BuildForm();
            RetroTheme.Apply(form);
            CreateHandles(form);
            form.PerformLayout();
            form.Controls.OfType<DataGridView>().First().ClearSelection();
            using var bitmap = new Bitmap(form.ClientSize.Width, form.ClientSize.Height);
            using (var g = Graphics.FromImage(bitmap))
            {
                g.Clear(form.BackColor);
            }
            foreach (Control control in form.Controls)
            {
                control.DrawToBitmap(bitmap, control.Bounds);
            }
            bitmap.Save(outPath, ImageFormat.Png);
            Console.WriteLine($"wrote {Path.GetFullPath(outPath)} ({bitmap.Width}x{bitmap.Height})");

            // ComboBox does not answer the offscreen print message, so its owner-draw path is checked directly.
            using (var combo = new TestCombo())
            {
                combo.Items.AddRange(new object[] { "North", "South" });
                RetroTheme.Apply(combo);
                using var cell = new Bitmap(200, 30);
                using (var g = Graphics.FromImage(cell))
                {
                    g.Clear(Color.White);
                    combo.Draw(new DrawItemEventArgs(g, combo.Font, new Rectangle(0, 0, 200, 30), 0, DrawItemState.ComboBoxEdit));
                }
                var corner = cell.GetPixel(190, 2);
                var lit = Enumerable.Range(0, 60).Any(x => Enumerable.Range(0, 30).Any(y => cell.GetPixel(x, y).GetBrightness() > 0.6f));
                var okCombo = combo.DrawMode == DrawMode.OwnerDrawFixed && corner.ToArgb() == RetroTheme.InputColor.ToArgb() && lit;
                Console.WriteLine($"{(okCombo ? "PASS" : "FAIL")}  combo owner-draw: mode {combo.DrawMode}, background {corner}, text drawn {lit}");
                failures += okCombo ? 0 : 1;
            }

            // Presentation only: an app-coloured label keeps its colour, a filled RichTextBox keeps its formatting.
            using (var probe = new Form())
            {
                var red = new Label { Text = "ERROR", ForeColor = Color.Red };
                var plain = new Label { Text = "plain" };
                var rich = new RichTextBox();
                var emptyRich = new RichTextBox();
                var tabs = new TabControl();
                var page = new TabPage("One") { UseVisualStyleBackColor = true };
                tabs.TabPages.Add(page);
                var number = new NumericUpDown();
                var italic = new Label { Text = "hint", Font = new Font("Segoe UI", 9f, FontStyle.Italic) };
                var underlined = new Label { Text = "link", Font = new Font("Segoe UI", 9f, FontStyle.Underline) };
                var grid = new DataGridView();
                grid.DefaultCellStyle.Font = new Font("Segoe UI", 12f, FontStyle.Bold);
                var group = new GroupBox { Text = "GROUP" };
                var inGroup = new Label { Text = "inside" };
                group.Controls.Add(inGroup);
                var richGroup = new GroupBox { Text = "NOTES" };
                var groupRich = new RichTextBox();
                richGroup.Controls.Add(groupRich);
                probe.Controls.AddRange(new Control[] { red, plain, rich, emptyRich, tabs, number, italic, underlined, grid, group, richGroup });
                CreateHandles(probe);
                rich.Rtf = @"{\rtf1\ansi{\fonttbl{\f0 Arial;}{\f1 Courier New;}}{\colortbl;\red255\green0\blue0;}\f0 plain \cf1\f1 red courier\cf0\f0  end}";
                var rtfBefore = rich.Rtf;
                groupRich.Rtf = rich.Rtf;
                var groupRtfBefore = groupRich.Rtf;
                var richGroupFontBefore = richGroup.Font;
                RetroTheme.Apply(probe);
                var innerEdit = number.Controls.OfType<TextBox>().FirstOrDefault();
                var checks = new (bool Ok, string What)[]
                {
                    (red.ForeColor.ToArgb() == Color.Red.ToArgb(), "app-coloured label keeps its colour"),
                    (plain.ForeColor.ToArgb() == RetroPalette.Text.ToArgb(), "default label text turns light"),
                    (rich.Rtf == rtfBefore, "filled RichTextBox formatting untouched"),
                    (emptyRich.BackColor.ToArgb() == RetroTheme.InputColor.ToArgb(), "empty RichTextBox themed"),
                    (!page.UseVisualStyleBackColor && page.BackColor.ToArgb() == RetroPalette.Black.ToArgb(), "tab page dark"),
                    (number.BackColor.ToArgb() == RetroTheme.InputColor.ToArgb(), "NumericUpDown themed"),
                    (innerEdit != null && innerEdit.BorderStyle == BorderStyle.None, "NumericUpDown inner edit box keeps no border"),
                    (italic.Font.Italic, $"italic label stays italic ({italic.Font.Name})"),
                    (underlined.Font.Underline && underlined.Font.Name == "Space Grotesk", $"underlined label stays underlined in the kit font ({underlined.Font.Name})"),
                    (grid.DefaultCellStyle.Font.Bold && Math.Abs(grid.DefaultCellStyle.Font.SizeInPoints - 12f) < 0.01f, "grid keeps its 12 pt bold cell font"),
                    (group.Font.Name == "Space Grotesk" && group.Font.Bold, "group caption in the kit font, bold"),
                    (!inGroup.Font.Bold && inGroup.Font.Name == "Space Grotesk", "group child not bold, in the kit font"),
                    (groupRich.Rtf == groupRtfBefore && richGroup.Font.Equals(richGroupFontBefore), "group above a filled RichTextBox keeps its font and the RTF"),
                };
                foreach (var (ok, what) in checks)
                {
                    Console.WriteLine($"{(ok ? "PASS" : "FAIL")}  {what}");
                    failures += ok ? 0 : 1;
                }
            }

            var buttonBack = form.Controls.OfType<Button>().First(b => b.Text == "SAVE").BackColor;
            var okPrimary = buttonBack.ToArgb() == RetroPalette.C6.ToArgb();
            Console.WriteLine($"{(okPrimary ? "PASS" : "FAIL")}  primary button colour {buttonBack}");
            failures += okPrimary ? 0 : 1;

            Console.WriteLine(failures == 0 ? "ALL PASS" : $"{failures} FAILURE(S)");
            return failures == 0 ? 0 : 1;
        }

        // The form is never shown, so child controls would not get window handles (and would not draw) on their own.
        private static void CreateHandles(Control control)
        {
            _ = control.Handle;
            foreach (Control child in control.Controls)
            {
                CreateHandles(child);
            }
        }

        private static bool SameRender(Font a, Font b)
        {
            using var one = Render(a);
            using var two = Render(b);
            for (var y = 0; y < one.Height; y++)
            {
                for (var x = 0; x < one.Width; x++)
                {
                    if (one.GetPixel(x, y) != two.GetPixel(x, y))
                    {
                        return false;
                    }
                }
            }
            return true;
        }

        private static Bitmap Render(Font font)
        {
            var bmp = new Bitmap(320, 60);
            using var g = Graphics.FromImage(bmp);
            g.Clear(Color.Black);
            TextRenderer.DrawText(g, "NEON APP 42", font, new Point(4, 4), Color.White);
            return bmp;
        }

        private static Form BuildForm()
        {
            var form = new Form { ClientSize = new Size(900, 560), Text = "Neon App", StartPosition = FormStartPosition.Manual };

            var menu = new MenuStrip { Dock = DockStyle.None, Location = new Point(0, 0), Width = 900 };
            var file = new ToolStripMenuItem("File");
            file.DropDownItems.Add("Open");
            file.DropDownItems.Add("Save");
            menu.Items.Add(file);
            menu.Items.Add(new ToolStripMenuItem("View"));
            menu.Items.Add(new ToolStripMenuItem("Help"));
            form.Controls.Add(menu);

            form.Controls.Add(new StripeBar { Location = new Point(0, 28), Width = 900 });

            var title = new Label { Text = "NEON APP", AutoSize = true, Location = new Point(28, 46) };
            RetroTheme.SetRole(title, "title");
            form.Controls.Add(title);

            var status = new Label { Text = "> ALL SYSTEMS NOMINAL", AutoSize = true, Location = new Point(32, 96) };
            RetroTheme.SetRole(status, "terminal");
            form.Controls.Add(status);

            var caption = new Label { Text = "DISPLAY NAME", AutoSize = true, Location = new Point(32, 140) };
            RetroTheme.SetRole(caption, "label");
            form.Controls.Add(caption);
            form.Controls.Add(new TextBox { Text = "Player One", Location = new Point(32, 162), Width = 300 });
            form.Controls.Add(new CheckBox { Text = "Email me release notes", Checked = true, AutoSize = true, Location = new Point(32, 206) });

            var x = 32;
            foreach (var (text, role) in new[] { ("SAVE", "primary"), ("PREVIEW", "secondary"), ("PUBLISH", "success"), ("DELETE", "danger"), ("CANCEL", "") })
            {
                var button = new Button { Text = text, Location = new Point(x, 290), Size = new Size(118, 42) };
                RetroTheme.SetRole(button, role);
                form.Controls.Add(button);
                x += 128;
            }

            var grid = new DataGridView
            {
                Location = new Point(32, 352),
                Size = new Size(620, 180),
                AllowUserToAddRows = false,
                RowHeadersVisible = false,
                AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
            };
            grid.Columns.Add("job", "JOB");
            grid.Columns.Add("owner", "OWNER");
            grid.Columns.Add("runs", "RUNS");
            grid.Rows.Add("Nightly build", "Build bot", 42);
            grid.Rows.Add("Asset sync", "Studio", 17);
            grid.Rows.Add("Report export", "Finance", 3);
            form.Controls.Add(grid);

            var group = new GroupBox { Text = "SETTINGS", Location = new Point(680, 140), Size = new Size(190, 120) };
            group.Controls.Add(new RadioButton { Text = "Dark", Checked = true, Location = new Point(14, 34), AutoSize = true });
            group.Controls.Add(new RadioButton { Text = "Darker", Location = new Point(14, 66), AutoSize = true });
            form.Controls.Add(group);
            return form;
        }
    }
}
