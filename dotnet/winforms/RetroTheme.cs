// retro-neon-ui for WinForms: applies the palette and fonts to an existing form, without touching its logic.
// MIT license. Needs RetroPalette.cs (generated) and RetroFonts.cs. Written in C# 7.3: compile-tested as a
// .NET Framework 4.8 library and run-tested on .NET 8.
//
//   RetroFonts.Load();                          // once, at startup
//   RetroTheme.SetRole(saveButton, "primary");  // optional: primary | secondary | success | danger,
//                                               // title | subtitle | label | terminal | muted (labels), card (panels)
//   RetroTheme.Apply(this);                     // in the form's constructor, after InitializeComponent()
//
// What Apply changes (presentation only): BackColor and ForeColor of forms, labels, inputs, lists, trees, grids,
// check and radio buttons, group boxes, tab pages, up-down boxes, menus and tool strips; the font FAMILY of leaf
// controls (each keeps its own size and style: bold, italic, underline; roles set their own); buttons become flat
// with a neon outline;
// DropDownList-style combo boxes still on DrawMode.Normal become owner-drawn (dark items); grid row and header heights
// grow to fit the fonts; "card" panels get a dark fill and at least 16 px padding. Colours the app set itself on
// labels, check boxes and radio buttons are kept (only default black text is recoloured).
// Container fonts: a form's or user control's font is never changed (that re-runs font autoscaling). A group box's
// caption font and a tab control's header font change only when no RichTextBox below them holds text, because a
// parent's font change rewrites every run of a RichTextBox; their children keep their own fonts either way. A
// RichTextBox that already holds text is left alone entirely (its colour or font would rewrite every run); an empty
// one is themed. The inner parts of an up-down box are not walked (they would get a second border).
// Plain WinForms cannot draw glows or slanted buttons. The StripeBar control below draws the rainbow speed stripes.
#if NETCOREAPP
#nullable disable
#endif
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Runtime.CompilerServices;
using System.Windows.Forms;

namespace RetroNeon
{
    public static class RetroTheme
    {
        private static readonly ConditionalWeakTable<Control, string> Roles = new ConditionalWeakTable<Control, string>();

        /// <summary>Opaque stand-ins for the CSS's translucent colours (WinForms has no alpha blending on controls).</summary>
        public static readonly Color PanelColor = Color.FromArgb(18, 14, 34);
        public static readonly Color InputColor = Color.FromArgb(7, 6, 14);
        public static readonly Color LineOpaque = Color.FromArgb(54, 24, 82);
        public static readonly Color GridLine = Color.FromArgb(33, 16, 50);
        public static readonly Color Selection = Color.FromArgb(120, 24, 82);
        public static readonly Color HoverCyan = Color.FromArgb(10, 40, 48);
        public static readonly Color DangerText = Color.FromArgb(255, 139, 150);

        /// <summary>Gives a control a variant (see the file header). Call before Apply().</summary>
        public static void SetRole(Control control, string role)
        {
            Roles.Remove(control);
            Roles.Add(control, role);
        }

        private static string RoleOf(Control control)
        {
            string role;
            return Roles.TryGetValue(control, out role) ? role : "";
        }

        /// <summary>Styles <paramref name="root"/> and every control under it (parents first, so children that inherit
        /// colours and fonts pick up the theme).</summary>
        public static void Apply(Control root)
        {
            ApplyOne(root);
            // An up-down box's inner edit box and buttons belong to it: theming them again adds a second border.
            if (root is UpDownBase)
            {
                return;
            }
            foreach (Control child in root.Controls)
            {
                Apply(child);
            }
        }

        /// <summary>The kit's body family at the control's own size and style (bold, italic, underline, strikeout).</summary>
        private static Font BodyLike(Font current) => RetroFonts.Body(current.SizeInPoints, current.Style);

        private static bool HasFilledRichText(Control control)
        {
            foreach (Control child in control.Controls)
            {
                var rich = child as RichTextBox;
                if ((rich != null && rich.TextLength > 0) || HasFilledRichText(child))
                {
                    return true;
                }
            }
            return false;
        }

        /// <summary>Changes a container's own font (a caption, tab headers) while its direct children keep the font they
        /// had, so nothing below inherits the change.</summary>
        private static void SetContainerFont(Control container, Font font)
        {
            var kept = new List<KeyValuePair<Control, Font>>();
            foreach (Control child in container.Controls)
            {
                kept.Add(new KeyValuePair<Control, Font>(child, child.Font));
            }
            container.Font = font;
            foreach (var pair in kept)
            {
                pair.Key.Font = pair.Value;
            }
        }

