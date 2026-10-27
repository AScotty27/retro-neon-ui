// Loads RetroNeon.Implicit.xaml the way an app would (pack URI, fonts as resources), checks every font key resolves
// to the shipped TTF, renders a sample of every style offscreen and saves it as a PNG. Exit 1 on any failure.
using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;

namespace WpfSmoke
{
    public static class Program
    {
        private record Row(string Job, string Owner, int Runs);

        [STAThread]
        public static int Main(string[] args)
        {
            var outPath = args.Length > 0 ? args[0] : "wpf-smoke.png";
            var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
            app.Resources.MergedDictionaries.Add(new ResourceDictionary
            {
                Source = new Uri("pack://application:,,,/WpfSmoke;component/Themes/RetroNeon.Implicit.xaml"),
            });

            var failures = 0;
            var fonts = new (string Key, FontWeight Weight, FontStyle Style, string File)[]
            {
                ("Rt.Font.Display", FontWeights.Black, FontStyles.Italic, "Exo2-BlackItalic.ttf"),
                ("Rt.Font.Display", FontWeights.ExtraBold, FontStyles.Italic, "Exo2-ExtraBoldItalic.ttf"),
                ("Rt.Font.Body", FontWeights.Normal, FontStyles.Normal, "SpaceGrotesk-Regular.ttf"),
                ("Rt.Font.Body", FontWeights.Bold, FontStyles.Normal, "SpaceGrotesk-Bold.ttf"),
                ("Rt.Font.Pixel", FontWeights.Normal, FontStyles.Normal, "PressStart2P-Regular.ttf"),
                ("Rt.Font.Term", FontWeights.Normal, FontStyles.Normal, "VT323-Regular.ttf"),
            };
            foreach (var (key, weight, style, file) in fonts)
            {
                var family = (FontFamily)app.FindResource(key);
                var face = new Typeface(family, style, weight, FontStretches.Normal);
                var ok = face.TryGetGlyphTypeface(out var glyphs) && glyphs.FontUri.ToString().EndsWith(file, StringComparison.OrdinalIgnoreCase);
                Console.WriteLine($"{(ok ? "PASS" : "FAIL")}  {key} {weight} {style} -> {(glyphs != null ? glyphs.FontUri.ToString() : "no glyph typeface")}");
                failures += ok ? 0 : 1;
            }

            var keys = new[]
            {
                "Rt.Window", "Rt.Text.Title", "Rt.Text.Subtitle", "Rt.Text.Label", "Rt.Text.Terminal", "Rt.Text.Body", "Rt.Text.Muted",
                "Rt.Button", "Rt.Button.Primary", "Rt.Button.Secondary", "Rt.Button.Success", "Rt.Button.Danger", "Rt.TextBox",
                "Rt.PasswordBox", "Rt.CheckBox", "Rt.Switch", "Rt.ProgressBar", "Rt.Card", "Rt.Alert.Info", "Rt.Alert.Success",
                "Rt.Alert.Warning", "Rt.Alert.Danger", "Rt.Tag", "Rt.Tag.Accent", "Rt.Tag.Info", "Rt.Tag.Success", "Rt.Tag.Warning",
                "Rt.Tag.Danger", "Rt.DataGrid", "Rt.ToolTip", "Rt.StripeBar", "Rt.Trail", "Rt.Scanlines", "Rt.Brush.Stripes",
                "Rt.Brush.Trail", "Rt.Glow.Yellow", "Rt.CornerRadius", "Rt.ScrollBar",
            };
            foreach (var key in keys)
            {
                if (app.TryFindResource(key) == null)
                {
                    Console.WriteLine($"FAIL  missing resource {key}");
                    failures++;
                }
            }

            var sample = BuildSample(app);
            const int width = 1100, height = 780;
            sample.Measure(new Size(width, height));
            sample.Arrange(new Rect(0, 0, width, height));
            sample.UpdateLayout();

            var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
            bitmap.Render(sample);
            var encoder = new PngBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using (var stream = File.Create(outPath))
            {
                encoder.Save(stream);
            }
            Console.WriteLine($"wrote {System.IO.Path.GetFullPath(outPath)} ({width}x{height})");
            Console.WriteLine(failures == 0 ? "ALL PASS" : $"{failures} FAILURE(S)");
            return failures == 0 ? 0 : 1;
        }

        private static T Styled<T>(Application app, T element, string key) where T : FrameworkElement
        {
            element.Style = (Style)app.FindResource(key);
            return element;
        }

