# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM public.ecr.aws/amazonlinux/amazonlinux:2 

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV CUDA_VERSION 11.6.2
ENV NVIDIA_REQUIRE_CUDA "cuda>=11.6 brand=tesla,driver>=418,driver<419 brand=tesla,driver>=450,driver<451 brand=tesla,driver>=470,driver<471 brand=unknown,driver>=470,driver<471 brand=nvidia,driver>=470,driver<471 brand=nvidiartx,driver>=470,driver<471 brand=geforce,driver>=470,driver<471 brand=geforcertx,driver>=470,driver<471 brand=quadro,driver>=470,driver<471 brand=quadrortx,driver>=470,driver<471 brand=titan,driver>=470,driver<471 brand=titanrtx,driver>=470,driver<471"
ENV PATH /usr/local/nvidia/bin:/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH /usr/local/nvidia/lib:/usr/local/nvidia/lib64
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility

ENV NVIDIA_PRODUCT_NAME="CUDA"
ENV LIBRARY_PATH /usr/local/cuda/lib64/stubs
ENV CUDA_HOME=/usr/local/cuda-11.6
ENV TMPDIR=/tmp

LABEL com.nvidia.cudnn.version="8.4.0.27-1"

COPY cuda.repo-x86_64 /etc/yum.repos.d/cuda.repo
COPY NGC-DL-CONTAINER-LICENSE /
COPY openfold /opt/openfold
COPY esm /opt/esm
COPY D42D0685.pub /tmp

RUN NVIDIA_GPGKEY_SUM=d0664fbbdb8c32356d45de36c5984617217b2d0bef41b93ccecd326ba3b80c87 \
  && sed '/^Version/d' /tmp/D42D0685.pub > /etc/pki/rpm-gpg/RPM-GPG-KEY-NVIDIA \
  && echo "$NVIDIA_GPGKEY_SUM  /etc/pki/rpm-gpg/RPM-GPG-KEY-NVIDIA" | sha256sum -c --strict - \
  && amazon-linux-extras install python3.8 \
  && yum upgrade -y \
  && yum install -y \
  cuda-cudart-11-6-11.6.55-1 \
  cuda-compat-11-6 \
  cuda-libraries-11-6-11.6.2-1 \
  cuda-nvtx-11-6-11.6.124-1 \
  libnpp-11-6-11.6.3.124-1 \
  libcublas-11-6-11.9.2.110-1 \
  libnccl-2.12.10-1+cuda11.6 \
  cuda-libraries-devel-11-6-11.6.2-1 \
  cuda-minimal-build-11-6-11.6.2-1 \
  libcudnn8-8.4.0.27-1.cuda11.6 \
  libcudnn8-devel-8.4.0.27-1.cuda11.6 \
  git-2.39.2 \
  unzip-6.0 \
  which-2.20 \
  tar-1.26 \
  python38-devel-3.8.16 \
  && echo "/usr/local/nvidia/lib" >> /etc/ld.so.conf.d/nvidia.conf \
  && echo "/usr/local/nvidia/lib64" >> /etc/ld.so.conf.d/nvidia.conf \
  && mkdir --parents /root/.cache/torch/hub/checkpoints \
  && python3.8 -m venv /opt/venv \
  && source /opt/venv/bin/activate \
  && python -m pip install -q --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cu116 \
  torch==1.13.1+cu116 \
  PyYAML==6.0 \
  scipy==1.10.1 \
  biopython==1.81 \
  pandas==2.0.0 \
  matplotlib==3.7.1 \
  omegaconf==2.3.0 \
  ninja==1.11.1 \
  ml-collections==0.1.1 \
  dm-tree==0.1.7 \
  einops==0.6.0 \
  && cd /opt/openfold && python setup.py install \
  && pip install -q --no-cache-dir /opt/esm \
  && yum clean all \
  && rm -rf /var/cache/yum/*

ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /home
