#ifndef __GST_H264DEMUXER_H__
#define __GST_H264DEMUXER_H__

#include <gst/gst.h>

/* Package and library details required for plugin_init */
#define PACKAGE "h264demuxer"
#define VERSION "1.0"
#define LICENSE "LGPL"
#define DESCRIPTION "Plugin for h264demuxer"
#define BINARY_PACKAGE "H264Demuxer"
#define URL "https://github.com/kaist-casys-internal/xvdec"

G_BEGIN_DECLS

/* Standard boilerplate stuff */
typedef struct _GstH264Demuxer GstH264Demuxer;
typedef struct _GstH264DemuxerClass GstH264DemuxerClass;

/* Standard boilerplate stuff */
#define GST_TYPE_H264DEMUXER (gst_h264demuxer_get_type())
#define GST_H264DEMUXER(obj)                                                         \
  (G_TYPE_CHECK_INSTANCE_CAST((obj), GST_TYPE_H264DEMUXER, GstH264Demuxer))
#define GST_H264DEMUXER_CLASS(klass)                                                 \
  (G_TYPE_CHECK_CLASS_CAST((klass), GST_TYPE_H264DEMUXER, GstH264DemuxerClass))
#define GST_H264DEMUXER_GET_CLASS(obj)                                               \
  (G_TYPE_INSTANCE_GET_CLASS((obj), GST_TYPE_H264DEMUXER, GstH264DemuxerClass))
#define GST_IS_H264DEMUXER(obj) (G_TYPE_CHECK_INSTANCE_TYPE((obj), GST_TYPE_H264DEMUXER))
#define GST_IS_H264DEMUXER_CLASS(klass)                                              \
  (G_TYPE_CHECK_CLASS_TYPE((klass), GST_TYPE_H264DEMUXER))
#define GST_H264DEMUXER_CAST(obj) ((GstH264Demuxer *)(obj))

struct _GstH264Demuxer
{
  GstElement element;

  GstPad *sinkpad, *srcpad;

  /* properties for request pad */
  GHashTable     *pad_indexes;
  guint           next_pad_index;

  gboolean silent;

  /* buffer */
  GList* gops; // gops will contain bufs
  guint n_gops;
  GList* bufs;
};

// Boiler plate stuff
struct _GstH264DemuxerClass {
  GstElementClass parent_class;
};

GType gst_h264demuxer_get_type(void);

G_END_DECLS

#endif /* __GST_H264DEMUXER_H__ */