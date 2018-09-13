#!/usr/bin/env python
from __future__ import print_function

import argparse
import sys
from collections import OrderedDict

from pygtftk.arg_formatter import FileWithExtension
from pygtftk.biomart import Biomart
from pygtftk.cmd_object import CmdObject
from pygtftk.gtf_interface import GTF
from pygtftk.utils import message, write_properly

__updated__ = "2018-01-20"

__doc__ = """
 Select lines/genes from a GTF file using a Gene Ontology ID (e.g GO:0097194).
"""


def make_parser():
    """The program parser."""
    parser = argparse.ArgumentParser(add_help=True)

    parser.add_argument('-i', '--inputfile',
                        help="Path to the GTF file. Default to STDIN",
                        default=sys.stdin,
                        metavar="GTF",
                        type=FileWithExtension('r',
                                               valid_extensions='\.[Gg][Tt][Ff](\.[Gg][Zz])?$'))

    parser.add_argument('-o', '--outputfile',
                        help="Output file.",
                        default=sys.stdout,
                        metavar="GTF",
                        type=FileWithExtension('w',
                                               valid_extensions='\.[Gg][Tt][Ff]$'))

    parser.add_argument('-g', '--go-id',
                        help='The GO ID (with or without "GO:" prefix).',
                        default="GO:0003700",
                        type=str,
                        required=False)

    parser_mut = parser.add_mutually_exclusive_group(required=True)

    parser_mut.add_argument('-l', '--list-datasets',
                            help='Do not select lines. Only get a list of available datasets/species.',
                            action="store_true",
                            required=False)

    parser_mut.add_argument('-s', '--species',
                            help='The dataset/species.',
                            default=None,
                            type=str,
                            required=False)

    parser.add_argument('-n', '--invert-match',
                        help='Not/invert match.',
                        action="store_true")

    parser.add_argument('-p1', '--http-proxy',
                        help='Use this http proxy (not tested/experimental).',
                        default='',
                        type=str,
                        required=False)

    parser.add_argument('-p2', '--https-proxy',
                        help='Use this https proxy (not tested/experimental).',
                        default='',
                        type=str,
                        required=False)
    return parser


XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "0" uniqueRows = "0" count = "" datasetConfigVersion = "0.6" >
            
    <Dataset name = "{species}_gene_ensembl" interface = "default" >
        <Filter name = "go_parent_term" value = "{go}"/>
        <Attribute name = "ensembl_gene_id" />
    </Dataset>
</Query>"""


def select_by_go(inputfile=None,
                 outputfile=None,
                 go_id=None,
                 https_proxy=None,
                 http_proxy=None,
                 list_datasets=None,
                 species=None,
                 invert_match=False,
                 tmp_dir=None,
                 logger_file=None,
                 verbosity=0):
    """ Select lines from a GTF file based using a Gene Ontology ID (e.g GO:0050789).
    """

    if not go_id.startswith("GO:"):
        go_id = "GO:" + go_id

    is_associated = OrderedDict()

    bm = Biomart(http_proxy=http_proxy,
                 https_proxy=https_proxy)

    bm.get_datasets('ENSEMBL_MART_ENSEMBL')

    if list_datasets:
        for i in sorted(bm.datasets):
            write_properly(i.replace("_gene_ensembl", ""), outputfile)
        sys.exit()
    else:
        if species + "_gene_ensembl" not in bm.datasets:
            message("Unknow dataset/species.", type="ERROR")

    bm.query({'query': XML.format(species=species, go=go_id)})

    for i in bm.response.content.decode().split("\n"):
        i = i.rstrip("\n")
        if i != '':
            is_associated[i] = 1

    gtf = GTF(inputfile)

    gtf_associated = gtf.select_by_key("gene_id",
                                       ",".join(list(is_associated.keys())),
                                       invert_match)

    gtf_associated.write(outputfile)


def main():
    """The main function."""
    myparser = make_parser()
    args = myparser.parse_args()
    args = dict(args.__dict__)
    select_by_go(**args)


if __name__ == '__main__':
    main()


else:

    test = '''
    # Select_by_go all
    @test "select_by_go_1" {
     result=`gtftk select_by_go -i  pygtftk/data/mini_real/mini_real.gtf.gz  -s hsapiens | gtftk tabulate -uH -k gene_name | wc -l`
      [ "$result" -gt 50 ]
    }
    
    '''

    CmdObject(name="select_by_go",
              message=" Select lines from a GTF file using a Gene Ontology ID.",
              parser=make_parser(),
              fun=select_by_go,
              group="selection",
              desc=__doc__,
              updated=__updated__,
              test=test)
