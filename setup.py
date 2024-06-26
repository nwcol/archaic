from setuptools import setup


setup(
    name="archaic_project",
    version="2024.1",
    author="Nick Collier",
    author_email="nwcollier@wisc.edu",
    packages=["archaic"],
    entry_points={
        "console_scripts": [
            "make_exon_masks=archaic.workup.make_exon_masks:main",
            "mask_from_vcf=archaic.workup.mask_from_vcf:main",
            "make_mask=archaic.workup.make_mask:main"
        ]
    }
)
