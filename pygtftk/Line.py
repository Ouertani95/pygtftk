"""
This section contains representation of GTF, TAB and FASTA records (i.e, 'lines').
When iterating over GTF, TAB or FASTA instances, the following objects will be
returned respectively:

    - Feature
    - FieldSet
    - FastaSequence

"""
import sys
from collections import OrderedDict

from cffi import FFI

import pygtftk.utils
import pygtftk.utils
from pygtftk.error import GTFtkError
from pygtftk.utils import write_properly

ffi = FFI()


# ---------------------------------------------------------------
# Classes FieldSet
#
# ---------------------------------------------------------------


class FieldSet(object):
    """A class representating a set of Fields obtained from a splitted line."""

    def __init__(self, ptr=None, size=None, alist=None, ft_type=None):
        """
        :param ptr: A pointer to a gtf line.
        :param alist: A list of string if one want to construct a Feature from a list.

                >>> from  pygtftk.utils import get_example_file
                >>> from pygtftk.gtf_interface import GTF
                >>> a_file = get_example_file()[0]
                >>> a_tab = GTF(a_file).extract_data("gene_id,start")
                >>> n = 0
                >>> for i in a_tab: n += 1
                >>> assert len(i) == 2
                >>> assert i[0] == 'G0010'
                >>> assert i[1] == '184'
                >>> from pygtftk.Line import FieldSet
                >>> assert isinstance(i, FieldSet)
                >>> assert isinstance(list(i), list)

        """
        if ptr is not None:
            self.fields = [ffi.string(ptr[x]) for x in range(size)]
        elif alist is not None:
            self.fields = alist
        else:
            raise GTFtkError('Unsupported type.')
        if ft_type is not None:
            for i in range(len(ft_type)):
                setattr(self, ft_type[i], self.fields[i])

        self.size = len(self.fields)

    def __repr__(self):
        return '\t'.join([str(x) for x in self.fields])

    def __str__(self):
        return self.__repr__()

    def __len__(self):
        return len(self.fields)

    def __getitem__(self, pos=None):
        """Redefining the getter."""
        return self.fields[pos]

    def __setitem__(self, pos, value):
        """Redefining the setter."""
        self.fields[pos] = value

    def format(self, separator="\t"):
        """
        Return a tabulated string.

        :param separator: output field separator.

        :Example:

        >>> from pygtftk.Line import FieldSet
        >>> from pygtftk.utils import TAB
        >>> a = FieldSet(alist=['chr1', '123', '456'])
        >>> assert len(a.format().split(TAB)) == 3


        """
        return separator.join(self.fields)

    def write(self, file_out=None, separator="\t"):
        """Write FieldSet to a file or stdout (if file is None).

        :param separator: output field separator.
        :param file_out: output file object.

        :Example:

        >>> from pygtftk.Line import FieldSet
        >>> from pygtftk.utils import  make_tmp_file
        >>> a = FieldSet(alist=['chr1', '123', '456'])
        >>> f = make_tmp_file()
        >>> a.write(f)
        >>> f.close()
        >>> from pygtftk.utils import  simple_line_count
        >>> assert simple_line_count(f) == 1

        """

        if file_out is not None:
            file_out.write(self.format(separator) + '\n')
        else:
            sys.stdout.write(self.format(separator) + '\n')


# ---------------------------------------------------------------
#
# Classes FastaSequence
#
# ---------------------------------------------------------------


