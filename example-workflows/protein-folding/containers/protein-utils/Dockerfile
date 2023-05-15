FROM public.ecr.aws/amazonlinux/amazonlinux:2 as build

COPY code /tmp/putils

# Install python and other dependencies
RUN amazon-linux-extras install python3.8 \
  && yum upgrade -y \
  && yum install -y \
  unzip-6.0 \
  wget-1.14 \
  && python3.8 -m venv /opt/venv \
  && source /opt/venv/bin/activate \
  && pip install -q --no-cache-dir \
  pandas==2.0.0 \
  numpy==1.24.2 \
  biopython==1.81 \
  /tmp/putils \
  && yum clean all \
  && rm -rf /var/cache/yum \
  && rm -rf /tmp/putils

ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /home