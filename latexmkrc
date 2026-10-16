# Put every compilation file (aux, log, toc, synctex, pdf, ...) in build/
$pdf_mode = 1;
$out_dir  = 'build';
$aux_dir  = 'build';

# After a successful build, copy only the final PDF to the project root
$success_cmd = 'internal copy_pdf_to_root %D';
sub copy_pdf_to_root {
    use File::Copy;
    use File::Basename;
    my $pdf = shift;
    copy($pdf, basename($pdf)) or warn "Could not copy $pdf to root: $!\n";
    return 0;
}

# TikZ figures: each Figures/<name>.tex is a standalone LuaLaTeX document (using
# SolutionFigure.cls) compiled to Figures/<name>.pdf (intermediate files go in
# build/figures-aux). latexmk only reruns this when <name>.tex, or a project
# file it reads (e.g. SolutionFigure.cls), changes or when the PDF is missing.
add_cus_dep('tex', 'pdf', 0, 'compile_figure');
sub compile_figure {
    use File::Copy;
    use File::Basename;
    use File::Path qw(make_path);
    my $base = shift;
    my $name = basename($base);
    my $dir  = "$out_dir/figures-aux";
    make_path($dir);
    my $ret = system('lualatex', '-interaction=nonstopmode', '-halt-on-error', '-recorder',
                     "-output-directory=$dir", "$base.tex");
    return $ret if $ret;
    copy("$dir/$name.pdf", "$base.pdf") or die "Could not copy $dir/$name.pdf: $!\n";

    # Register the project files read by the figure (relative paths in the .fls)
    # as extra sources, so that the figure is rebuilt when one of them changes.
    if (open(my $fls, '<', "$dir/$name.fls")) {
        while (<$fls>) {
            next unless /^INPUT\s+(.+?)\s*$/;
            (my $file = $1) =~ s{\\}{/}g;
            $file =~ s{^\./}{};
            next if $file =~ m{^(/|[A-Za-z]:)} || $file eq "$base.tex" || $file =~ m{^\Q$out_dir\E/};
            rdb_ensure_file($rule, $file);
        }
        close($fls);
    }
    return 0;
}
