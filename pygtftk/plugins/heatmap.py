#!/usr/bin/env python
import argparse
import os
import zipfile
from collections import OrderedDict

from pygtftk.arg_formatter import FileWithExtension
from pygtftk.arg_formatter import float_greater_than_null
from pygtftk.arg_formatter import float_grt_than_null_and_lwr_than_one
from pygtftk.arg_formatter import int_greater_than_null
from pygtftk.cmd_object import CmdObject
from pygtftk.utils import check_r_packages
from pygtftk.utils import chomp
from pygtftk.utils import make_outdir_and_file
from pygtftk.utils import message

R_LIB = 'ggplot2,reshape2,colorRamps,data.table,amap'

__updated__ = "2018-01-20"
__doc__ = """
 Create a heatmap from mk_matrix result. This can be used to visualize coverage around or along a set of genomic features.
"""

__notes__ = """
    -- The program makes call to ggplot (geom_raster). It should be used with a limited number of features (e.g by selecting one transcript per gene). Otherwise it will run in memory issues.
    -- The program proposes various ways to split the dataset (kmeans, global kmeans, equally sized classes, chromosomes, user-defined transcript sets...).
    -- The program also proposes various way to organize the rows inside each sub-panel (mean, median, variance, standard deviation, median absolute deviation, inter-quartile range, maximum, minimum, position with maximum value, user_defined...).
    -- Kmeans and ordering are performed based on the first appearing bigwig. The leading bigwig can be changed using -bo.
"""


def make_parser():
    """The main parser."""

    parser = argparse.ArgumentParser(add_help=True)

    parser_grp = parser.add_argument_group('Arguments')

    parser_grp.add_argument('-i', '--inputfile',
                            help='A zipped of matrix file as produced by mk_matrix.',
                            default=None,
                            metavar='MATRIX',
                            type=FileWithExtension('r', '\.[Zz][Ii][Pp]'),
                            required=True)

    parser_grp.add_argument('-o', '--out-dir',
                            help='Output directory name.',
                            default="heatmap_gtftk",
                            type=str)

    parser_grp.add_argument('-t', '--transcript-file',
                            help="A two columns file with the transcripts"
                                 " of interest and their classes.",
                            default=None,
                            type=argparse.FileType("r"),
                            required=False)

    parser_grp.add_argument('-s', '--order-fun',
                            help="The statistics used for row ordering.",
                            default="mean",
                            choices=["mean", "median", "var",
                                     "sd", "mad", "IQR", "max", "min",
                                     "l_r", "r_l", "user_defined"],
                            type=str,
                            required=False)

    parser_grp.add_argument('-tl', '--to-log',
                            action="store_true",
                            help="Control whether the data should be log2-transform before plotting.",
                            required=False)

    parser_grp.add_argument('-rn', '--show-row-names',
                            action='store_true',
                            help='Show row names (need a limited set of genes).')

    parser_grp.add_argument('-di', '--distance',
                            choices=("pearson", "euclidean", "maximum",
                                     "manhattan", "canberra",
                                     "binary", "abspearson",
                                     "abscorrelation", "correlation", "spearman", "kendall"),
                            default="pearson",
                            help='The distance to be used for k-means clustering.',
                            required=False)

    parser_grp.add_argument('-bo', '--bwig-order-user',
                            help='A comma-separated list indicating bwig ordering.',
                            default=None,
                            required=False)

    parser_grp.add_argument('-y', '--y-factor',
                            help='The factor to use for y/second dimension.',
                            default='eq_sizes',
                            type=str,
                            choices=['kmeans',
                                     'gkmeans',
                                     'eq_sizes',
                                     'chrom',
                                     'tx_classes',
                                     'signal',
                                     'eq_sizes'],
                            required=False)

    parser_grp.add_argument('-yo', '--y-factor-order',
                            help='A comma-separated list indicating y_factor ordering.',
                            default=None,
                            required=False)

    parser_grp.add_argument('-c', '--color-palette',
                            type=str,
                            # default="#FFF7FB,#ECE2F0,#D0D1E6,#A6BDDB,#67A9CF,#3690C0,#02818A,#016450",
                            # default='#1A1835,#15464E,#2B6F39,#757B33,#C17A70,#D490C6,#C3C1F2,#CFEBEF',
                            # default="#0000FF,#00FFFF,#80FF80,#FFFF00,#FF0000",
                            # default="#0000AA,#0000FF,#00FFFF,#80FF80,#FFFF00,#FF0000,#AA0000",
                            # default='#4575b4,#74add1,#abd9e9,#e0f3f8,#fee090,#fdae61,#f46d43,#d73027',
                            # default='#67001f,#b2182b,#d6604d,#f4a582,#fddbc7,#f7f7f7,#d1e5f0,#92c5de,#4393c3,#2166ac,#053061',
                            # default="#2b83ba,#abdda4,#fdae61,#d7191c",
                            # default="#bababa,#f4a582,darkviolet",
                            # default="#0000BF,#0000FF,#0080FF,#00FFFF,#40FFBF,#80FF80,#BFFF40,#FFFF00,#FF8000,#FF0000,#BF0000", #matlab.like2
                            # default="#D58C52,#BF5D4E,#A92E4A,#930047", #
                            # jaime
                            default="#d73027,#fc8d59,#fee090,#e0f3f8,#91bfdb,#253494",
                            help='A set of colors to create an interpolated color palette.',
                            required=False)

    parser_grp.add_argument('-n', '--nb-class',
                            type=int_greater_than_null,
                            default=1,
                            help='Split the dataset into nb class based on mean expression level (exprs) or kmeans.',
                            required=False)

    parser_grp.add_argument('-pw', '--page-width',
                            help='Output pdf file width (inches).',
                            type=float_greater_than_null,
                            default=7,
                            required=False)

    parser_grp.add_argument('-ph', '--page-height',
                            help='Output odf file height (inches).',
                            type=int_greater_than_null,
                            default=7,
                            required=False)

    parser_grp.add_argument('-pf', '--page-format',
                            help='Output file format.',
                            choices=['pdf', 'png'],
                            default='pdf',
                            required=False)

    parser_grp.add_argument('-ti', '--title',
                            help='A title for the diagram.',
                            default="",
                            type=str,
                            required=False)

    parser_grp.add_argument('-xl', '--xlab',
                            help='X axis label.',
                            default="Selected genomic regions",
                            type=str,
                            required=False)

    parser_grp.add_argument('-ml', '--max-line',
                            help='Add a line that underline the maximum values across rows (to be used with --order-fun 5p-3p).',
                            action="store_true",
                            required=False)

    parser_grp.add_argument('-fo', '--force-tx-class',
                            help='Force even if some transcripts from --transcript-file were not found.',
                            action="store_true",
                            required=False)

    parser_grp.add_argument('-ms', '--min-signal',
                            help='All lines without a sum of bin values equal or greater to --min-signal will be deleted.',
                            type=float,
                            default=5,
                            required=False)

    parser_grp.add_argument('-ul',
                            '--upper-limit',
                            type=float_grt_than_null_and_lwr_than_one,
                            default=0.95,
                            help='Upper limit based on quantile computed from unique values.',
                            required=False)

    parser_grp.add_argument('-nm',
                            '--normalization-method',
                            choices=['none', 'pct'],
                            default='none',
                            help='The normalization method : pct = (x_i - min(x))/(max(x) - min(x)).',
                            required=False)

    parser_grp.add_argument('-if', '--user-img-file',
                            help="Provide an alternative path for the image.",
                            default=None,
                            type=argparse.FileType("w"),
                            required=False)

    parser_grp.add_argument('-ry', '--rotate-y-label',
                            help="Rotate the y label",
                            type=int,
                            default=0,
                            required=False)

    parser_grp.add_argument('-rx', '--rotate-x-label',
                            help="Rotate the x label",
                            type=int,
                            default=0,
                            required=False)
    return parser


