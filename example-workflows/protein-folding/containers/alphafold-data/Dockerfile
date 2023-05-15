# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM public.ecr.aws/amazonlinux/amazonlinux:2 as build

RUN yum upgrade -y \
  && yum install -y \
  cmake-2.8.12.2 \
  gcc-7.3.1 \
  gcc-c++-7.3.1 \
  git-2.39.2 \
  glibc-static-2.26 \
  gzip-1.5 \
  make-3.82 \
  tar-1.26 \
  unzip-6.0 \
  zlib-devel-1.2.7 \
  && yum clean all \
  && rm -rf /var/cache/yum

ADD hh-suite.tar.gz /tmp/hh-suite
RUN pushd /tmp/hh-suite \
  && cmake -DCMAKE_INSTALL_PREFIX=/opt/hhsuite . \
  && make && make install \
  && popd

ADD kalign.tar.gz /tmp/kalign2
RUN pushd /tmp/kalign2 \
  && ./configure \
  && make && make install \
  && popd

ADD hmmer.tar.gz /tmp/hmmer
RUN pushd /tmp/hmmer/hmmer-* \
  && ./configure \
  && make && make install \
  && popd

FROM public.ecr.aws/amazonlinux/amazonlinux:2

COPY --from=build /opt/hhsuite/bin /usr/bin
COPY --from=build /usr/local/bin /usr/bin
COPY alphafold /app/alphafold
COPY hhsearch.py hmmsearch.py /app/alphafold/alphafold/data/tools/
COPY stereo_chemical_props.txt /app/alphafold/alphafold/common/
COPY create_msa_monomer.py search_templates.py generate_features.py new_pipelines.py /opt/

# Install python and other dependencies
RUN yum upgrade -y \
  && amazon-linux-extras install python3.8 epel \
  && yum install -y \
  unzip-6.0 \
  gzip-1.5 \
  tar-1.26 \
  libgomp-7.3.1 \
  && yum clean all \
  && rm -rf /var/cache/yum \
  && python3.8 -m venv /opt/venv \
  && source /opt/venv/bin/activate \
  && pip install -q --no-cache-dir \
  absl-py==1.4.0 \
  biopython==1.81 \
  dm-tree==0.1.8\
  numpy==1.23.5 \
  pandas==2.0.0 \
  scipy==1.10.1 \
  && pip install --no-cache-dir --no-deps /app/alphafold

ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /home