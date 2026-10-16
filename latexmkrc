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