def heatmap(inputfile=None,
            out_dir=None,
            transcript_file=None,
            order_fun=None,
            to_log=True,
            show_row_names=None,
            upper_limit=1,
            rotate_y_label=False,
            rotate_x_label=False,
            distance=None,
            bwig_order_user=None,
            y_factor=None,
            y_factor_order=None,
            nb_class=None,
            normalization_method='',
            color_palette=None,
            title='',
            page_width=7,
            min_signal=1,
            page_height=7,
            page_format='pdf',
            user_img_file=None,
            max_line=False,
            tmp_dir=None,
            xlab="Selected genomic regions",
            logger_file=None,
            verbosity=False,
            force_tx_class=None
            ):
    # -------------------------------------------------------------------------
    #
    # Check args
    #
    # -------------------------------------------------------------------------

    if order_fun == "user_defined":
        if y_factor != 'tx_classes':
            message("if --order-fun is set to 'user_defined',"
                    " --y-factor should be set to 'tx_classes'.",
                    type="ERROR")

    if transcript_file is not None:
        if y_factor != 'tx_classes':
            message("if providing a transcript file"
                    " --y-factor should be set to 'tx_classes'.",
                    type="ERROR")

    # -------------------------------------------------------------------------
    #
    # We need some R packages
    #
    # -------------------------------------------------------------------------

    message("Checking R package.")
    check_r_packages(R_LIB.split(","))

    # -------------------------------------------------------------------------
    #
    # Convert some args
    #
    # -------------------------------------------------------------------------

    if show_row_names:
        show_row_names = "T"
    else:
        show_row_names = "F"

    if to_log:
        to_log = "T"
    else:
        to_log = "F"

    if max_line:
        max_line = "T"
    else:
        max_line = "F"

    # -------------------------------------------------------------------------
    #
    # Input and output should not be the same (see yasmina issue)
    #
    # -------------------------------------------------------------------------

    if not inputfile.name.endswith('.zip'):
        message("Not a valid zip file (*.zip).", type="ERROR")

    base_input = os.path.split(os.path.abspath(inputfile.name))[1]
    base_input = base_input.replace(".zip", "")
    base_output = os.path.split(os.path.abspath(out_dir))[1]

    if base_output in [base_input, base_input]:
        message("The input file and output directory should have different names.",
                type="ERROR")

    # -------------------------------------------------------------------------
    #
    # Unzipping input file
    #
    # -------------------------------------------------------------------------

    dir_name = os.path.dirname(os.path.abspath(inputfile.name))

    message("Uncompressing in directory :" + dir_name,
            type="DEBUG")
    # input_zip = zipfile.ZipFile(inputfile.name, "r")
    # input_zip = input_zip.extractall()

    try:
        with zipfile.ZipFile(inputfile.name) as zf:
            zf.extractall(dir_name)
    except:
        message("Problem encountered when unzipping...",
                type="ERROR")
    inputfile_main = open(os.path.join(dir_name, zf.namelist()[0]), "r")
    message("Reading from file:" + inputfile_main.name,
            type="DEBUG")

    # -------------------------------------------------------------------------
    #
    # Retrieving info from the matrix file
    #
    # -------------------------------------------------------------------------

    message("Getting configuration info from input file.")

    input_file_tx = set()
    infile_chrom = set()
    infile_bwig = set()
    header = ""

    for line_number, line in enumerate(inputfile_main):

        # comment (line 0)
        if line_number == 0:
            header = chomp(line.lstrip("#"))
            header = header.rstrip(";")
            continue
        # skip header (line 1)
        elif line_number > 1:
            line = chomp(line)
            field = line.split("\t")
            tx_id = field[4]
            chrom = field[1]
            input_file_tx.add(tx_id)
            infile_chrom.add(chrom)
            infile_bwig.add(field[0])

    message("BigWigs found : " + ",".join(list(infile_bwig)))

    # -------------------------------------------------------------------------
    #
    # Parse the header
    #
    # -------------------------------------------------------------------------
    header = [x.split(":") for x in header.split(";")]

    config = dict()
    for x in header:
        config[x[0]] = x[1]

    # -------------------------------------------------------------------------
    #
    # Check arguments: --transcript-file
    #
    # -------------------------------------------------------------------------

    tx_to_class = OrderedDict()
    tx_class_list = OrderedDict()

    if y_factor == 'tx_classes':
        if transcript_file is not None:

            transcript_file_nm = transcript_file.name

            message("Reading transcript class file (--transcript_file).")

            for line in transcript_file:
                if line in ('\n', '\r\n'):
                    continue

                line = chomp(line)
                fields = line.split("\t")
                tx_name = fields[0].strip()

                try:
                    tx_to_class[tx_name] = chomp(fields[1])
                    tx_class_list[fields[1]] = 1
                except:
                    message("The file provided to --target-tx-file"
                            " should contain two columns (transcript and "
                            "class).", type="ERROR")

            nb_class = len(list(set(tx_class_list.keys())))

            if nb_class == 0:
                message("No transcript found in file provided through "
                        "--target-tx-file.", type="ERROR")

            else:
                message("Found : " + str(nb_class) + " classes.")

            # ------------------------------------------------------------------
            # Check the transcripts are found in the GTF...
            # ------------------------------------------------------------------

            intersect = set(tx_to_class.keys()).intersection(input_file_tx)
            nb_intersect = len(intersect)

            if nb_intersect != len(tx_to_class.keys()):
                not_found = list(set(tx_to_class.keys()) - input_file_tx)
                message(not_found[0] + "...", type="WARNING")

                if force_tx_class:
                    msg_type = "WARNING"
                else:
                    msg_type = "ERROR"

                message("Some transcripts (n={n}) from --transcript-class where not"
                        " found in input file (overriden with --force-tx-class).".format(
                    n=len(not_found)),
                    type=msg_type)

                if force_tx_class:
                    tx_to_class = {
                        k: tx_to_class[k] for k in tx_to_class if k in intersect}
                    nb_class = len(list(set(tx_to_class.values())))

                    if nb_class == 0:
                        message("No transcript found in file provided through "
                                "--target-tx-file.", type="ERROR")

            else:
                message("Found %d transcripts of interest in "
                        "input file." % nb_intersect)
        else:
            message(
                "Please provide --transcript-file if --x-factor or "
                "--y-factor is set to tx_classes.",
                type="ERROR")
    else:
        transcript_file_nm = ''

    # -------------------------------------------------------------------------
    #
    # Check factor ordering args.
    #
    # -------------------------------------------------------------------------

    # bwig_order_user
    if bwig_order_user is None:

        bwig_order = ",".join(list(infile_bwig))
    else:

        if any(
                [True for x in bwig_order_user.split(",") if x not in infile_bwig]):
            message("Fix --bwig-order. Unknown bwig. Should be one of: " + ",".join(infile_bwig),
                    type="ERROR")
        if len(set(bwig_order_user.split(","))) != len(
                bwig_order_user.split(",")):
            message("Fix --bwig-order. Duplicates not allowed.",
                    type="ERROR")
        if any([x not in infile_bwig for x in bwig_order_user.split(",")]):
            message("Fix --bwig-order. Some bigwigs were not found.",
                    type="ERROR")

        bwig_order = bwig_order_user

    # y factor
    if y_factor == 'tx_classes':
        if y_factor_order is None:
            y_factor_order = ",".join(tx_class_list.keys())
        else:
            if len(set(y_factor_order.split(","))) > len(tx_class_list.keys()):
                message("Fix --y-factor-order. Unknown item or duplicates.",
                        type="ERROR")

            if any([x not in tx_class_list.keys()
                    for x in y_factor_order.split(",")]):
                message("Fix --y-factor-order. Some items were not found.",
                        type="ERROR")

            if len(y_factor_order.split(",")) != len(tx_class_list.keys()):
                message("Fix --y-factor-order. Some classes are lacking.",
                        type="ERROR")

    if y_factor == 'chrom':

        if y_factor_order is None:
            y_factor_order = ",".join(list(infile_chrom))
        else:
            if len(set(y_factor_order.split(","))) > len(infile_chrom):
                message("Fix --y-factor-order. Unknown item or duplicates.",
                        type="ERROR")

            if any([x not in infile_chrom for x in y_factor_order.split(",")]):
                message("Fix --y-factor-order. Some items were not found.",
                        type="ERROR")

            if len(y_factor_order.split(",")) != len(infile_chrom):
                message("Fix --y-factor-order. Some classes are lacking.",
                        type="ERROR")

    elif y_factor in ['signal', 'eq_sizes', 'kmeans', 'gkmeans']:
        if y_factor_order is not None:
            message("--y-factor-order can not be set if --y-factor is ''signal', 'eq_sizes' or 'kmeans'.",
                    type="WARNING")
        y_factor_order = ""
        if y_factor == 'gkmeans':
            if len(infile_bwig) == 1:
                y_factor = 'kmeans'
                message("Only one bigwig found. Changed 'gkmeans' to 'kmeans'.",
                        type="WARNING")

    # -------------------------------------------------------------------------
    #
    # Colors for profiles
    #
    # -------------------------------------------------------------------------

    # Colors for the heatmap
    color_palette_list = color_palette.split(",")
    if len(color_palette_list) < 2:
        message("Need more than 2 colors for heatmap color palette.",
                type="ERROR")

    # -------------------------------------------------------------------------
    #
    # Prepare output files
    #
    # -------------------------------------------------------------------------

    img_file = config['ft_type'] + "_u%s_d%s." + page_format
    img_file = img_file % (config['from'], config['to'])

    file_out_list = make_outdir_and_file(out_dir,
                                         [img_file,
                                          "R_diagram_code.R",
                                          "transcript_order_and_class.txt"],
                                         force=True)

    img_file, r_code_file, tx_order_file_out = file_out_list

    if user_img_file is not None:
        os.unlink(img_file.name)
        img_file = user_img_file
        if not img_file.name.endswith(page_format):
            msg = "Image format: {f}. Please fix.".format(f=page_format)
            message(msg, type="ERROR")

    # ------------------------------------------------------------------
    # Graphics with a call to R
    # ------------------------------------------------------------------

    r_code = """
    ########################################
    # Input variables
    ########################################
    
    color.palette <- c("{color_palette}")
    color.palette <- strsplit(color.palette, ",")[[1]]
    show.rownames <- {show_row_names}
    to.log <- {to_log}
    max.line <- {max_line}
    order.fun <- '{order_fun}'
    inputfile <- '{inputfile}'
    transcript.file <- '{transcript_file}'
    img.file <- '{img_file}'
    page.width <- {page_width}
    page.height <- {page_height}
    xlab <- '{xlab}'
    title <- '{title}'
    nb_class <- {nb_class}
    min.signal <- {min_signal}
    upper.limit <- {upper_limit}
    normalization.method <- '{normalization_method}'
    rotate_y_label <- {rotate_y_label}
    rotate_x_label <- {rotate_x_label}
    # plot type
    ft.type <- '{ft_type}'
    from <- {fr}
    to <- {to}
    
    # bwig_order
    bwig.order <- '{bwig_order}'
    bwig.order <- strsplit(bwig.order, ",")[[1]]
    first.bigwig <- bwig.order[1]

    # y.factor
    y.factor <- '{y_factor}'
    y.factor.order <- '{y_factor_order}'
    y.factor.order <- strsplit(y.factor.order, ",")[[1]]
    if(length(y.factor.order)==0)
        y.factor.order <- ''

    
    # kmeans
    distance <- '{distance}'
    
    ########################################
    # Required packages
    ########################################
    
    suppressWarnings(suppressMessages(library("amap")))
    suppressWarnings(suppressMessages(library("grid")))
    suppressWarnings(suppressMessages(library("reshape2")))
    suppressWarnings(suppressMessages(library("ggplot2")))
    suppressWarnings(suppressMessages(library("colorRamps")))
    suppressWarnings(suppressMessages(library("data.table")))
    
    ########################################
    # Function declaration
    ########################################

        
    # Gtftk-like messages
    message <- function(msg){{
      cat(paste("    |--- ",format(Sys.time(),"%R"), "-INFO : ", msg, "\\n", sep=""), file=stderr())
    }}
    
    # From ggplot2 utilities-break.r
    breaks <- function(x, equal, nbins = NULL, binwidth = NULL) {{
      equal <- match.arg(equal, c("numbers", "width"))
      if ((!is.null(nbins) && !is.null(binwidth)) || (is.null(nbins) && is.null(binwidth))) {{
        stop("Specify exactly one of n and width")
      }}
      
      rng <- range(x, na.rm = TRUE, finite = TRUE)
      if (equal == "width") {{
        if (!is.null(binwidth)) {{
          fullseq(rng, binwidth)
        }} else {{
          seq(rng[1], rng[2], length.out = nbins + 1)
        }}
      }} else {{
        if (!is.null(binwidth)) {{
          probs <- seq(0, 1, by = binwidth)
        }} else {{
          probs <- seq(0, 1, length.out = nbins + 1)
        }}
        stats::quantile(x, probs, na.rm = TRUE)
      }}
      
    }}

    l_r <- function(x, na.rm = FALSE){{
        ind <- which(x == max(x, na.rm = na.rm))[1]
        return(ind)
    }}

    r_l <- function(x, na.rm = FALSE){{
        ind <- which(x == min(x, na.rm = na.rm))[length(x)]
        return(ind)
    }}

    
    ########################################
    # Load dataset
    ########################################
    
    message("Preparing profile diagram.")
    message("Reading input file.")
    
    d <- as.data.frame(fread(inputfile,
                             sep='\\t',
                             header=T,
                             skip=1,
                             showProgress=FALSE))
    
    if(y.factor == 'tx_classes'){{
        # Get the transcript classes
        # and delete duplicate transcripts
        # --------------------------------
        message("Reading transcript file.")
        df_class <- read.table(transcript.file, sep='\\t', head=F, colClasses = "character")
        dup <- duplicated(as.character(df_class[,1]))
        df_class <- df_class[!dup, ]
        tx_ordering <- as.character(df_class[,1])
        tx_classes <- as.character(df_class[,2])
        names(tx_classes)  <- tx_ordering

        # Select the transcript of interest and add class info to the data.frame
        # -----------------------------------------------------------------------
        all_tx <- as.character(d$gene)
        ind <- all_tx %in% tx_ordering
        message(paste("Keeping ",
                      length(unique(all_tx[ind])),
                      " transcript out of ",
                      length(unique(all_tx)),
                      ".", sep=""))
    
        d <- d[ind,]
        all_tx <- as.character(d$gene)
        d <- cbind(tx_classes[all_tx], d)
        colnames(d)[1] <- "tx_classes"
        
    }}else{{
        d <- cbind(1, d)
        colnames(d)[1] <- "tx_classes"
        all_tx <- unique(d$gene)
    }}
    
    # Select the bwig of interest
    # ----------------------------
    
    d <- d[as.character(d[, 'bwig']) %in% bwig.order, ]
    

    # Store level order (pos)
    # ------------------------
    pos.order <- colnames(d)[8:ncol(d)]


    # compute bin number upstream, main, downstream
    # -----------------------------------------------
    bin_nb_main <- length(grep("main", colnames(d)))
    bin_nb_ups <- length(grep("upstream", colnames(d)))
    bin_nb_dws <- length(grep("downstream", colnames(d)))
    bin_nb_total <- bin_nb_ups + bin_nb_main + bin_nb_dws
    

    
    ########################################
    # Delete row without enough signal
    ########################################

    nb_gene_before <- length(all_tx)
    df.tmp <- data.frame(bwig=d$bwig, gene=d$gene, sum=apply(d[,8:ncol(d)], 1, sum), check.names = FALSE)
    df.tmp <- df.tmp[df.tmp$sum > min.signal, ]
    nb_gene_after <- length(unique(as.character(df.tmp$gene)))
    d <- d[d$gene %in% as.character(unique(df.tmp$gene)), ]
    message(paste("Deleted ", nb_gene_before - nb_gene_after,
            " regions (not enough signal, see -ms).", sep=""))

    ########################################
    # Melting
    ########################################
    
    dm <- melt(d[,-c(4,5,7)], id=c('tx_classes', 'bwig','chrom', 'gene'))
    colnames(dm) <-  c('tx_classes', 'bwig', 'chrom', 'gene', 'pos', 'exprs')
    dm[, 'bwig']  <- factor(dm[, 'bwig'], levels=bwig.order, ordered=T)
    

    ########################################
    # ceiling
    ########################################


    if(upper.limit < 1){{
        message('Ceiling')
        for(k in unique(dm$bwig)){{
            tmp <- dm[dm$bwig == k, 'exprs']
            qu <- quantile(unique(as.vector(as.matrix(tmp))), upper.limit)
            tmp[tmp > qu] <- qu
            dm[dm$bwig == k, 'exprs'] <- tmp
        }}
    }}


    ########################################
    # Normalize/transform
    ########################################
    
    if(to.log){{
      
      if(length(dm$exprs[dm$exprs ==0]) > 0){{
        message("Zero value detected. Adding a pseudocount (+1) before log transformation.")
        dm$exprs <- dm$exprs + 1
      }}
      message("Converting to log2.")
      dm$exprs <- log2(dm$exprs)
      ylab <- "log2(Signal)"
      
    }} else{{
       ylab <- "Signal"
    }}

    
    if(normalization.method == 'pct'){{
        message('Normalizing (percentage)')
        for(k in unique(dm$bwig)){{
            tmp <- dm[dm$bwig == k, 'exprs']
            tmp.norm <- (tmp - min(tmp))/(max(tmp) - min(tmp)) * 100
            dm[dm$bwig == k, 'exprs'] <- tmp.norm
        }}
        ylab <- paste("scaled(", ylab, ", %)", sep="")
    }}
        
    ########################################
    # Factor ordering
    ########################################

    bwig_all <- unique(d[,'bwig'])

    if(y.factor == 'gkmeans'){{
      set.seed(123)
      message(paste("Performing global kmeans  with : ",
              nb_class, " classes", sep=""))
      d.split <- split(d[, 8:ncol(d)], d$bwig)
      rn  <- split(d$gene, d$bwig)
      for(i in 1:length(d.split)){{
        rownames(d.split[[i]]) <- rn[[i]]
      }}
      km.data <- d.split[[1]]
      for(i in 2:length(d.split)){{
        km.data <- cbind( km.data, d.split[[i]][rownames(km.data),])
      }}

      km <- Kmeans(km.data,
                   centers=nb_class,
                   method = distance,
                   iter.max = 100)
      km.order <- km$cluster
      names(km.order) <- rownames(km.data)
      dm$gkmeans <- km.order[dm$gene]
      y.factor.order <- sort(unique(km.order[dm$gene]))
      
    }}

    if(y.factor == 'kmeans'){{
      set.seed(123)
      message(paste("Performing kmeans (based on ", first.bigwig[1],
              " signal) with : ",
              nb_class, " classes", sep=""))
      km.data <- d[d[,'bwig'] == first.bigwig[1], 8:ncol(d)]
      rownames(km.data) <- d[d[,'bwig'] == first.bigwig[1], 'gene']
      km <- Kmeans(km.data,
                   centers=nb_class,
                   method = distance,
                   iter.max = 100)
      km.order <- km$cluster
      names(km.order) <- rownames(km.data)
      dm$kmeans <- km.order[dm$gene]
      y.factor.order <- sort(unique(km.order[dm$gene]))

    }}
    

    # by signal / eq_sizes
    if(y.factor == 'signal'){{

      if(nb_class > 1){{
          signal <- apply(d[d[,'bwig'] == first.bigwig[1],
                          8:ncol(d)], 1,  get(order.fun))
          cut_signal <- cut(signal, breaks=nb_class)
          names(cut_signal) <- d[d[,'bwig'] == first.bigwig[1], 'gene']
          dm$signal <- cut_signal[dm$gene]
          y.factor.order <- rev(sort(unique(cut_signal[dm$gene])))

          
      }}else{{
        cut_signal <- 1
        dm$signal <- cut_signal
        y.factor.order <- '1'
      }}
      

    }}

    
    # by eq_sizes
    if(y.factor == 'eq_sizes'){{
      
      if(nb_class > 1){{
        signal <- apply(d[d[,'bwig'] == first.bigwig[1],
                          8:ncol(d)], 1,  get(order.fun))

          brk <- unique(breaks(signal, "n", 5))
          cut_signal <- cut(signal, brk , include.lowest = TRUE)
          names(cut_signal) <- d[d[,'bwig'] == first.bigwig[1], 'gene']
          dm$eq_sizes <- cut_signal[dm$gene]
          y.factor.order <- rev(sort(unique(cut_signal[dm$gene])))

        
      }}else{{
        cut_signal <- 1
        dm$eq_sizes <- cut_signal
        y.factor.order <- '1'
      }}
      
    }}
       


    # Right side strips: groups (tx_classes, chrom) ordering

    dm[, y.factor]  <- factor(dm[, y.factor],
                              levels=y.factor.order, ordered=T)
    
    
    # X axis text ordering
    
    if(ft.type %in% c("transcript","user_regions")){{
      dm$pos <- factor(dm$pos,
                       levels=pos.order,
                       ordered=T)
    }}else{{
      dm$pos <- factor(dm$pos,
                       levels=pos.order,
                       ordered=T)
      levels(dm$pos) <- seq(from= - from, to=to, length.out = length(pos.order))
      dm$pos <- as.double(as.character(dm$pos))
    }}
    
    if(ft.type %in% c("transcript","user_regions")){{
      #continuous scale
      levels(dm$pos) <- seq(0, 100, length.out=bin_nb_total )
      dm$pos <- as.double(as.character(dm$pos))
    }}
    
    ########################################
    # Compute gene ordering
    ########################################
    
    if(order.fun == 'user_defined'){{
        dm[,'gene'] <- factor(dm[,'gene'],
                              levels=rev(tx_ordering), ordered =  TRUE)
    }}else{{
        tx_ordering <- order(apply(d[d[,'bwig'] == first.bigwig[1], 8:ncol(d)],
                            1,  get(order.fun), na.rm = TRUE),
                            decreasing=FALSE)
        tx_ordering <- d[d[,'bwig'] == first.bigwig[1],]$gene[tx_ordering]
        dm[,'gene'] <- factor(dm[,'gene'],
                              levels=tx_ordering, ordered =  TRUE)
    }}
   
    ########################################
    # Plot
    ########################################
    
    message('Plotting')
    p <- ggplot(dm, aes(x = pos, y = gene, fill = exprs))
    p <- p + theme_bw()
    p <- p + geom_raster(na.rm = TRUE)



    color.ramp <- colorRampPalette(c(color.palette))(10)
    p <- p + scale_fill_gradientn(colours = color.ramp,
                                  name="Signal")
    
    p <- p + xlab(xlab)
    p <- p + ylab("Genes")
    
    
    p <- p + theme(   legend.text=element_text(size=6),
                      panel.border=element_blank(),
                      legend.position = "bottom",
                      legend.key = element_rect(colour = "white"),
                      axis.text.y = element_text(colour="grey20",
                                                 size=4),
                      axis.line.x = element_line(size = 0.25,
                                                  linetype = "solid",
                                                  colour="grey20"),
                      axis.text.x = element_text(colour="grey20",
                                                 size=6,angle=65,
                                                 face="plain",
                                                 vjust = 0.3),
                      axis.title.x = element_text(colour="grey20",
                                                  size=8,angle=0,
                                                  face="plain"),
                      axis.title.y = element_text(colour="grey20",
                                                  size=8,angle=90,
                                                  hjust=.5,vjust=1,
                                                  face="plain"),
                      strip.text.y = element_text(size = 7,
                                                  colour = 'white',
                                                  angle = rotate_y_label),
                      strip.text.x = element_text(colour = 'white',
                                                  size = 7,
                                                  angle = rotate_x_label),
                      strip.background = element_rect(colour=NA,
                                                      fill="#606060"),
                      panel.spacing.y=unit(0.4,"lines"),
                      panel.spacing.x=unit(0.4,"lines")
    )


    
    if(!show.rownames){{
      p <- p + theme(axis.text.y = element_blank(),
                     axis.ticks.y=element_blank())
    }}
    


    p <- p + facet_grid(as.formula(paste(y.factor , "~", 'bwig')),
                            scales = "free",
                            space = "free_y")


    if(ft.type %in% c("transcript","user_regions")){{
      
      if(from){{
        
        if(to){{
          ticks <- c(0, bin_nb_ups/2, seq(bin_nb_ups,
                                           bin_nb_main + bin_nb_ups, length.out=11),
                      bin_nb_total - bin_nb_dws/2, bin_nb_total) / bin_nb_total * 100
          labels <- c(- from,  round(- from/2,0),
                      paste(seq(0,100, length.out=11), "%", sep=""), round(to/2,0), to)
        }}else{{
          ticks <- c(0, bin_nb_ups/2,
                      seq(bin_nb_ups,  bin_nb_total, length.out=11)) / bin_nb_total * 100
          labels <- c(- from,round(- from/2,0), paste(seq(0,100, length.out=6), "%", sep=""))
        }}
        
        }}else{{
          
          if(to){{
            ticks <- c(seq(0, bin_nb_main, length.out=11),
                        bin_nb_total - bin_nb_dws/2, bin_nb_total) / bin_nb_total * 100
            labels <- c(paste(seq(0,100, length.out=6), "%", sep=""), to/2, to)
          }}else{{
            ticks <- seq(from=0, to=bin_nb_total, length.out=6) / bin_nb_total * 100
            labels <- paste(seq(0,100, length.out=6), "%", sep="")
          }}
          
        }}
    
        p <- p + scale_x_continuous(expand=c(0,0), breaks=ticks, labels=labels)

    }}else{{
        p <- p + scale_x_continuous(expand = c(0,0))
    }}
     
     
    
     
    ########################################
    # Output
    ########################################
    #p <- p +  theme(panel.grid.major = element_line(colour = "gray"))
    
    # Output
    # -------------------

    ggsave(filename=img.file,
           plot=p,
           width=page.width,
           height=page.height)

    message("Plot saved..")

    # transcript order and class
    # --------------------------
    message("Writing transcript classes.")
    tmp <- dm[dm$bwig == first.bigwig[1], y.factor]
    names(tmp) <- dm[dm$bwig == first.bigwig[1], 'gene']
    d.out <- data.frame(row.names=1:length(tx_ordering),
                        transcript=tx_ordering,
                        class= tmp[tx_ordering],
                        check.names = FALSE)
    write.table(d.out, file='{tx_order_file_out}',
                row.names = FALSE,
                sep='\\t', quote=F)

    """.format(ft_type=config['ft_type'],
               fr=config['from'],
               to=config['to'],
               inputfile=inputfile_main.name,
               img_file=img_file.name,
               rotate_y_label=rotate_y_label,
               rotate_x_label=rotate_x_label,
               page_width=page_width,
               page_height=page_height,
               transcript_file=transcript_file_nm,
               to_log=to_log,
               order_fun=order_fun,
               xlab=xlab,
               title=title,
               bwig_order=bwig_order,
               y_factor=y_factor,
               y_factor_order=y_factor_order,
               color_palette=color_palette,
               show_row_names=show_row_names,
               nb_class=nb_class,
               distance=distance,
               max_line=max_line,
               min_signal=min_signal,
               upper_limit=upper_limit,
               normalization_method=normalization_method,
               tx_order_file_out=tx_order_file_out.name)

    message("Printing R code to: " + r_code_file.name)

    r_code_file.write(r_code)
    r_code_file.close()

    message("Executing R code.")

    # Execute R code.
    os.system("cat " + r_code_file.name + "| R --slave")


