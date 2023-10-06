FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Eastern

RUN apt update && \
    apt install -y git make g++ python3-pip wget samtools bedtools pigz && \
    ln -s /usr/bin/python3 /usr/bin/python && pip install pandas

RUN git clone --depth 1 --branch v1.3.2 --recurse-submodules \
    https://github.com/DaehwanKimLab/hisat-genotype && \
    cd /hisat-genotype/hisat2 && make

ENV PATH="/hisat-genotype/hisat2:${PATH}"

RUN cd /hisat-genotype && bash setup.sh

ENV PATH="/hisat-genotype:${PATH}"

ENV PYTHONPATH="/hisat-genotype/hisatgenotype_modules"
