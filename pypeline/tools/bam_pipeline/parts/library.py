#!/usr/bin/python
#
# Copyright (c) 2012 Mikkel Schubert <MSchubert@snm.ku.dk>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import os
import types

from pypeline.common.utilities import safe_coerce_to_tuple
from pypeline.node import MetaNode
from pypeline.nodes.picard import MarkDuplicatesNode
from pypeline.nodes.misc import \
     CopyOutputFilesNode
from pypeline.nodes.mapdamage import \
     MapDamagePlotNode, \
     MapDamageModelNode, \
     MapDamageRescaleNode
from pypeline.tools.bam_pipeline.nodes import \
     FilterCollapsedBAMNode, \
     IndexAndValidateBAMNode



class Library:
    """Represents a single library in a BAM pipeline.

    Is reponsible for aggregating per-lane BAMS, removal of PCR duplicates,
    rescaling of quality-scores using mapDamage, as well as running mapDamage
    for QC purposes.

    Properties:
      name      -- Name of the libray (as specified in makefile)
      lanes     -- Tuple of lanes assosisated with the library
      options   -- Makefile options that apply to the current library
      folder    -- Folder containing files assosisated with library. Is used as
                   a prefix for files generated by this class.
      bams      -- Dictionary of BAM filenames -> nodes, for each BAM generated by
                   the Library class. Depending on options, this may either be newly
                   generated files, or the files produced by Lanes.
      mapdamage -- mapDamage plotting node if enabled. This node is not placed within
                   the library dependency tree, since other nodes typically do not
                   depend on it. See Target class.
    """

    def __init__(self, config, target, prefix, lanes, name):
        self.name        = name
        self.lanes       = safe_coerce_to_tuple(lanes)
        self.options     = lanes[0].options
        self.folder      = os.path.dirname(self.lanes[0].folder)
        self.bams        = None
        self.mapdamage   = None

        assert all((self.folder == os.path.dirname(lane.folder)) for lane in self.lanes)
        assert all((self.options == lane.options) for lane in self.lanes)

        lane_bams = self._collect_bams_by_type(self.lanes)

        pcr_duplicates = self.options["PCRDuplicates"]
        if pcr_duplicates:
            lane_bams = self._remove_pcr_duplicates(config, prefix, lane_bams, pcr_duplicates)

        # At this point we no longer need to differentiate between types of reads
        files_and_nodes = self._collect_files_and_nodes(lane_bams)

        self.bams, self.mapdamage = \
          self._build_mapdamage_nodes(config, target, prefix, files_and_nodes)

        self.node = MetaNode(description  = "Library: %s" % os.path.basename(self.folder),
                             dependencies = self.bams.values())


    @classmethod
    def _collect_bams_by_type(cls, lanes):
        bams = {}
        for lane in lanes:
            for key, files in lane.bams.iteritems():
                key = "collapsed" if (key == "Collapsed") else "normal"
                bams.setdefault(key, {}).update(files)
        return bams


    @classmethod
    def _collect_files_and_nodes(cls, bams):
        files_and_nodes = {}
        for dd in bams.itervalues():
            files_and_nodes.update(dd)
        return files_and_nodes


    def _remove_pcr_duplicates(self, config, prefix, bams, strategy):
        rmdup_cls = {"collapsed"  : FilterCollapsedBAMNode,
                     "normal"     : MarkDuplicatesNode}

        keep_duplicates = False
        if isinstance(strategy, types.StringTypes) and (strategy.lower() == "mark"):
            keep_duplicates = True

        results = {}
        for (key, files_and_nodes) in bams.items():
            output_filename = self.folder + ".rmdup.%s.bam" % key
            node = rmdup_cls[key](config       = config,
                                  input_bams   = files_and_nodes.keys(),
                                  output_bam   = output_filename,
                                  keep_dupes   = keep_duplicates,
                                  dependencies = files_and_nodes.values())
            validated_node = IndexAndValidateBAMNode(config, prefix, node)

            results[key] = {output_filename : validated_node}
        return results


    def _build_mapdamage_nodes(self, config, target, prefix, files_and_nodes):
        plot_node = model_node = None
        if self.options["RescaleQualities"]:
            # Basic run of mapDamage, only generates plots / tables, but no modeling
            files_and_nodes, plot_node, model_node = \
              self._rescale_quality_scores(config, self.folder, prefix, self.name, files_and_nodes)

        if not ("mapDamage" in self.options["Features"]):
            return files_and_nodes, None

        # External destination for mapDamage plots / tables
        # Messing with these does not cause the pipeline to re-do other stuff
        destination = os.path.join(config.destination, "%s.%s.mapDamage" % (target, prefix["Name"]), self.name)

        if plot_node:
            # Simply copy existing results to external folder
            plot_node = CopyOutputFilesNode(description  = "mapDamage",
                                            destination  = destination,
                                            source_nodes = (plot_node, model_node))
        else:
            # Results of mapDamage are placed directly in the external folder
            plot_node = \
              self._build_mapdamage_plot_node(config, destination, prefix, self.name, files_and_nodes)

        return files_and_nodes, plot_node


    @classmethod
    def _build_mapdamage_plot_node(cls, config, destination, prefix, title, files_and_nodes):
        return MapDamagePlotNode(config           = config,
                                 reference        = prefix["Path"],
                                 input_files      = files_and_nodes.keys(),
                                 output_directory = destination,
                                 title            = "mapDamage plot for library %r" % (title,),
                                 dependencies     = files_and_nodes.values())


    @classmethod
    def _rescale_quality_scores(cls, config, destination, prefix, plot_title, files_and_nodes):
        # Generate plot / table files in internal tree in order to prevent the
        # user from accidentially messing with them / causing re=runs
        md_directory  = "%s.mapDamage" % (destination,)
        output_filename = destination + ".rescaled.bam"

        # Generates basic plots / table files
        plot  = cls._build_mapdamage_plot_node(config, md_directory, prefix, plot_title, files_and_nodes)

        # Builds model of post-mortem DNA damage
        model = MapDamageModelNode(reference     = prefix["Reference"],
                                   directory     = md_directory,
                                   dependencies  = plot)

        # Rescales BAM quality scores using model built above
        scale = MapDamageRescaleNode(config       = config,
                                     reference    = prefix["Reference"],
                                     input_files  = files_and_nodes.keys(),
                                     output_file  = output_filename,
                                     directory    = md_directory,
                                     dependencies = model)

        # Grab indexing and validation nodes
        validate = IndexAndValidateBAMNode(config, prefix, scale).subnodes

        node = MetaNode(description = "Rescale Qualities",
                        subnodes    = (plot, model, scale) + tuple(validate),
                        dependencies = files_and_nodes.values())

        return {output_filename : node}, plot, model
