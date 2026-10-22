# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
#
# Project build settings. The build rules are shared by every solution manual
# and live in the framework folder of the template submodule; outputs stay in
# this project (build/, Figures/*.pdf and main.pdf in this folder).

# Framework folder, relative to this file
$framework_dir = 'template/solution-manual';

use File::Spec;
my $shared = File::Spec->rel2abs("$framework_dir/latexmkrc");
do $shared or die "Could not load $shared: ", ($@ || $!), "\n";

# Project-specific latexmk settings can be added below.

# Completion report: in the Progress section of README.md (between the
# completion report markers) instead of a separate COMPLETION.md
$completion_readme = 'README.md';
$completion_report = '';
