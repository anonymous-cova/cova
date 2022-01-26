# CoVA

## Exploiting Compressed-Domain Analysis to Accelerate Video Analytics

## Installation

### Requirements

 - Docker
 - TensorRT 8.2.0.6 `DEB` package file for installation

### Tested Environment

 - Ubuntu 18.04
 - CUDA 11.5.1

### Building and launching Docker container

One should first download `deepstream` image from [NVIDIA NGC](https://ngc.nvidia.com/catalog/containers/nvidia:deepstream)
Then, build on image on top of it with specified TF and GStreamer version

```
./docker/build.sh
./docker/launch.sh
```
or, pull down the image from DockerHub with the following command
```
docker pull anonymouscova/cova
```

### Setup inside launched Docker container

#### Patch `libavcodec` to entropy decoder
The entropy decoder is built upon modification on libavcodec.
```
git submodule update --init
cd third_parties/FFmpeg
git apply ../../entdec.patch
./configure --enable-shared --disable-static
make -j`nproc` install

cd ../third_parties/gst-libav
meson build
ninja -C build install
```
Once patched `avdec_h264` is installed, it should work as entropy decoder with the combination of `metapreprocess` element.

#### Install CoVA GStreamer plugins
```
cd gst-plugins
```
Build and install all plugins inside the directories
 - gst-cova: Plugin for blob tracking and decode aware frame filtering
 - gst-h264demuxer: Enables data parallel entropy decoding
 - gst-metapreprocess: Process and stacks extracted metadatas
 - ...

#### Install Requirements inside Docker container
- TensorRT for Ubuntu 18.04 from NVIDIA
- rustc

### Running CoVA

#### Training blob extractor

1. Extract metadata and dump them into a file.

```
cd /workspace
./scripts/meta-extractor.sh H264_VIDEO DUMP_PATH
```

2. Generate ground truth label using MOG.
```
python python/generate-mog.py H264_VIDEO
```

3. Pack dump and label into `Tensorflow Record`
```
python python/dump2record DUMP_PATH
```

4. Run training
```
python python/train-blob-extractor.py CUDA RECORD_PATH
```

5. Convert frozen model into TensorRT engine
```
python -m pip install pyinvoke
cd model
python -m invoke tf2trt MODEL_PATH
```

#### Launch CoVA pipeline

1. Write nvinfer configuration file
    - Specify TensorRT engine path
    - Specify batch size, precision, etc...

2. Run CoVA using GStreamer
Since CoVA is written as GStreamer pipeline, user can launch cova using `gst-launch-1.0` comand line tools.
Check example script in `entdec/cova.sh`.

#### Parsing CoVA output
Output blob tracking result and object detection result is collected using Redis server.
Launch the collaborative query processor
```
cd /workspace/collaborative-analyzer
cargo run REDIS_PORT CONFIG_PATH
```

### Demo
#### Compressed Domain Mask Extraction
![demo/demo.gif](https://github.com/anonymous-cova/cova/blob/master/demo/demo.gif?raw=true)
