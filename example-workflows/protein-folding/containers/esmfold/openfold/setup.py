# Copyright 2021 AlQuraishi Laboratory
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from setuptools import setup, find_packages

from torch.utils.cpp_extension import BuildExtension, CUDAExtension

version_dependent_macros = [
    "-DVERSION_GE_1_1",
    "-DVERSION_GE_1_3",
    "-DVERSION_GE_1_5",
]

extra_cuda_flags = [
    "-std=c++14",
    "-maxrregcount=50",
    "-U__CUDA_NO_HALF_OPERATORS__",
    "-U__CUDA_NO_HALF_CONVERSIONS__",
    "--expt-relaxed-constexpr",
    "--expt-extended-lambda",
]

compute_capabilities = set(
    [
        # (7, 0),  # V100 for p3
        # (8, 0),  # A100 for p4dn
        (7, 5),  # T4 for g4dn        
        (8, 6),  # A10 for g5
    ]
)

cc_flag = []
for major, minor in list(compute_capabilities):
    cc_flag.extend(
        [
            "-gencode",
            "arch=compute_{major}{minor},code=sm_{major}{minor}".format(major=major, minor=minor),
        ]
    )

extra_cuda_flags += cc_flag

setup(
    name="openfold",
    version="1.0.0",
    description="An AWS adaptation of a PyTorch reimplementation of DeepMind's AlphaFold 2",
    author="Brian Loyal",
    author_email="bloyal@amazon.com",
    license="Apache License, Version 2.0",
    url="https://github.com/aqlaboratory/openfold",
    packages=find_packages(exclude=["tests", "scripts"]),
    include_package_data=True,
    package_data={
        "openfold": ["utils/kernel/csrc/*"],
        "": ["resources/stereo_chemical_props.txt"],
    },
    ext_modules=[
        CUDAExtension(
            name="attn_core_inplace_cuda",
            sources=[
                "openfold/utils/kernel/csrc/softmax_cuda.cpp",
                "openfold/utils/kernel/csrc/softmax_cuda_kernel.cu",
            ],
            include_dirs=[
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "openfold/utils/kernel/csrc/",
                )
            ],
            extra_compile_args={
                "cxx": ["-O3"] + version_dependent_macros,
                "nvcc": (
                    ["-O3", "--use_fast_math"]
                    + version_dependent_macros
                    + extra_cuda_flags
                ),
            },
        )
    ],
    cmdclass={"build_ext": BuildExtension},
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