        private static FrameworkElement BuildSample(Application app)
        {
            var root = new Grid { Background = (Brush)app.FindResource("Rt.Brush.Window") };
            TextElement.SetForeground(root, (Brush)app.FindResource("Rt.Brush.Text"));
            TextElement.SetFontFamily(root, (FontFamily)app.FindResource("Rt.Font.Body"));

            var page = new StackPanel { Margin = new Thickness(36, 28, 36, 28) };
            root.Children.Add(page);

            page.Children.Add(Styled(app, new Rectangle(), "Rt.StripeBar"));
            page.Children.Add(Styled(app, new TextBlock { Text = "NEON APP", Margin = new Thickness(0, 18, 0, 6) }, "Rt.Text.Title"));
            page.Children.Add(Styled(app, new TextBlock { Text = "> ALL SYSTEMS NOMINAL", Margin = new Thickness(0, 0, 0, 8) }, "Rt.Text.Terminal"));
            page.Children.Add(Styled(app, new Rectangle { Width = 220, HorizontalAlignment = HorizontalAlignment.Left }, "Rt.Trail"));

            var buttons = new WrapPanel { Margin = new Thickness(0, 22, 0, 10) };
            buttons.Children.Add(Styled(app, new Button { Content = "PRIMARY" }, "Rt.Button.Primary"));
            buttons.Children.Add(Styled(app, new Button { Content = "SECONDARY" }, "Rt.Button.Secondary"));
            buttons.Children.Add(Styled(app, new Button { Content = "SUCCESS" }, "Rt.Button.Success"));
            buttons.Children.Add(Styled(app, new Button { Content = "DANGER" }, "Rt.Button.Danger"));
            buttons.Children.Add(new Button { Content = "IMPLICIT" });
            buttons.Children.Add(new Button { Content = "DISABLED", IsEnabled = false });
            page.Children.Add(buttons);

            var columns = new Grid { Margin = new Thickness(0, 10, 0, 0) };
            columns.ColumnDefinitions.Add(new ColumnDefinition());
            columns.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(24) });
            columns.ColumnDefinitions.Add(new ColumnDefinition());
            page.Children.Add(columns);

            var form = new StackPanel();
            form.Children.Add(Styled(app, new TextBlock { Text = "DISPLAY NAME", Margin = new Thickness(0, 0, 0, 8) }, "Rt.Text.Label"));
            form.Children.Add(new TextBox { Text = "Player One" });
            form.Children.Add(Styled(app, new TextBlock { Text = "PASSWORD", Margin = new Thickness(0, 14, 0, 8) }, "Rt.Text.Label"));
            form.Children.Add(new PasswordBox { Password = "hunter22" });
            var toggles = new WrapPanel { Margin = new Thickness(0, 16, 0, 0) };
            toggles.Children.Add(new CheckBox { Content = "Email me", IsChecked = true, Margin = new Thickness(0, 0, 24, 0) });
            toggles.Children.Add(Styled(app, new ToggleButton { Content = "AUTOSAVE", IsChecked = true, Margin = new Thickness(0, 0, 24, 0) }, "Rt.Switch"));
            toggles.Children.Add(Styled(app, new CheckBox { Content = "SCANLINES" }, "Rt.Switch"));
            form.Children.Add(toggles);
            form.Children.Add(new ProgressBar { Value = 62, Margin = new Thickness(0, 18, 0, 0) });
            form.Children.Add(new ProgressBar { IsIndeterminate = true, Margin = new Thickness(0, 10, 0, 0) });
            var tags = new WrapPanel { Margin = new Thickness(0, 16, 0, 0) };
            foreach (var (text, key) in new[] { ("TAG", "Rt.Tag"), ("ACCENT", "Rt.Tag.Accent"), ("INFO", "Rt.Tag.Info"),
                         ("OK", "Rt.Tag.Success"), ("SLOW", "Rt.Tag.Warning"), ("DOWN", "Rt.Tag.Danger") })
            {
                tags.Children.Add(Styled(app, new Label { Content = text, Margin = new Thickness(0, 0, 8, 0) }, key));
            }
            form.Children.Add(tags);
            var card = Styled(app, new ContentControl { Content = form }, "Rt.Card");
            Grid.SetColumn(card, 0);
            columns.Children.Add(card);

            var right = new StackPanel();
            foreach (var (text, key) in new[] { ("New version ready.", "Rt.Alert.Info"), ("Saved.", "Rt.Alert.Success"),
                         ("Low disk space.", "Rt.Alert.Warning"), ("Sync failed.", "Rt.Alert.Danger") })
            {
                right.Children.Add(Styled(app, new ContentControl { Content = text, Margin = new Thickness(0, 0, 0, 10) }, key));
            }
            var grid = new DataGrid
            {
                AutoGenerateColumns = true,
                IsReadOnly = true,
                Height = 170,
                Margin = new Thickness(0, 6, 0, 0),
                ItemsSource = new List<Row> { new("Nightly build", "Build bot", 42), new("Asset sync", "Studio", 17),
                    new("Report export", "Finance", 3), new("Backup", "Ops", 7) },
            };
            right.Children.Add(grid);
            Grid.SetColumn(right, 2);
            columns.Children.Add(right);

            // Scanlines over everything, as an app's root Grid would have them.
            root.Children.Add(Styled(app, new Rectangle(), "Rt.Scanlines"));
            return root;
        }
    }
}
