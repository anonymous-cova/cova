#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 BATCH"
    exit -1
fi

# LOCATION=/ssd4/high/archie-day/day2.mp4
LOCATION=/ssd4/test/short.mp4
# LOCATION=/ssd4/test/6h.mp4
CC=3
MINHITS=45
MAXAGE=45
DEBUG=FALSE


GST_DEBUG=xvdec:4 \
gst-launch-1.0 \
    filesrc location=${LOCATION} ! qtdemux \
        ! h264parse config-interval=-1 ! h264demuxer name=d \
        d.src_0 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t0 \
            t0.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x0.sink_enc xvdec name=x0 id=0 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn0.sink_0 nvstreammux name=m_rnn0 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t0.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=512 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn0.sink_0 nvstreammux name=m_fcn0 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=$1 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn0 d_fcn0.src_0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue \
                ! x0.sink_mask \
        d.src_1 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t1 \
            t1.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x1.sink_enc xvdec name=x1 id=1 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn1.sink_0 nvstreammux name=m_rnn1 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t1.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=512 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn1.sink_0 nvstreammux name=m_fcn1 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn1 d_fcn1.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x1.sink_mask \
        d.src_2 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t2 \
            t2.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x2.sink_enc xvdec name=x2 id=2 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn2.sink_0 nvstreammux name=m_rnn2 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t2.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=1024 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn2.sink_0 nvstreammux name=m_fcn2 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn2 d_fcn2.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x2.sink_mask \
        d.src_3 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t3 \
            t3.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x3.sink_enc xvdec name=x3 id=3 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn3.sink_0 nvstreammux name=m_rnn3 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t3.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=1024 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn3.sink_0 nvstreammux name=m_fcn3 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn3 d_fcn3.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x3.sink_mask \
        d.src_4 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t4 \
            t4.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x4.sink_enc xvdec name=x4 id=4 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn4.sink_0 nvstreammux name=m_rnn4 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t4.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=1024 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn4.sink_0 nvstreammux name=m_fcn4 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn4 d_fcn4.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x4.sink_mask \
        d.src_5 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t5 \
            t5.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x5.sink_enc xvdec name=x5 id=5 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn5.sink_0 nvstreammux name=m_rnn5 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t5.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=1024 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn5.sink_0 nvstreammux name=m_fcn5 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn5 d_fcn5.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x5.sink_mask \
        d.src_6 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t6 \
            t6.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x6.sink_enc xvdec name=x6 id=6 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn6.sink_0 nvstreammux name=m_rnn6 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t6.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=1024 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn6.sink_0 nvstreammux name=m_fcn6 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn6 d_fcn6.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x6.sink_mask \
        d.src_7 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
            ! tee name=t7 \
            t7.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x7.sink_enc xvdec name=x7 id=7 \
                    cc-threshold=$CC track-maxage=$MAXAGE track-minhits=$MINHITS debug=$DEBUG \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvv4l2decoder cudadec-memtype=0 bufapi-version=0 num-extra-surfaces=24 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! identity drop-buffer-flags=4096 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! m_rnn7.sink_0 nvstreammux name=m_rnn7 width=1280 height=720 batch-size=2 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/rnn/yolov4.txt \
                ! fakesink silent=TRUE \
            t7.src_1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! avdec_h264 max-threads=1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! metapreprocess \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvvideoconvert nvbuf-memory-type=2 output-buffers=1024 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! m_fcn7.sink_0 nvstreammux name=m_fcn7 width=80 height=180 batch-size=$1 \
                    buffer-pool-size=1024 nvbuf-memory-type=2 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvinfer config-file-path=/workspace/deepstream/config/fcn/tempunet-small.txt \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvsegvisual width=80 height=45 batch-size=$1 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! nvstreamdemux name=d_fcn7 d_fcn7.src_0 \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! 'video/x-raw(memory:NVMM),format=(string)RGBA'  \
                ! nvvideoconvert \
                ! 'video/x-raw,format=(string)RGBA'  \
                ! videoconvert \
                ! 'video/x-raw,format=(string)GRAY8'  \
                ! queue max-size-buffers=1024 max-size-bytes=0 max-size-time=0 \
                ! x7.sink_mask \

