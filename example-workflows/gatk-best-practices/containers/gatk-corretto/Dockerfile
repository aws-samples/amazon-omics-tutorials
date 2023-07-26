FROM public.ecr.aws/aws-genomics/broadinstitute/gatk:4.2.6.1

RUN wget https://corretto.aws/downloads/latest/amazon-corretto-11-x64-linux-jdk.deb \
 && apt-get install -f ./amazon-corretto-11-x64-linux-jdk.deb

WORKDIR /gatk