        /// <summary>Default black text becomes the theme's text colour; any colour the app chose is kept.</summary>
        private static Color TextUnlessCustom(Color current)
        {
            var argb = current.ToArgb();
            return argb == SystemColors.ControlText.ToArgb() || argb == SystemColors.WindowText.ToArgb() ||
                   argb == Color.Black.ToArgb()
                ? RetroPalette.Text
                : current;
        }

        private static void ApplyOne(Control c)
        {
            switch (c)
            {
                case Form form:
                    form.BackColor = RetroPalette.Black;
                    form.ForeColor = RetroPalette.Text;
                    break;
                case Button button:
                    StyleButton(button, RoleOf(button));
                    break;
                case RichTextBox rich:
                    if (rich.TextLength == 0)
                    {
                        rich.BackColor = InputColor;
                        rich.ForeColor = RetroPalette.Text;
                        rich.Font = BodyLike(rich.Font);
                        rich.BorderStyle = BorderStyle.FixedSingle;
                    }
                    break;
                case TextBoxBase box:
                    box.BackColor = InputColor;
                    box.ForeColor = RetroPalette.Text;
                    box.BorderStyle = BorderStyle.FixedSingle;
                    box.Font = BodyLike(box.Font);
                    break;
                case UpDownBase upDown:
                    upDown.BackColor = InputColor;
                    upDown.ForeColor = RetroPalette.Text;
                    upDown.BorderStyle = BorderStyle.FixedSingle;
                    upDown.Font = BodyLike(upDown.Font);
                    break;
                case ComboBox combo:
                    combo.BackColor = InputColor;
                    combo.ForeColor = RetroPalette.Text;
                    combo.FlatStyle = FlatStyle.Flat;
                    combo.Font = BodyLike(combo.Font);
                    // A DropDownList's closed box is drawn by Windows in system colours unless the items are owner-drawn.
                    // Combos the app already owner-draws are left alone (and so is a second Apply()).
                    if (combo.DrawMode == DrawMode.Normal)
                    {
                        combo.DrawMode = DrawMode.OwnerDrawFixed;
                        combo.ItemHeight = Math.Max(combo.ItemHeight, combo.Font.Height + 6);
                        combo.DrawItem += DrawComboItem;
                    }
                    break;
                case ListBox list:
                    list.BackColor = InputColor;
                    list.ForeColor = RetroPalette.Text;
                    list.BorderStyle = BorderStyle.FixedSingle;
                    list.Font = BodyLike(list.Font);
                    break;
                case ListView view:
                    view.BackColor = InputColor;
                    view.ForeColor = RetroPalette.Text;
                    view.Font = BodyLike(view.Font);
                    break;
                case TreeView tree:
                    tree.BackColor = InputColor;
                    tree.ForeColor = RetroPalette.Text;
                    tree.LineColor = RetroPalette.C2;
                    tree.Font = BodyLike(tree.Font);
                    break;
                case DataGridView grid:
                    StyleGrid(grid);
                    break;
                case CheckBox check:
                    check.ForeColor = TextUnlessCustom(check.ForeColor);
                    check.Font = BodyLike(check.Font);
                    check.FlatStyle = FlatStyle.Flat;
                    check.FlatAppearance.BorderColor = RetroPalette.C2;
                    check.FlatAppearance.CheckedBackColor = InputColor;
                    break;
                case RadioButton radio:
                    radio.ForeColor = TextUnlessCustom(radio.ForeColor);
                    radio.Font = BodyLike(radio.Font);
                    radio.FlatStyle = FlatStyle.Flat;
                    break;
                case GroupBox group:
                    // Children that only inherit the group's colour would turn cyan with the caption; give them text colour.
                    var inheriting = new List<Control>();
                    foreach (Control child in group.Controls)
                    {
                        if (child.ForeColor.ToArgb() == group.ForeColor.ToArgb())
                        {
                            inheriting.Add(child);
                        }
                    }
                    group.ForeColor = RetroPalette.Cyan;
                    foreach (Control child in inheriting)
                    {
                        child.ForeColor = RetroPalette.Text;
                    }
                    if (!HasFilledRichText(group))
                    {
                        SetContainerFont(group, RetroFonts.Body(group.Font.SizeInPoints, group.Font.Style | FontStyle.Bold));
                    }
                    break;
                case TabControl tabs:
                    // The tab headers use the TabControl's font; the pages are themed one by one as the walk reaches them.
                    if (!HasFilledRichText(tabs))
                    {
                        SetContainerFont(tabs, BodyLike(tabs.Font));
                    }
                    break;
                case Label label:
                    StyleLabel(label, RoleOf(label));
                    break;
                case ToolStrip strip:
                    strip.Renderer = new ToolStripProfessionalRenderer(new RetroColorTable());
                    strip.BackColor = RetroPalette.Ink;
                    strip.ForeColor = RetroPalette.Text;
                    strip.Font = BodyLike(strip.Font);
                    StyleItems(strip.Items);
                    break;
                case TabPage page:
                    // Visual-style tab pages paint a light background whatever BackColor says.
                    page.UseVisualStyleBackColor = false;
                    page.BackColor = RetroPalette.Black;
                    page.ForeColor = TextUnlessCustom(page.ForeColor);
                    break;
                case Panel panel when RoleOf(panel) == "card":
                    panel.BackColor = PanelColor;
                    panel.Padding = new Padding(Math.Max(panel.Padding.Left, 16));
                    break;
            }
        }

