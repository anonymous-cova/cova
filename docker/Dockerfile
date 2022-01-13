# syntax = docker/dockerfile:1.0-experimental
###
#
# Base Builder
#
###
FROM nvcr.io/nvidia/deepstream:6.0-devel AS base-builder
MAINTAINER anonymouscova

USER root

RUN apt-get update && apt-get install -y \
        automake \
        autotools-dev \
        bison \
        flex \
        libtool \
        gtk-doc-tools \
        unzip \
        zip \
        python3-setuptools \
        python3-wheel \
        ninja-build \
        && rm -rf /var/lib/apt/lists/*

# Install pip
WORKDIR /root
RUN curl -sSLO https://bootstrap.pypa.io/get-pip.py
RUN ln -s -f /usr/bin/python3 /usr/bin/python && python ./get-pip.py

WORKDIR /root/nvidia
COPY nv-tensorrt-repo-ubuntu1804-cuda11.4-trt8.2.0.6-ea-20210922_1-1_amd64.deb nv-tensorrt-repo-ubuntu1804-cuda11.4-trt8.2.0.6-ea-20210922_1-1_amd64.deb
COPY install_trt.sh install_trt.sh
RUN ./install_trt.sh

WORKDIR /root
RUN rm -rf nvidia

# Install common Python packages
RUN python -m pip install meson six numpy wheel setuptools mock future
RUN python -m pip install keras_preprocessing keras_applications --no-deps

###
#
# Build Tensorflow
#
###
FROM base-builder AS tf-builder

WORKDIR /build/tf

# Install bazel
RUN curl -SLO https://github.com/bazelbuild/bazel/releases/download/3.7.2/bazel-3.7.2-installer-linux-x86_64.sh \
        && bash bazel-3.7.2-installer-linux-x86_64.sh \
        && rm bazel-3.7.2-installer-linux-x86_64.sh

# Build Tensorflow
RUN git clone https://github.com/tensorflow/tensorflow.git
WORKDIR tensorflow
RUN git checkout v2.7.0

# As for tensorflow 2.7, TensorRT 8.2 is not supported
RUN git config user.email "anonymouscova@gmail.com" \
    && git config user.name "Anonymous Cova" \
    && git remote add patch https://github.com/christopherbate/tensorflow.git \
    && git fetch patch \
    && git cherry-pick --strategy=recursive -X theirs patch/tftrt-trt-8.2-support

COPY tf_configure.bazelrc .tf_configure.bazelrc
RUN bazel build --config=opt --config=cuda //tensorflow/tools/pip_package:build_pip_package
RUN ./bazel-bin/tensorflow/tools/pip_package/build_pip_package /mnt

###
#
# Build GStreamer
#
###
FROM base-builder AS gst-builder

WORKDIR /build/gst

RUN git config --global http.sslVerify false
RUN git clone https://gitlab.freedesktop.org/gstreamer/gstreamer.git
WORKDIR /build/gst/gstreamer
RUN git checkout 1.19.3
RUN meson -Ddisable_gst_libav=true build
RUN ninja -C build

###
#
# Build CMake
#
###
FROM base-builder AS cmake-builder

WORKDIR /build/cmake

RUN curl -sSLO https://github.com/Kitware/CMake/releases/download/v3.20.1/cmake-3.20.1.tar.gz && tar xvzf cmake-3.20.1.tar.gz
WORKDIR /build/cmake/cmake-3.20.1
RUN ./bootstrap && make -j`nproc`

###
#
# Create final image
#
###
FROM base-builder

RUN apt-get update && apt-get install -y \
        ffmpeg \
        htop \
        && rm -rf /var/lib/apt/lists/*

# Install python modules
RUN python -m pip install \
        notebook \
        tf2onnx \
        pandas \
        matplotlib \
        fabric2 \
        PyYaml

# Install GStreamer
COPY --from=gst-builder /build/gst/gst-build /build/gst/gstreamer
WORKDIR /build/gst/gst-build
RUN ninja -C build install

# Install Tensorflow
COPY --from=tf-builder /mnt/tensorflow-2.7.0-cp36-cp36m-linux_x86_64.whl /mnt/tensorflow-2.7.0-cp36-cp36m-linux_x86_64.whl
RUN python -m pip install /mnt/tensorflow-2.7.0-cp36-cp36m-linux_x86_64.whl && rm /mnt/tensorflow-2.7.0-cp36-cp36m-linux_x86_64.whl

# Install CMake
WORKDIR /build/cmake/cmake-3.20.1
COPY --from=cmake-builder /build/cmake/cmake-3.20.1 /build/cmake/cmake-3.20.1
RUN make install -C /build/cmake/cmake-3.20.1 && rm -rf /build/cmake

# Workaround
RUN python -m pip install --upgrade numpy

# Install Rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y

ENV LD_LIBRARY_PATH /usr/local/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