class FastaSequence(object):
    """A class representating a fasta file line."""

    def __init__(self, ptr=None, alist=None, feat="transcript", rev_comp=False):
        """
        :param ptr: A pointer to a fasta sequence.
        :param alist: A list of string if one want to construct a FastaSequence from a list. The list should contain a header and a sequence.

        :Example:

        >>> from pygtftk.Line import FastaSequence
        >>> a = FastaSequence(alist=['>bla', 'AATACAGAGAT','chr21','+', 'BLA', 'NM123', 123, 456, 'transcript'])

        """

        if ptr is not None:

            self.header = ffi.string(ptr.header)
            self.chrom = ffi.string(ptr.seqid)
            self.strand = ptr.strand
            self.gene_id = ffi.string(ptr.gene_id)
            self.transcript_id = ffi.string(ptr.transcript_id)
            self.sequence = ffi.string(ptr.sequence)

            self.start = str(ptr.start)
            self.end = str(ptr.end)
            self.feat = "transcript"

        elif alist is not None:
            self.header = alist[0]
            self.sequence = alist[1]
            self.chrom = alist[2]
            self.strand = alist[3]
            self.gene_id = alist[4]
            self.transcript_id = alist[5]
            self.start = alist[6]
            self.end = alist[7]
            self.feat = feat
        else:
            raise GTFtkError('Unsupported type.')

    def __repr__(self):
        return self.format()

    def __str__(self):
        return self.__repr__()

    def format(self):
        """
        Return a formated fasta sequence.

        :Example:

        >>> from pygtftk.Line import FastaSequence
        >>> a = FastaSequence(alist=['>bla', 'AATACAGAGAT','chr21','+', 'BLA', 'NM123', 123, 456, 'transcript'])
        >>> assert a.sequence == 'AATACAGAGAT'
        >>> assert a.header == '>bla'
        """
        return self.header + "\n" + self.sequence

    def write(self, file_out=None):
        """Write FastaSequence to a file or stdout (if file is None).

        :Example:

        >>> from pygtftk.Line import FastaSequence
        >>> from pygtftk.utils import  make_tmp_file
        >>> a = FastaSequence(alist=['>bla', 'AATACAGAGAT','chr21','+', 'BLA', 'NM123', 123, 456, 'transcript'])
        >>> f = make_tmp_file()
        >>> a.write(f)
        >>> f.close()
        >>> from pygtftk.utils import  simple_line_count
        >>> assert simple_line_count(f) == 2

        """
        if file_out is not None:
            file_out.write(self.format() + '\n')
        else:
            sys.stdout.write(self.format() + '\n')


# ---------------------------------------------------------------
# Classes Feature
#
# ---------------------------------------------------------------