        private static void DrawComboItem(object sender, DrawItemEventArgs e)
        {
            var combo = sender as ComboBox;
            if (combo == null)
            {
                return;
            }
            var highlighted = (e.State & DrawItemState.Selected) != 0 && (e.State & DrawItemState.ComboBoxEdit) == 0;
            using (var back = new SolidBrush(highlighted ? HoverCyan : InputColor))
            {
                e.Graphics.FillRectangle(back, e.Bounds);
            }
            if (e.Index >= 0)
            {
                var text = combo.GetItemText(combo.Items[e.Index]);
                var bounds = new Rectangle(e.Bounds.X + 4, e.Bounds.Y, e.Bounds.Width - 4, e.Bounds.Height);
                TextRenderer.DrawText(e.Graphics, text, combo.Font, bounds, highlighted ? RetroPalette.Cyan : RetroPalette.Text,
                    TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPrefix | TextFormatFlags.EndEllipsis);
            }
        }

        private static void StyleButton(Button b, string role)
        {
            b.FlatStyle = FlatStyle.Flat;
            b.FlatAppearance.BorderSize = 2;
            b.Font = RetroFonts.DisplayButton(b.Font.SizeInPoints);
            b.Cursor = Cursors.Hand;
            b.UseVisualStyleBackColor = false;
            Color fore, back, border, hover;
            switch (role)
            {
                case "primary":
                    fore = Color.FromArgb(26, 15, 0);
                    back = RetroPalette.C6;
                    border = Color.FromArgb(255, 242, 122);
                    hover = Color.FromArgb(255, 226, 60);
                    break;
                case "secondary":
                    fore = RetroPalette.Cyan;
                    back = InputColor;
                    border = RetroPalette.Cyan;
                    hover = HoverCyan;
                    break;
                case "success":
                    fore = RetroPalette.Green;
                    back = InputColor;
                    border = RetroPalette.Green;
                    hover = Color.FromArgb(12, 44, 24);
                    break;
                case "danger":
                    fore = DangerText;
                    back = InputColor;
                    border = RetroPalette.Red;
                    hover = Color.FromArgb(48, 12, 18);
                    break;
                default:
                    fore = RetroPalette.Text;
                    back = RetroPalette.Ink;
                    border = LineOpaque;
                    hover = Color.FromArgb(26, 20, 48);
                    break;
            }
            b.ForeColor = fore;
            b.BackColor = back;
            b.FlatAppearance.BorderColor = border;
            b.FlatAppearance.MouseOverBackColor = hover;
            b.FlatAppearance.MouseDownBackColor = back;
        }

        private static void StyleLabel(Label l, string role)
        {
            switch (role)
            {
                case "title":
                    l.ForeColor = RetroPalette.Yellow;
                    l.Font = RetroFonts.Display(22f);
                    break;
                case "subtitle":
                    l.ForeColor = RetroPalette.Text;
                    l.Font = RetroFonts.DisplayButton(13f);
                    break;
                case "label":
                    l.ForeColor = RetroPalette.Cyan;
                    l.Font = RetroFonts.Pixel(7.5f);
                    break;
                case "terminal":
                    l.ForeColor = RetroPalette.Green;
                    l.Font = RetroFonts.Terminal(16f);
                    break;
                case "muted":
                    l.ForeColor = RetroPalette.Muted;
                    break;
                default:
                    // Keeps app colours (a red error label stays red) and sizes; default black text turns light.
                    l.ForeColor = TextUnlessCustom(l.ForeColor);
                    l.Font = BodyLike(l.Font);
                    break;
            }
        }

