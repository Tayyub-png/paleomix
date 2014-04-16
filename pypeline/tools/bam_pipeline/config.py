#!/usr/bin/python
#
# Copyright (c) 2013 Mikkel Schubert <MSchubert@snm.ku.dk>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import optparse

import pypeline

from pypeline.config import \
     ConfigError, \
     PerHostValue, \
     PerHostConfig


_TARGETS_BY_NAME = ("targets", "prefixes", "samples", "libraries",
                    "lanes", "mapping", "trimming")


def _run_config_parser(argv):
    per_host_cfg = PerHostConfig("bam_pipeline")

    usage_str    = "%prog <command> [options] [makefiles]"
    version_str  = "%%prog %s" % (pypeline.__version__,)
    parser       = optparse.OptionParser(usage = usage_str, version = version_str)
    parser.add_option("--allow-missing-input-files", action = "store_true", default = False,
                      help = "Allow processing of lanes, even if the original input files are no-longer " \
                             "accesible, if for example a network drive is down. This option should be " \
                             "used with care!")

    pypeline.ui.add_optiongroup(parser,
                                ui_default=PerHostValue("quiet"),
                                color_default=PerHostValue("on"))
    pypeline.logger.add_optiongroup(parser, default = PerHostValue("warning"))

    group  = optparse.OptionGroup(parser, "Scheduling")
    group.add_option("--bowtie2-max-threads", type = int, default = PerHostValue(1),
                     help = "Maximum number of threads to use per BWA instance [%default]")
    group.add_option("--bwa-max-threads", type = int, default = PerHostValue(1),
                     help = "Maximum number of threads to use per BWA instance [%default]")
    group.add_option("--max-threads", type = int, default = per_host_cfg.max_threads,
                     help = "Maximum number of threads to use in total [%default]")
    group.add_option("--dry-run", action = "store_true", default = False,
                     help = "If passed, only a dry-run in performed, the dependency "
                            "tree is printed, and no tasks are executed.")
    parser.add_option_group(group)

    group  = optparse.OptionGroup(parser, "Required paths")
    group.add_option("--jar-root", default = PerHostValue("~/install/jar_root", is_path = True),
                     help = "Folder containing Picard JARs (http://picard.sf.net), " \
                            "and GATK (www.broadinstitute.org/gatk). " \
                            "The latter is only required if realigning is enabled. " \
                            "[%default]")
    group.add_option("--temp-root", default = per_host_cfg.temp_root,
                     help = "Location for temporary files and folders [%default/]")
    group.add_option("--destination", default = None,
                     help = "The destination folder for result files. By default, files will be "
                            "placed in the same folder as the makefile which generated it.")
    parser.add_option_group(group)

    group  = optparse.OptionGroup(parser, "Files and executables")
    group.add_option("--list-output-files", action = "store_true", default = False,
                     help = "List all files generated by pipeline for the makefile(s).")
    group.add_option("--list-orphan-files", action = "store_true", default = False,
                     help = "List all files at destination not generated by the pipeline. " \
                            "Useful for cleaning up after making changes to a makefile.")
    group.add_option("--list-executables", action="store_true", default=False,
                     help="List all executables required by the pipeline, "
                          "with version requirements (if any).")
    parser.add_option_group(group)

    group  = optparse.OptionGroup(parser, "Targets")
    group.add_option("--target", dest = "targets", action = "append", default = [],
                     help = "Only execute nodes required to build specified target.")
    group.add_option("--list-targets", default = None, choices = _TARGETS_BY_NAME,
                     help = "List all targets at a given resolution (%s)" \
                        % (", ".join(_TARGETS_BY_NAME),))
    parser.add_option_group(group)

    group  = optparse.OptionGroup(parser, "Misc")
    group.add_option("--jre-option", dest = "jre_options", action = "append", default = PerHostValue([]),
                     help = "May be specified one or more times with options to be passed "
                            "tot the JRE (Jave Runtime Environment); e.g. to change the "
                            "maximum amount of memory (default is -Xmx4g)")
    parser.add_option_group(group)

    return per_host_cfg.parse_args(parser, argv)


def parse_config(argv):
    config, args = _run_config_parser(argv)
    pypeline.ui.set_ui_colors(config.ui_colors)

    config.targets = set(config.targets)

    if config.list_output_files and config.list_orphan_files:
        raise ConfigError("ERROR: Both --list-output-files and --list-orphan-files set!")

    return config, args

