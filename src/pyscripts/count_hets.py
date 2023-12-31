
# Count and print out the number of heterozygotic sites "0/1", "1/0" in a
# .vcf.gz file

import sys

sys.path.insert(0, "c:/archaic/src")

from archaic import vcf_util


def main(file_name, sample):
    heteros = vcf_util.count_hets(file_name, sample)
    return heteros


file_name = str(sys.argv[1])
sample = str(sys.argv[2])
print(main(file_name, sample))