        private static void StyleGrid(DataGridView g)
        {
            g.BackgroundColor = RetroPalette.Black;
            g.BorderStyle = BorderStyle.None;
            g.GridColor = GridLine;
            g.CellBorderStyle = DataGridViewCellBorderStyle.SingleHorizontal;
            g.EnableHeadersVisualStyles = false;
            g.ColumnHeadersBorderStyle = DataGridViewHeaderBorderStyle.None;
            g.ColumnHeadersDefaultCellStyle.BackColor = RetroPalette.Ink2;
            g.ColumnHeadersDefaultCellStyle.ForeColor = RetroPalette.Cyan;
            g.ColumnHeadersDefaultCellStyle.Font = RetroFonts.Pixel(7f);
            g.ColumnHeadersDefaultCellStyle.Padding = new Padding(6, 8, 6, 8);
            g.ColumnHeadersDefaultCellStyle.SelectionBackColor = RetroPalette.Ink2;
            g.ColumnHeadersHeight = Math.Max(g.ColumnHeadersHeight, 38);
            g.DefaultCellStyle.BackColor = RetroPalette.Ink;
            g.DefaultCellStyle.ForeColor = RetroPalette.Text;
            g.DefaultCellStyle.Font = BodyLike(g.DefaultCellStyle.Font ?? g.Font);
            g.DefaultCellStyle.SelectionBackColor = Selection;
            g.DefaultCellStyle.SelectionForeColor = Color.White;
            g.DefaultCellStyle.Padding = new Padding(6, 4, 6, 4);
            g.AlternatingRowsDefaultCellStyle.BackColor = Color.FromArgb(16, 13, 28);
            g.RowHeadersDefaultCellStyle.BackColor = RetroPalette.Ink2;
            g.RowHeadersDefaultCellStyle.ForeColor = RetroPalette.Muted;
            g.RowTemplate.Height = Math.Max(g.RowTemplate.Height, 34);
            // RowTemplate only reaches rows added later; rows the grid already holds get the height here.
            foreach (DataGridViewRow row in g.Rows)
            {
                row.Height = Math.Max(row.Height, g.RowTemplate.Height);
            }
        }

        private static void StyleItems(ToolStripItemCollection items)
        {
            foreach (ToolStripItem item in items)
            {
                item.ForeColor = RetroPalette.Text;
                var drop = item as ToolStripDropDownItem;
                if (drop != null)
                {
                    drop.DropDown.BackColor = RetroPalette.Ink;
                    StyleItems(drop.DropDownItems);
                }
            }
        }
    }

    /// <summary>Menu and toolbar colours for ToolStripProfessionalRenderer.</summary>
    public class RetroColorTable : ProfessionalColorTable
    {
        public override Color MenuStripGradientBegin => RetroPalette.Ink;
        public override Color MenuStripGradientEnd => RetroPalette.Ink;
        public override Color ToolStripGradientBegin => RetroPalette.Ink;
        public override Color ToolStripGradientMiddle => RetroPalette.Ink;
        public override Color ToolStripGradientEnd => RetroPalette.Ink;
        public override Color ToolStripBorder => RetroTheme.LineOpaque;
        public override Color ToolStripDropDownBackground => RetroPalette.Ink;
        public override Color MenuBorder => RetroTheme.LineOpaque;
        public override Color MenuItemBorder => RetroPalette.Cyan;
        public override Color MenuItemSelected => RetroTheme.HoverCyan;
        public override Color MenuItemSelectedGradientBegin => RetroTheme.HoverCyan;
        public override Color MenuItemSelectedGradientEnd => RetroTheme.HoverCyan;
        public override Color MenuItemPressedGradientBegin => RetroPalette.Ink2;
        public override Color MenuItemPressedGradientEnd => RetroPalette.Ink2;
        public override Color ImageMarginGradientBegin => RetroPalette.Ink;
        public override Color ImageMarginGradientMiddle => RetroPalette.Ink;
        public override Color ImageMarginGradientEnd => RetroPalette.Ink;
        public override Color SeparatorDark => RetroTheme.LineOpaque;
        public override Color SeparatorLight => RetroPalette.Ink;
        public override Color ButtonSelectedHighlight => RetroTheme.HoverCyan;
        public override Color ButtonSelectedGradientBegin => RetroTheme.HoverCyan;
        public override Color ButtonSelectedGradientEnd => RetroTheme.HoverCyan;
        public override Color ButtonSelectedBorder => RetroPalette.Cyan;
        public override Color StatusStripGradientBegin => RetroPalette.Ink;
        public override Color StatusStripGradientEnd => RetroPalette.Ink;
    }

    /// <summary>The seven rainbow speed stripes as a thin bar (default 3 px tall). Dock it to the top of a panel or form.</summary>
    public class StripeBar : Control
    {
        public StripeBar()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw |
                     ControlStyles.UserPaint, true);
            Height = 3;
            TabStop = false;
        }

        protected override Size DefaultSize => new Size(200, 3);

        protected override void OnPaint(PaintEventArgs e)
        {
            IReadOnlyList<Color> stripes = RetroPalette.Stripes;
            for (var i = 0; i < stripes.Count; i++)
            {
                var x0 = Width * i / stripes.Count;
                var x1 = Width * (i + 1) / stripes.Count;
                using (var brush = new SolidBrush(stripes[i]))
                {
                    e.Graphics.FillRectangle(brush, x0, 0, x1 - x0, Height);
                }
            }
        }
    }
}