class Feature(object):
    """Class representation of a genomic feature. Corresponds to a GTF line."""

    def __init__(self, ptr=None, alist=None):
        """
        :param ptr: A pointer to a gtf line.
        :param alist: A list if one want to construct a Feature from a list.

        :Example:


        >>> from pygtftk.Line import Feature
        >>> alist = ['chr1','Unknown','transcript', 100, 200]
        >>> from collections import OrderedDict
        >>> d = OrderedDict()
        >>> d['transcript_id'] = 'g1t1'
        >>> d['gene_id'] = 'g1'
        >>> alist +=['.','+','.',d]
        >>> a = Feature.from_list(alist)
        >>> assert a.get_tx_id() == 'g1t1'
        >>> assert a.get_gn_id() == 'g1'


        """

        if ptr is not None:
            self.rank = ptr.rank
            self.nb_key = ptr.attributes.nb
            self.chrom = ffi.string(ptr.field[0])
            self.src = ffi.string(ptr.field[1])
            self.ft_type = ffi.string(ptr.field[2])
            self.start = int(ffi.string(ptr.field[3]))
            self.end = int(ffi.string(ptr.field[4]))
            self.score = ffi.string(ptr.field[5])
            self.strand = ffi.string(ptr.field[6])
            self.frame = ffi.string(ptr.field[7])
            self.attr = OrderedDict()
            for k, v in zip(ptr.attributes.attr[0:self.nb_key], ptr.attributes.attr[0:self.nb_key]):
                self.attr[ffi.string(k.key)] = ffi.string(v.value)
        elif alist is not None:
            self.rank = 1
            self.nb_key = len(alist[8])
            self.chrom = alist[0]
            self.src = alist[1]
            self.ft_type = alist[2]
            self.start = int(alist[3])
            self.end = int(alist[4])
            self.score = alist[5]
            self.strand = alist[6]
            self.frame = alist[7]
            self.attr = alist[8]
        else:
            raise GTFtkError('Arguments alist or ptr should be set.')

    @classmethod
    def from_list(cls,
                  a_list):
        """Create a Feature object from a list.

        :params alist: a list.
        :Example:


        >>> from pygtftk.Line import Feature
        >>> alist = ['chr1','Unknown','transcript', 100, 200]
        >>> from collections import OrderedDict
        >>> d = OrderedDict()
        >>> d['transcript_id'] = 'g1t1'
        >>> d['gene_id'] = 'g1'
        >>> alist +=['.','+','.',d]
        >>> a = Feature.from_list(alist)


        """
        return Feature(alist=a_list)

    def __repr__(self):

        return self.format()

    def __str__(self):
        return self.__repr__()

    def get_tx_id(self):
        """Get value for 'transcript_id' attribute.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> assert feat.get_tx_id() == 'g1t1'

        """

        try:
            return self.attr['transcript_id']
        except:
            return None

    def get_gn_id(self):
        """Get value for 'gene_id' attribute.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> assert feat.get_gn_id() == 'g1'

        """
        return self.attr['gene_id']

    def get_5p_end(self):
        """Get the 5' end of the feature. Returns 'start' if on '+' strand 'end'
        otherwise (one based).

        :Example:


        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> assert feat.get_5p_end() == 100
        >>> from pygtftk.Line import Feature
        >>> from collections import OrderedDict
        >>> a_feat = Feature.from_list(['1','pygtftk', 'exon', '100', '200', '0', '-', '1', OrderedDict()])
        >>> assert a_feat.get_5p_end() == 200
        >>> a_feat = Feature.from_list(['1','pygtftk', 'exon', '100', '200', '0', '+', '1', OrderedDict()])
        >>> assert a_feat.get_5p_end() == 100

        """
        if self.strand == '+':
            return self.start
        elif self.strand == '-':
            return self.end
        else:
            raise GTFtkError("Can not retrieve 5'end "
                             "from an unstranded features.")

    def get_3p_end(self):
        """Get the 3' end of the feature. Returns 'end' if on '+' strand 'start'
        otherwise (one based).

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> assert feat.get_3p_end() == 200

        """
        if self.strand == '+':
            return self.end
        elif self.strand == '-':
            return self.start
        else:
            raise GTFtkError(
                "Can not retrieve 5'end from an unstranded features.")

    def get_attr_names(self):
        """Returns the attribute names from the Feature.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> assert feat.get_attr_names() == ['transcript_id', 'gene_id']

        """
        return self.attr.keys()

    def format(self):
        """
        Returns Feature as a string in gtf file format. Typically
        to write to a gtf file.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> from pygtftk.utils import TAB
        >>> feat = get_example_feature()
        >>> assert len(feat.format().split(TAB)) == 9

        """

        tok_list = list()
        for key, val in self.attr.items():
            tok_list += [key + ' "' + val + '";']

        if pygtftk.utils.ADD_CHR == 1:
            chrom_out = "chr" + self.chrom
        else:
            chrom_out = self.chrom

        token = [chrom_out,
                 self.src,
                 self.ft_type,
                 str(self.start),
                 str(self.end),
                 str(self.score),
                 self.strand,
                 str(self.frame),
                 ' '.join(tok_list)]
        return '\t'.join(token)

    def format_tab(self, attr_list, sep="\t"):
        r"""Returns Feature as a string in tabulated format.

        :param attr_list: the attributes names.
        :param sep: separator.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> a = 'chr1\tUnknown\ttranscript\t100\t200\t.\t+\t.\tg1t1'
        >>> assert feat.format_tab('transcript_id') == a

        """
        if isinstance(attr_list, str):
            attr_list = [attr_list]

        tok = list()
        token = [self.chrom,
                 self.src,
                 self.ft_type,
                 str(self.start),
                 str(self.end),
                 str(self.score),
                 self.strand,
                 str(self.frame)]
        for attr_name in attr_list:
            if self.attr.get(attr_name):
                tok.append(self.attr[attr_name])
            else:
                tok.append('NA')

        token = token + tok
        return sep.join(token)

    def write_bed(self,
                  name=None,
                  format='bed6',
                  outputfile=None):
        """Write the Feature instance in bed format (Zero-based).

        :param name: A string to use as name (Column 4).
        :param format: Format should be one of 'bed/bed6' or 'bed3'. Default to bed6.
        :param outputfile: the file object were data should be printed.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> from pygtftk.utils import make_tmp_file
        >>> from pygtftk.utils import TAB
        >>> from pygtftk.utils import  simple_line_count
        >>> tmp_file =  make_tmp_file()
        >>> feat = get_example_feature()
        >>> feat.write_bed(name="foo", outputfile=tmp_file)
        >>> tmp_file.close()
        >>> for line in open(tmp_file.name): line= line.split(TAB)
        >>> assert line[3] == 'foo'
        >>> assert simple_line_count(tmp_file) == 1
        """

        if format not in ['bed6', 'bed', 'bed3']:
            raise GTFtkError('Unsupported bed format')

        if pygtftk.utils.ADD_CHR == 1:
            chrom_out = "chr" + self.chrom
        else:
            chrom_out = self.chrom

        # bed is 0-based (-1 on start)
        token = [chrom_out,
                 str(int(self.start) - 1),
                 str(self.end)]

        if format == 'bed6' or format == 'bed':
            if name is None:
                raise GTFtkError("Need a name (column 4) to write a BED6 format.")
            token += [name,
                      str(self.score),
                      self.strand]

        pygtftk.utils.write_properly('\t'.join(token), outputfile)

    def write_gtf_to_bed6(self,
                          name=["transcript_id", "gene_id"],
                          sep="|",
                          add_feature_type=False,
                          outputfile=None):
        """Write the Feature instance in bed format (Zero-based). Select the
        key/values to add as a name.

        :param name: The keys that should be used to computed the 'name' column.
        :param sep: The separator used for the name (e.g 'gene_id|transcript_id".
        :param add_feature_type: Add the feature type to the name.
        :param outputfile: the file object were data should be printed.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> from pygtftk.utils import make_tmp_file
        >>> from pygtftk.utils import TAB
        >>> from pygtftk.utils import  simple_line_count
        >>> tmp_file =  make_tmp_file()
        >>> feat = get_example_feature()
        >>> feat.write_gtf_to_bed6(outputfile=tmp_file)
        >>> tmp_file.close()
        >>> for line in open(tmp_file.name): line= line.split(TAB)
        >>> assert len(line) == 6
        >>> assert line[3] == 'g1t1|g1'
        >>> assert simple_line_count(tmp_file) == 1

        """

        if pygtftk.utils.ADD_CHR == 1:
            chrom_out = "chr" + self.chrom
        else:
            chrom_out = self.chrom

        # bed is 0-based (-1 on start)
        token = [chrom_out,
                 str(int(self.start) - 1),
                 str(self.end)]

        name_list = self.get_attr_value(attr_name=name,
                                        upon_none='set_na')

        if add_feature_type:
            name_out = sep.join(name_list + [self.ft_type])
        else:
            name_out = sep.join(name_list)

        token += [name_out,
                  str(self.score),
                  self.strand]

        pygtftk.utils.write_properly('\t'.join(token), outputfile)

    def write_bed_5p_end(self,
                         name=None,
                         format='bed6',
                         outputfile=None):
        """Write the 5p end coordinates of feature in bed format (Zero-based).

        :param outputfile: the output file.
        :param name: The keys that should be used to computed the 'name' column.
        :param format: Format should be one of 'bed/bed6' or 'bed3'. Default to bed6.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> from pygtftk.utils import make_tmp_file
        >>> from pygtftk.utils import TAB
        >>> from pygtftk.utils import  simple_line_count
        >>> tmp_file =  make_tmp_file()
        >>> feat = get_example_feature()
        >>> feat.write_bed_5p_end(name='foo', outputfile=tmp_file)
        >>> tmp_file.close()
        >>> for line in open(tmp_file.name): line= line.split(TAB)
        >>> assert line[1] == '99'
        >>> assert line[2] == '100'
        >>> assert simple_line_count(tmp_file) == 1

        """

        if format not in ['bed6', 'bed', 'bed3']:
            raise GTFtkError('Unsupported bed format')

        if pygtftk.utils.ADD_CHR == 1:
            chrom_out = "chr" + self.chrom
        else:
            chrom_out = self.chrom

        token = [chrom_out,
                 str(int(self.get_5p_end()) - 1),
                 str(self.get_5p_end())]

        if format == 'bed6' or format == 'bed':
            if name is None:
                raise GTFtkError("Need a name (column 4) to write a BED6 format.")
            token += [name,
                      str(self.score),
                      self.strand]

        pygtftk.utils.write_properly('\t'.join(token), outputfile)

    def write_bed_3p_end(self,
                         name=None,
                         format='bed6',
                         outputfile=None):
        """Write the 3p end coordinates of feature in bed format (Zero-based).

        :param outputfile: The output file name.
        :param name: The string to be used as fourth column.
        :param format: Format should be one of 'bed/bed6' or 'bed3'. Default to bed6.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> from pygtftk.utils import make_tmp_file
        >>> from pygtftk.utils import TAB
        >>> from pygtftk.utils import  simple_line_count
        >>> tmp_file =  make_tmp_file()
        >>> feat = get_example_feature()
        >>> feat.write_bed_3p_end(name='foo', outputfile=tmp_file)
        >>> tmp_file.close()
        >>> for line in open(tmp_file.name): line= line.split(TAB)
        >>> assert line[1] == '199'
        >>> assert line[2] == '200'
        >>> assert simple_line_count(tmp_file) == 1

        """

        if pygtftk.utils.ADD_CHR == 1:
            chrom_out = "chr" + self.chrom
        else:
            chrom_out = self.chrom

        if format not in ['bed6', 'bed', 'bed3']:
            raise GTFtkError('Unsupported bed format')

        token = [chrom_out,
                 str(int(self.get_3p_end()) - 1),
                 str(self.get_3p_end())]

        if format == 'bed6' or format == 'bed':
            token += [name,
                      str(self.score),
                      self.strand]

        pygtftk.utils.write_properly('\t'.join(token), outputfile)

    def add_attr(self, key, val):
        """Add an attribute to the Feature instance.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> feat= feat.add_attr("foo", "bar")
        >>> assert feat.get_attr_value('foo') == ['bar']
        """
        self.attr[key] = str(val)

    def add_attr_and_write(self, key, val, outputfile):
        """
        Add a key/attribute record and write to a file.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> from pygtftk.utils import make_tmp_file
        >>> feat = get_example_feature()
        >>> tmp_file =  make_tmp_file()
        >>> feat.add_attr_and_write("foo", "bar", tmp_file)
        >>> tmp_file.close()
        >>> from pygtftk.gtf_interface import  GTF
        >>> gtf = GTF(tmp_file.name, check_ensembl_format=False)
        >>> assert gtf.extract_data("foo", as_list=True) == ['bar']
        """

        tok_list = list()

        for key_cur, val_cur in self.attr.items():
            tok_list.append(''.join([key_cur, ' "', str(val_cur), '";']))

        tok_list.append(''.join([key, ' "', str(val), '";']))

        tok = ' '.join(tok_list)
        token = [self.chrom,
                 self.src,
                 self.ft_type,
                 str(self.start),
                 str(self.end),
                 str(self.score),
                 self.strand,
                 str(self.frame),
                 tok]

        write_properly('\t'.join(token), outputfile)

    def set_attr(self, key, val, upon_none='continue'):
        """Set an attribute value of the Feature instance.

        :param key: The key.
        :param val: The value.
        :param  upon_none: Wether we should 'continue', 'raise' an error or 'set_na'.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> feat.set_attr("gene_id", "bla")
        >>> assert feat.get_gn_id() == 'bla'
        """

        val = str(val)

        if key in self.attr:
            self.attr[key] = str(val)
        elif key in ['chrom', 'seqname', 'seqid']:
            self.chrom = val
        elif key in ['feature', 'ft_type']:
            self.ft_type = val
        elif key == 'start':
            self.start = val
        elif key == 'end':
            self.end = val
        elif key in ['src', 'source']:
            self.src = val
        elif key == 'score':
            self.score = val
        elif key == 'frame':
            self.frame = val
        else:
            if upon_none == 'continue':
                pass
            elif upon_none == 'set_na':
                self.add_attr(key, ".")
            elif upon_none == 'raise':
                pygtftk.utils.message('Attribute ' + key + ' does not exist',
                                      type="ERROR")
            else:
                pygtftk.utils.message('Attribute ' + key + ' does not exist',
                                      type="ERROR")

    def get_attr_value(self, attr_name, upon_none='continue'):
        """Get the value of a basic or extended attribute.

        :param attr_name: Name of the attribute/key.
        :param  upon_none: Wether we should 'continue', 'raise' an error or \
        'set_na'.

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> feat = get_example_feature()
        >>> assert feat.get_attr_value('transcript_id') == ['g1t1']
        >>> assert feat.get_attr_value('chrom') == ['chr1']
        >>> assert feat.get_attr_value('end') == [200]
        >>> assert feat.get_attr_value('bla', upon_none='continue') == [None]

        """

        if isinstance(attr_name, str):
            attr_name = [attr_name]

        if not isinstance(attr_name, list):
            raise GTFtkError('Unsupported type.')

        val_list = []

        for i in attr_name:
            if i in ['chrom', 'seqname', 'seqid']:
                val_cur = self.chrom
            elif i in ['feature', 'ft_type']:
                val_cur = self.ft_type
            elif i == 'start':
                val_cur = self.start
            elif i == 'end':
                val_cur = self.end
            elif i in ['src', 'source']:
                val_cur = self.src
            elif i == 'score':
                val_cur = self.score
            elif i == 'frame':
                val_cur = self.frame
            else:
                val_cur = self.attr.get(i, None)
                if val_cur is None:
                    if upon_none == 'continue':
                        pass
                    elif upon_none == 'raise':
                        raise KeyError('Key not found')
                    elif upon_none == 'set_na':
                        val_cur = '.'
                    else:
                        raise KeyError('upon_none argument should be'
                                       ' continue, raise or set_na.')
            val_list += [val_cur]

        return val_list

    def write(self, file_out="-"):
        """Write Feature to a file or stdout (if file is '-').

        :Example:

        >>> from pygtftk.utils import get_example_feature
        >>> from pygtftk.utils import make_tmp_file
        >>> feat = get_example_feature()
        >>> tmp_file =  make_tmp_file()
        >>> feat.write(tmp_file)
        >>> tmp_file.close()
        >>> from pygtftk.utils import  simple_line_count
        >>> assert simple_line_count(tmp_file) == 1
        """

        if file_out != "-":
            file_out.write(self.format() + '\n')
        else:
            sys.stdout.write(self.format() + '\n')
