FROM public.ecr.aws/aws-genomics/broadinstitute/genomes-in-the-cloud:2.5.7-2021-06-09_16-47-48Z

RUN wget https://corretto.aws/downloads/latest/amazon-corretto-11-x64-linux-jdk.deb \
 && apt-get install -y -f ./amazon-corretto-11-x64-linux-jdk.deb

ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /usr/gitc