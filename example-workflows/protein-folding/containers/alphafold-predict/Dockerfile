# Original Copyright 2021 DeepMind Technologies Limited
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM public.ecr.aws/amazonlinux/amazonlinux:2

# CUDA Base
ENV NVARCH x86_64
ENV NVIDIA_REQUIRE_CUDA "cuda>=11.6 brand=tesla,driver>=418,driver<419 brand=tesla,driver>=450,driver<451 brand=tesla,driver>=470,driver<471 brand=unknown,driver>=470,driver<471 brand=nvidia,driver>=470,driver<471 brand=nvidiartx,driver>=470,driver<471 brand=geforce,driver>=470,driver<471 brand=geforcertx,driver>=470,driver<471 brand=quadro,driver>=470,driver<471 brand=quadrortx,driver>=470,driver<471 brand=titan,driver>=470,driver<471 brand=titanrtx,driver>=470,driver<471"
ENV NV_CUDA_CUDART_VERSION 11.6.55-1
ENV NV_CUDA_LIB_VERSION 11.6.2-1
ENV CUDA_VERSION 11.6.2
ENV PATH /usr/local/nvidia/bin:/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH /usr/local/nvidia/lib:/usr/local/nvidia/lib64
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility

# CUDA Runtime
ENV NV_NVTX_VERSION 11.6.124-1
ENV NV_LIBNPP_VERSION 11.6.3.124-1
ENV NV_LIBNPP_PACKAGE libnpp-11-6-${NV_LIBNPP_VERSION}
ENV NV_LIBCUBLAS_VERSION 11.9.2.110-1
ENV NV_LIBNCCL_PACKAGE_NAME libnccl
ENV NV_LIBNCCL_PACKAGE_VERSION 2.12.10-1
ENV NCCL_VERSION 2.12.10
ENV NV_LIBNCCL_PACKAGE ${NV_LIBNCCL_PACKAGE_NAME}-${NV_LIBNCCL_PACKAGE_VERSION}+cuda11.6

# CUDA dnn8
ENV NV_CUDNN_VERSION 8.4.0.27-1
ENV NV_CUDNN_PACKAGE libcudnn8-${NV_CUDNN_VERSION}.cuda11.6

ENV NVIDIA_PRODUCT_NAME="CUDA"
ENV LIBRARY_PATH /usr/local/cuda/lib64/stubs
ENV CUDA_HOME=/usr/local/cuda-11.6
ENV TMPDIR=/tmp

LABEL com.nvidia.cudnn.version="${NV_CUDNN_VERSION}"

COPY cuda.repo-x86_64 /etc/yum.repos.d/cuda.repo
COPY NGC-DL-CONTAINER-LICENSE /
COPY alphafold /app/alphafold
COPY D42D0685.pub /tmp/
COPY Mambaforge-Linux-x86_64.sh /tmp/Mambaforge-Linux-x86_64.sh
COPY predict.py /opt/

RUN NVIDIA_GPGKEY_SUM=d0664fbbdb8c32356d45de36c5984617217b2d0bef41b93ccecd326ba3b80c87 \
  && sed '/^Version/d' /tmp/D42D0685.pub > /etc/pki/rpm-gpg/RPM-GPG-KEY-NVIDIA \
  && echo "$NVIDIA_GPGKEY_SUM  /etc/pki/rpm-gpg/RPM-GPG-KEY-NVIDIA" | sha256sum -c --strict - \
  && yum upgrade -y \
  && yum install -y \
  # CUDA Base
  cuda-cudart-11-6-${NV_CUDA_CUDART_VERSION} \
  cuda-compat-11-6 \
  # CUDA Runtime
  cuda-libraries-11-6-${NV_CUDA_LIB_VERSION} \
  cuda-nvtx-11-6-${NV_NVTX_VERSION} \
  ${NV_LIBNPP_PACKAGE} \
  libcublas-11-6-${NV_LIBCUBLAS_VERSION} \
  ${NV_LIBNCCL_PACKAGE} \
  # CUDA devel
  cuda-libraries-devel-11-6-${NV_CUDA_LIB_VERSION} \
  cuda-minimal-build-11-6-${NV_CUDA_LIB_VERSION} \
  # CUDA dnn8
  ${NV_CUDNN_PACKAGE} \
  # Other
  git-2.39.2 \
  unzip-6.0 \
  which-2.20 \
  tar-1.26 \
  wget-1.14 \
  rsync-3.1.2 \
  patch-2.7.1 \
  && echo "/usr/local/nvidia/lib" >> /etc/ld.so.conf.d/nvidia.conf \
  && echo "/usr/local/nvidia/lib64" >> /etc/ld.so.conf.d/nvidia.conf \
  && bash /tmp/Mambaforge-Linux-x86_64.sh -b -p "/opt/conda" \
  && source "/opt/conda/etc/profile.d/conda.sh" \
  && source "/opt/conda/etc/profile.d/mamba.sh" \  
  && rm /tmp/Mambaforge-Linux-x86_64.sh \
  && /opt/conda/bin/mamba config --set ssl_verify False \
  && /opt/conda/bin/mamba install -c conda-forge \
  conda-content-trust \
  charset-normalizer \
  && /opt/conda/bin/mamba clean -afy \
  && /opt/conda/bin/mamba install -y -c conda-forge \
  openmm=7.5.1 \    
  cudatoolkit=11.6.0 \
  pdbfixer=1.7 \
  pip=23.0.1 \
  python=3.9.16 \
  && /opt/conda/bin/pip install -q --no-cache-dir \
  absl-py==1.0.0 \
  biopython==1.79 \
  chex==0.0.7 \
  dm-haiku==0.0.9 \
  dm-tree==0.1.6 \
  docker==5.0.0 \
  immutabledict==2.0.0 \
  jax==0.3.25 \
  matplotlib==3.6.3 \
  ml-collections==0.1.0 \
  numpy==1.21.6 \
  pandas==1.3.4 \
  protobuf==3.20.1 \
  scipy==1.7.0 \
  tensorflow-cpu==2.9.0 \
  && /opt/conda/bin/pip install -q --no-cache-dir \
  jax==0.3.25  \
  jaxlib==0.3.25+cuda11.cudnn805 \
  -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html \
  && /opt/conda/bin/pip install -q --no-cache-dir --no-deps /app/alphafold \
  # Apply OpenMM patch.
  && cd /opt/conda/lib/python3.9/site-packages && patch -p0 < /app/alphafold/docker/openmm.patch \
  && yum clean all \
  && rm -rf /var/cache/yum \
  && /opt/conda/bin/mamba clean -afy

COPY stereo_chemical_props.txt /opt/conda/lib/python3.9/site-packages/alphafold/common/
ENV PATH="/opt/conda/bin:$PATH"
WORKDIR /home