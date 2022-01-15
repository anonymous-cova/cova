import sys, os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
from timeit import default_timer as timer


class CovaPipeline:
    def __init__(self, config, f=None, debug=False):
        # initialize GStreamer
        Gst.init(sys.argv)

        self.f = f
        self.queue_size = config['queue_size']
        self.config = config
        self.debug = debug

        self.state = Gst.State.NULL
        self.loop = GLib.MainLoop()
        self.pipeline = Gst.Pipeline.new("pipeline")

        self.filesrc = Gst.ElementFactory.make("filesrc", "file-source")
        self.filesrc.set_property("location", config['input_file'])

        self.qtdemux = Gst.ElementFactory.make("qtdemux", "qt-demux")
        self.qtdemux.connect("pad-added", self.on_qtdemux_pad_added)


        self.pipeline.add(self.filesrc)
        self.pipeline.add(self.qtdemux)

        self.filesrc.link(self.qtdemux)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.covas = []
        self.nvdecs = []

    def init_upto_last(self):
        config = self.config
        last_elems = []
        last = config['last']

        if last == 'avdec-only':
            avdec = Gst.ElementFactory.make("avdec_h264")
            avdec.set_property("max-threads", config['num_entdec'])
            self.pipeline.add(avdec)
            self.h264parse.link(avdec)
            return [avdec]

        if last == 'nvdec-only':
            nvdec = Gst.ElementFactory.make("nvv4l2decoder")
            nvdec.set_property("cudadec-memtype", 0)
            nvdec.set_property("num-extra-surfaces", config['nvdec_num_extra_surfaces'])
            self.pipeline.add(nvdec)
            self.h264parse.link(nvdec)
            return [nvdec]

        if last == 'nvinfer-only':
            nvdec = Gst.ElementFactory.make("nvv4l2decoder")
            nvdec.set_property("cudadec-memtype", 0)
            nvdec.set_property("num-extra-surfaces", config['nvdec_num_extra_surfaces'])
            nvdec.set_property("drop-frame-interval", 30)
            self.pipeline.add(nvdec)
            self.h264parse.link(nvdec)

            nvstreammux = Gst.ElementFactory.make("nvstreammux")
            nvstreammux.set_property("width", config['width'])
            nvstreammux.set_property("height", config['height'])
            nvstreammux.set_property("batch-size", config['dnn_batch_size'])
            nvstreammux.set_property("buffer-pool-size", config['dnn_pool_size'])
            nvstreammux.set_property("nvbuf-memory-type", 2)
            self.pipeline.add(nvstreammux)

            nvdec.get_static_pad('src').link(nvstreammux.get_request_pad(f'sink_0'))

            nvinfer = Gst.ElementFactory.make("nvinfer")
            nvinfer.set_property("config-file-path", config['nvinfer_dnn_config'])
            self.pipeline.add(nvinfer)
            nvstreammux.link(nvinfer)

            return [nvinfer]


        self.h264demuxer = Gst.ElementFactory.make("h264demuxer", "h264-demux")
        self.pipeline.add(self.h264demuxer)

        self.h264parse.link(self.h264demuxer)

        num_entdec = config['num_entdec']

        self.tees = []
        for i in range(num_entdec):
            tee = Gst.ElementFactory.make("tee")
            self.pipeline.add(tee)
            self.h264demuxer.get_request_pad("src_%u").link(tee.get_static_pad("sink"))
            self.tees.append(tee)

            entdec = Gst.ElementFactory.make("avdec_h264")
            entdec.set_property("max-threads", 1)
            self.pipeline.add(entdec)
            queue = self.prepend_queue(entdec)

            tee.get_request_pad("src_%u").link(queue.get_static_pad("sink"))

            if config['entdec_add_queue']:
                entdec = self.append_queue(entdec)
            last_elems.append(entdec)

        if last == 'entdec':
            return last_elems

        for i in range(len(last_elems)):
            entdec = last_elems[i]
            metapreprocess = Gst.ElementFactory.make("metapreprocess")
            metapreprocess.set_property("timestep", config['timestep'])
            self.pipeline.add(metapreprocess)
            entdec.link(metapreprocess)

            if config['metapreprocess_add_queue']:
                metapreprocess = self.append_queue(metapreprocess)
            last_elems[i] = metapreprocess

        if last == 'metapreprocess':
            return last_elems

        for i in range(len(last_elems)):
            metapreprocess = last_elems[i]

            nvvideoconvert = Gst.ElementFactory.make("nvvideoconvert")
            nvvideoconvert.set_property("nvbuf-memory-type", 2)
            nvvideoconvert.set_property(
                    "output-buffers", config['nvvideoconvert_up_output_buffers']
                    )
            capsfilter = Gst.ElementFactory.make("capsfilter")
            caps = Gst.Caps.from_string("video/x-raw(memory:NVMM),format=(string)RGBA")
            capsfilter.set_property("caps", caps)

            self.pipeline.add(nvvideoconvert)
            self.pipeline.add(capsfilter)

            metapreprocess.link(nvvideoconvert)
            nvvideoconvert.link(capsfilter)
            if config['nvvideoconvert_up_add_queue']:
                capsfilter = self.append_queue(capsfilter)
            last_elems[i] = capsfilter

        if last == 'nvvideoconvert_up':
            return last_elems

        num_mask = config['num_mask']
        assert num_entdec % num_mask == 0
        dec_per_mask = num_entdec // num_mask

        idx = 0
        prev_elems = last_elems
        last_elems = []
        for _ in range(num_mask):
            nvstreammux = Gst.ElementFactory.make("nvstreammux")
            nvstreammux.set_property("width", config['width'] // 16)
            nvstreammux.set_property("height", config['height'] // 16  * config['timestep'])
            nvstreammux.set_property("batch-size", config['mask_batch_size'])
            nvstreammux.set_property("buffer-pool-size", config['mask_pool_size'])
            nvstreammux.set_property("batched-push-timeout", config['mask_batched_push_timeout'])
            nvstreammux.set_property("nvbuf-memory-type", 2)

            self.pipeline.add(nvstreammux)

            for i in range(dec_per_mask):
                nvvideoconvert = prev_elems[idx]
                idx += 1
                nvvideoconvert.get_static_pad('src').link(nvstreammux.get_request_pad(f'sink_{i}'))

            if config['nvstreammux_mask_add_queue']:
                nvstreammux = self.append_queue(nvstreammux)
            last_elems.append(nvstreammux)

        if last == 'nvstreammux_mask':
            return last_elems

        for i in range(len(last_elems)):
            nvstreammux = last_elems[i]

            nvinfer = Gst.ElementFactory.make("nvinfer")
            nvinfer.set_property("config-file-path", config['nvinfer_mask_config'])
            self.pipeline.add(nvinfer)
            nvstreammux.link(nvinfer)

            if config['nvinfer_mask_add_queue']:
                nvinfer = self.append_queue(nvinfer)

            last_elems[i] = nvinfer

        if last == 'nvinfer_mask':
            return last_elems

        prev_elems = last_elems
        last_elems = []
        for nvinfer in prev_elems:
            nvstreamdemux = self.create_and_append(nvinfer, "nvstreamdemux")

            for i in range(dec_per_mask):
                capsfilter = Gst.ElementFactory.make("capsfilter")
                caps = Gst.Caps.from_string("video/x-raw(memory:NVMM),format=(string)RGBA")
                capsfilter.set_property("caps", caps)
                self.pipeline.add(capsfilter)

                nvstreamdemux.get_request_pad(f"src_{i}").link(capsfilter.get_static_pad("sink"))
                if config['nvstreamdemux_mask_add_queue']:
                    capsfilter = self.append_queue(capsfilter)

                last_elems.append(capsfilter)

        if last == 'nvstreamdemux_mask':
            return last_elems

        for i in range(len(last_elems)):
            maskcopy = self.create_and_append(last_elems[i], 'maskcopy')

            if config['maskcopy_add_queue']:
                maskcopy = self.append_queue(maskcopy)

            last_elems[i] = maskcopy

        if last == 'maskcopy':
            return last_elems

        assert len(last_elems) == len(self.tees)

        for i in range(len(last_elems)):
            maskcopy = last_elems[i]
            tee = self.tees[i]

            cova = Gst.ElementFactory.make("cova")
            cova.set_property("alpha", config["cova_alpha"])
            cova.set_property("beta", config["cova_beta"])
            cova.set_property("infer-i", config["cova_infer_i"])
            cova.set_property("cc-threshold", config["cova_cc_threshold"])
            cova.set_property("sort-iou", config["cova_sort_iou"])
            cova.set_property("sort-maxage", config["cova_sort_maxage"])
            cova.set_property("sort-minhits", config["cova_sort_minhits"])
            cova.set_property("port", config["cova_port"])
            self.pipeline.add(cova)
            self.covas.append(cova)

            maskcopy.get_static_pad("src").link(cova.get_static_pad("sink_mask"))

            queue = Gst.ElementFactory.make("queue")
            queue.set_property("max-size-buffers", 0)
            queue.set_property("max-size-bytes", 0)
            queue.set_property("max-size-time", 0)
            self.pipeline.add(queue)

            tee.get_request_pad("src_%u").link(queue.get_static_pad("sink"))
            queue.get_static_pad("src").link(cova.get_static_pad("sink_enc"))

            if config['cova_add_queue']:
                cova = self.append_queue(cova)

            last_elems[i] = cova

        if last == 'cova':
            return last_elems

        num_nvdec = config['num_nvdec']
        assert num_entdec == len(last_elems)
        assert num_entdec % num_nvdec == 0
        ent_per_nv = num_entdec // num_nvdec

        idx = 0
        prev_elems = last_elems
        last_elems = []
        for _ in range(num_nvdec):
            funnel = Gst.ElementFactory.make("funnel")
            self.pipeline.add(funnel)

            for _ in range(ent_per_nv):
                cova = prev_elems[idx]
                idx += 1
                cova.get_static_pad('src').link(funnel.get_request_pad(f'sink_%u'))

            if config['funnel_add_queue']:
                funnel = self.append_queue(funnel)
            last_elems.append(funnel)

        if last == 'funnel':
            return last_elems

        for i in range(len(last_elems)):
            funnel = last_elems[i]
            nvdec = Gst.ElementFactory.make("nvv4l2decoder")
            nvdec.set_property("cudadec-memtype", 0)
            nvdec.set_property("num-extra-surfaces", config['nvdec_num_extra_surfaces'])
            self.pipeline.add(nvdec)
            self.nvdecs.append([nvdec, False])
            funnel.link(nvdec)

            if config['nvdec_add_queue']:
                nvdec = self.append_queue(nvdec)
            last_elems[i] = nvdec

        if last == 'nvdec':
            return last_elems

        for i in range(len(last_elems)):
            nvdec = last_elems[i]
            identity = Gst.ElementFactory.make("identity")
            identity.set_property("drop-buffer-flags", 4096)
            self.pipeline.add(identity)
            nvdec.link(identity)

            if config['identity_add_queue']:
                identity = self.append_queue(identity)
            last_elems[i] = identity

        if last == 'identity':
            return last_elems


        # nvpts = self.create_and_append(identity, "nvpts")
        # if config['nvpts_add_queue']:
        #     nvpts = self.append_queue(nvpts)

        # if last == 'nvpts':
        #     return [nvpts]

        num_dnn = config['num_dnn']
        assert len(last_elems) == num_nvdec
        assert num_nvdec % num_dnn == 0
        dec_per_dnn = num_nvdec // num_dnn

        idx = 0
        prev_elems = last_elems
        last_elems = []
        for _ in range(num_dnn):
            nvstreammux = Gst.ElementFactory.make("nvstreammux")
            nvstreammux.set_property("width", config['width'])
            nvstreammux.set_property("height", config['height'])
            nvstreammux.set_property("batch-size", config['dnn_batch_size'])
            nvstreammux.set_property("buffer-pool-size", config['dnn_pool_size'])
            nvstreammux.set_property("nvbuf-memory-type", 2)
            nvstreammux.set_property("batched-push-timeout", config['dnn_batched_push_timeout'])
            self.pipeline.add(nvstreammux)

            for i in range(dec_per_dnn):
                identity = prev_elems[idx]
                idx += 1
                identity.get_static_pad('src').link(nvstreammux.get_request_pad(f'sink_{i}'))

            if config['nvstreammux_dnn_add_queue']:
                nvstreammux = self.append_queue(nvstreammux)
            last_elems.append(nvstreammux)

        if last == 'nvstreammux_dnn':
            return last_elems

        for i in range(len(last_elems)):
            nvstreammux = last_elems[i]
            nvinfer = Gst.ElementFactory.make("nvinfer")
            nvinfer.set_property("config-file-path", config['nvinfer_dnn_config'])
            self.pipeline.add(nvinfer)
            nvstreammux.link(nvinfer)

            if config['nvinfer_dnn_add_queue']:
                nvinfer = self.append_queue(nvinfer)

            last_elems[i] = nvinfer

        if last == 'nvinfer_dnn':
            return last_elems

        # if config['cova_port'] == 0 or config['tcpprobe_port'] == 0:
        #     return last_elems

        prev_elems = last_elems
        last_elems = []
        for nvinfer in prev_elems:
            nvstreamdemux = self.create_and_append(nvinfer, "nvstreamdemux")

            for i in range(dec_per_dnn):
                capsfilter = Gst.ElementFactory.make("capsfilter")
                caps = Gst.Caps.from_string("video/x-raw(memory:NVMM),format=(string)NV12")
                capsfilter.set_property("caps", caps)
                self.pipeline.add(capsfilter)

                nvstreamdemux.get_request_pad(f"src_{i}").link(capsfilter.get_static_pad("sink"))
                if config['nvstreamdemux_dnn_add_queue']:
                    capsfilter = self.append_queue(capsfilter)

                last_elems.append(capsfilter)

        if last == 'nvstreamdemux_dnn':
            return capsfilter

        # probefilter = self.create_and_append(capsfilter, 'probefilter')
        # if config['probefilter_add_queue']:
        #     probefilter = self.append_queue(probefilter)

        # if last == 'probefilter':
        #     return [probefilter]

        for i in range(len(last_elems)):
            capsfilter = last_elems[i]
            tcpprobe = Gst.ElementFactory.make("tcpprobe")
            tcpprobe.set_property("port", config['tcpprobe_port'])
            self.pipeline.add(tcpprobe)
            capsfilter.link(tcpprobe)

            if config['tcpprobe_add_queue']:
                tcpprobe = self.append_queue(tcpprobe)
            last_elems[i] = tcpprobe

        if last == 'tcpprobe':
            return last_elems

        assert last == 'full'
        assert len(last_elems) == num_nvdec

        return last_elems


    # TODO: Handle property as well with kwargs
    def create_and_append(self, prev_elem, elem_name):
        next_elem = Gst.ElementFactory.make(elem_name)
        self.pipeline.add(next_elem)
        prev_elem.link(next_elem)
        return  next_elem

    def prepend_queue(self, elem):
        queue = Gst.ElementFactory.make("queue")
        queue.set_property("max-size-buffers", self.queue_size)
        queue.set_property("max-size-bytes", 0)
        queue.set_property("max-size-time", 0)
        self.pipeline.add(queue)

        queue.link(elem)
        return queue

    def append_queue(self, elem):
        queue = Gst.ElementFactory.make("queue")
        queue.set_property("max-size-buffers", self.queue_size)
        queue.set_property("max-size-bytes", 0)
        queue.set_property("max-size-time", 0)
        self.pipeline.add(queue)

        elem.link(queue)
        return queue

    def append_sink(self, elem):
        sink = Gst.ElementFactory.make(self.config['sink'])
        if self.config['sink'] == 'filesink':
            sink.set_property("location", "/tmp/debug.dump")
        self.pipeline.add(sink)
        elem.link(sink)

    def on_message(self, bus, message):
        t = message.type
        if message.src == self.pipeline:
            if t == Gst.MessageType.EOS:
                self.stop_time = timer()
                print('Stopped Running Pipeline')
                self.terminate()
                self.loop.quit()

            elif t == Gst.MessageType.STATE_CHANGED:
                old, new, _ = Gst.Message.parse_state_changed(message)
                if old == Gst.State.PAUSED and new == Gst.State.PLAYING:
                    self.start_time = timer()
                    print('Started Running Pipeline')

        if t == Gst.MessageType.STREAM_STATUS:
            s_t, s_src = Gst.Message.parse_stream_status(message)
            if s_t == Gst.StreamStatusType.LEAVE:
                for i in range(len(self.nvdecs)):
                    if self.nvdecs[i][0] == s_src:
                        self.nvdecs[i][1] = True

                rets = [d[1] for d in self.nvdecs]
                if self.debug:
                    print(rets)

                if len(self.nvdecs) > 4:
                    # Bypass for now
                    if sum(rets) >= len(rets) - 4:
                        self.stop_time = timer()
                        print('Stopped Running Pipeline by NVDEC')
                        self.terminate(force=True)
                        self.loop.quit()

        if self.debug:
            # print(f'{t} from {message.src.get_name()}')
            print(f'{t} from {message.src}')
            if t == Gst.MessageType.EOS:
                print('EOS from', message.src)
            if t == Gst.MessageType.STREAM_STATUS:
                print(Gst.Message.parse_stream_status(message))


    def terminate(self, force=False):
        elapsed_sec = self.stop_time - self.start_time
        print('Elapsed seconds:', elapsed_sec)
        if self.f is not None:
            print('Elapsed seconds:', elapsed_sec, file=self.f)

        if self.covas:
            dropped = 0
            decoded_dependency = 0
            decoded_inference = 0
            for c in self.covas:
                dropped += c.get_property("dropped")
                decoded_dependency += c.get_property("decoded_dependency")
                decoded_inference += c.get_property("decoded_inference")

            decoded = decoded_dependency + decoded_inference
            total = dropped + decoded

            print('CoVA dropped:', dropped)
            print('CoVA decoded dependency:', decoded_dependency)
            print('CoVA decoded inference:', decoded_inference)
            print(f'CoVA decoding rate: {decoded / total :.4}')
            print(f'CoVA inference rate: {decoded_inference / total :.4}')
            if self.f is not None:
                print('CoVA dropped:', dropped, file=self.f)
                print('CoVA decoded dependency:', decoded_dependency, file=self.f)
                print('CoVA decoded inference:', decoded_inference, file=self.f)
                print(f'CoVA decoding rate: {decoded / total * 100 :.2}%', file=self.f)
                print(f'CoVA inference rate: {decoded_inference * 100 / total :.2}%', file=self.f)
                self.f.flush()

        if force:
            exit(0)

        # free resources
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None

    def on_qtdemux_pad_added(self, qtdemux, pad):
        # print('Hi', pad.caps().to_string())
        # print(qtdemux, pad, user_data)
        if pad.get_current_caps().to_string().startswith('video/x-h264'):
            self.h264parse = Gst.ElementFactory.make("h264parse", "h264-parse")
            self.h264parse.set_property("config-interval", -1)
            self.pipeline.add(self.h264parse)
            pad.link(self.h264parse.get_static_pad("sink"))

            last_elems = self.init_upto_last()
            for el in last_elems:
                self.append_sink(el)

            self.pipeline.set_state(Gst.State.PLAYING)


    '''
    # this function is called periodically to refresh the GUI
    def refresh_ui(self):
        current = -1

        if self.state < Gst.State.PAUSED:
            return True

        # if we don't know it yet, query the stream duration
        if self.duration == Gst.CLOCK_TIME_NONE:
            ret, self.duration = self.playbin.query_duration(Gst.Format.TIME)
            if not ret:
                print("ERROR: Could not query current duration")
            else:
                # set the range of the slider to the clip duration (in seconds)
                self.slider.set_range(0, self.duration / Gst.SECOND)

        ret, current = self.playbin.query_position(Gst.Format.TIME)
        if ret:
            # block the "value-changed" signal, so the on_slider_changed
            # callback is not called (which would trigger a seek the user
            # has not requested)
            self.slider.handler_block(self.slider_update_signal_id)

            # set the position of the slider to the current pipeline position
            # (in seconds)
            self.slider.set_value(current / Gst.SECOND)

            # enable the signal again
            self.slider.handler_unblock(self.slider_update_signal_id)

        return True
    '''

    def start(self):
        ret = self.pipeline.set_state(Gst.State.PAUSED)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("ERROR: Unable to set the pipeline to the playing state")
            sys.exit(1)
        # GLib.timeout_add_seconds(1, self.refresh_ui)
        self.loop.run()

if __name__ == '__main__':
    import argparse
    import yaml

    parser = argparse.ArgumentParser()
    parser.add_argument("CONFIG_FILE")
    parser.add_argument("--debug", action='store_true', default=False)
    args = parser.parse_args()

    config = yaml.safe_load(open(args.CONFIG_FILE))
    CovaPipeline(config, debug=args.debug).start()