if __name__ == '__main__':

    myparser = make_parser()
    args = myparser.parse_args()
    args = dict(args.__dict__)
    heatmap(**args)

else:

    test = '''

    #heatmap: prepare dataset
    @test "heatmap_1" {
     result=`gtftk get_example -d mini_real -f '*'; gtftk overlapping -i mini_real.gtf.gz -c hg38.genome  -n > mini_real_noov.gtf; gtftk random_tx -i mini_real_noov.gtf  -m 1 -s 123 > mini_real_noov_rnd_tx.gtf`
      [ -s "hg38.genome" ]
    }

    #heatmap: make mini_real_promoter
    @test "heatmap_2" {
     result=`gtftk mk_matrix -i mini_real_noov_rnd_tx.gtf -d 5000 -u 5000 -w 200 -c hg38.genome  -l  H3K4me3,H3K79me,H3K36me3 ENCFF742FDS_H3K4me3_K562_sub.bw ENCFF947DVY_H3K79me2_K562_sub.bw ENCFF431HAA_H3K36me3_K562_sub.bw -o mini_real_promoter`
      [ -s "mini_real_promoter.zip" ]
    }

    #heatmap: make mini_real_promoter
    @test "heatmap_3" {
     result=`gtftk heatmap -D -i mini_real_promoter.zip -o heatmap_prom_1 -tl -pf png -if example_10.png`
      [ -s "example_10.png" ]
    }

    #heatmap: make mini_real_promoter
    @test "heatmap_4" {
     result=`gtftk heatmap -D -i mini_real_promoter.zip -o heatmap_prom_2  -tl  -n 5 --y-factor kmeans -ul 0.9 -nm pct -pf png -if example_11.png -c "#e66101,#fdb863,#f7f7f7,#b2abd2,#5e3c99"`
      [ -s "example_11.png" ]
    }
        
    #heatmap: make mini_real_promoter
    @test "heatmap_5" {
     result=`gtftk heatmap -D -i mini_real_promoter.zip -o heatmap_prom_3  -tl  -n 5 --bwig-order-user  H3K36me3,H3K4me3,H3K79me --y-factor kmeans -ul 0.75 -nm pct -pf png -if example_12.png`
      [ -s "example_12.png" ]
    }
    
    #heatmap: make mini_real_promoter
    @test "heatmap_6" {
     result=`gtftk heatmap -D -i mini_real_promoter.zip -o heatmap_prom_4 -n 5 -tl --bwig-order-user  H3K36me3,H3K4me3,H3K79me --y-factor gkmeans -s max -ul 0.75 -nm pct -pf png -if example_13.png`
      [ -s "example_13.png" ]
    }
        
    
    #heatmap: make mini_real_promoter
    @test "heatmap_7" {
     result=`gtftk heatmap -D -i mini_real_promoter.zip -o heatmap_prom_5 -n 5 -tl --y-factor eq_sizes  -s mean -ul 0.75 -nm pct -pf png -if example_14.png -c "#0000AA,#0055FF,#00AAFF,#40FFFF,#80FFBF,#BFFF80,#FFFF40,#FFAA00,#FF5500,#AA0000"`
      [ -s "example_14.png" ]
    }

    #heatmap: make mini_real_promoter
    @test "heatmap_8" {
     result=`gtftk heatmap -D -i mini_real_promoter.zip -o heatmap_prom_6 -n 5 -tl --y-factor eq_sizes  -s l_r -ul 0.75 -nm pct -pf png -if example_15.png`
      [ -s "example_15.png" ]
    }
    

    #heatmap: make mini_real_promoter
    @test "heatmap_9" {
     result=`gtftk tabulate -i mini_real.gtf.gz -k transcript_id,transcript_biotype -Hun | perl -ne  'print if(/(protein_coding)|(lincRNA)/)'  > tx_classes.txt; head -n 100 tx_classes.txt >  tx_classes_100.txt`
      [ -s "tx_classes_100.txt" ]
    }
    
        
    #heatmap: make mini_real_promoter
    @test "heatmap_10" {
     result=` gtftk heatmap  -i mini_real_promoter.zip  -t tx_classes.txt -y tx_classes  -tl  -fo -o hh -s user_defined -c "#F9DA6B,#f03b20"  -pf png -if example_16.png`
      [ -s "example_16.png" ]
    }

    #heatmap: make mini_real_promoter
    @test "heatmap_11" {
     result=`gtftk heatmap  -i mini_real_promoter.zip  -t tx_classes_100.txt -y tx_classes -tl -fo -o hh -s user_defined --show-row-names -c "#c51b7d,#e9a3c9,#fde0ef,#f7f7f7,#e6f5d0,#a1d76a,#4d9221"  -pf png -if example_17.png`
      [ -s "example_17.png" ]
    }
        
    '''

    cmd = CmdObject(name="heatmap",
                    message="Create a heatmap from mk_matrix result.",
                    parser=make_parser(),
                    fun=heatmap,
                    desc=__doc__,
                    updated=__updated__,
                    notes=__notes__,
                    group="coverage",
                    test=test,
                    rlib=R_LIB)
