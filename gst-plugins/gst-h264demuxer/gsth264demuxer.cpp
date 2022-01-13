#ifdef HAVE_CONFIG_H
#  include <config.h>
#endif

#include "gsth264demuxer.h"
#include <stdio.h>

GST_DEBUG_CATEGORY_STATIC (gst_h264demuxer_debug);
#define GST_CAT_DEFAULT gst_h264demuxer_debug

#define BUFFER_FLAG_FORMAT "s%s%s%s%s%s%s%s%s%s%s%s%s"
#define BUFFER_FLAG_ARGS(inbuf) \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_LIVE) ? "GST_BUFFER_FLAG_LIVE " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_DECODE_ONLY) ? "GST_BUFFER_FLAG_DECODE_ONLY " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_DISCONT) ? "GST_BUFFER_FLAG_DISCONT " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_RESYNC) ? "GST_BUFFER_FLAG_RESYNC " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_CORRUPTED) ? "GST_BUFFER_FLAG_CORRUPTED " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_MARKER) ? "GST_BUFFER_FLAG_MARKER " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_HEADER) ? "GST_BUFFER_FLAG_HEADER " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_GAP) ? "GST_BUFFER_FLAG_GAP " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_DROPPABLE) ? "GST_BUFFER_FLAG_DROPPABLE " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_DELTA_UNIT) ? "GST_BUFFER_FLAG_DELTA_UNIT " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_TAG_MEMORY) ? "GST_BUFFER_FLAG_TAG_MEMORY " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_SYNC_AFTER) ? "GST_BUFFER_FLAG_SYNC_AFTER " : "", \
            GST_BUFFER_FLAG_IS_SET((inbuf), GST_BUFFER_FLAG_NON_DROPPABLE) ? "GST_BUFFER_FLAG_NON_DROPPABLE " : ""

/* Enum to identify properties */
enum
{
  PROP_0,
  PROP_SILENT,
  PROP_ALLOC_PAD
};

static GstStaticPadTemplate sink_factory = GST_STATIC_PAD_TEMPLATE ("sink",
    GST_PAD_SINK,
    GST_PAD_ALWAYS,
    GST_STATIC_CAPS("video/x-h264, "                           \
                    "parsed=(boolean) true, "                  \
                    "stream-format=(string) { byte-stream }, " \
                    "alignment=(string) { au }")
    );

static GstStaticPadTemplate src_factory = GST_STATIC_PAD_TEMPLATE ("src_%u",
    GST_PAD_SRC,
    GST_PAD_REQUEST,
    GST_STATIC_CAPS_ANY
    );

/*---------------------------h264 demuxer pad--------------------------------*/
/* h264 pad class code (for request pad) */
GType gst_h264demuxer_pad_get_type (void);

#define GST_TYPE_H264DEMUXER_PAD \
  (gst_h264demuxer_pad_get_type())
#define GST_H264DEMUXER_PAD(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST ((obj), GST_TYPE_H264DEMUXER_PAD, GstH264DemuxerPad))
#define GST_H264DEMUXER_PAD_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST ((klass), GST_TYPE_H264DEMUXER_PAD, GstH264DemuxerPadClass))
#define GST_IS_H264DEMUXER_PAD(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE ((obj), GST_TYPE_H264DEMUXER_PAD))
#define GST_IS_H264DEMUXER_PAD_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE ((klass), GST_TYPE_H264DEMUXER_PAD))
#define GST_H264DEMUXER_PAD_CAST(obj) \
  ((GstH264DemuxerPad *)(obj))

typedef struct _GstH264DemuxerPad GstH264DemuxerPad;
typedef struct _GstH264DemuxerPadClass GstH264DemuxerPadClass;

struct _GstH264DemuxerPad
{
  GstPad parent;

  GList* gops;
  guint index;
  gboolean removed;
};

struct _GstH264DemuxerPadClass
{
  GstPadClass parent;
};

G_DEFINE_TYPE (GstH264DemuxerPad, gst_h264demuxer_pad, GST_TYPE_PAD);

static void
gst_h264demuxer_pad_class_init (GstH264DemuxerPadClass * klass)
{
}

static void
gst_h264demuxer_pad_reset (GstH264DemuxerPad * pad)
{ 
  pad->gops = NULL;
  pad->removed = FALSE;
}

static void
gst_h264demuxer_pad_init (GstH264DemuxerPad * pad)
{
  gst_h264demuxer_pad_reset (pad);
}

static GstPad *gst_h264demuxer_request_new_pad (GstElement * element,
    GstPadTemplate * temp, const gchar * unused, const GstCaps * caps);
static void gst_h264demuxer_release_pad (GstElement * element, GstPad * pad);
static gboolean gst_h264demuxer_src_activate_mode (GstPad * pad, GstObject * parent,
    GstPadMode mode, gboolean active);

static GParamSpec *pspec_alloc_pad = NULL;

/*------------------------h264 demuxer pad done-----------------------------*/

/* Define our element type. Standard GObject/GStreamer boilerplate stuff */
static GstElementClass *parent_class = NULL;

static void gst_h264demuxer_finalize(GObject *object);
static void gst_h264demuxer_set_property (GObject * object, guint prop_id,
                                          const GValue * value, GParamSpec * pspec);
static void gst_h264demuxer_get_property (GObject * object, guint prop_id,
                                          GValue * value, GParamSpec * pspec);

static gboolean gst_h264demuxer_sink_event (GstPad * pad, GstObject * parent,
                                            GstEvent * event);
static GstFlowReturn gst_h264demuxer_chain (GstPad * pad, GstObject * parent,
                                            GstBuffer * buf);

static void gst_h264demuxer_finalize(GObject *object) {
  GstH264Demuxer *h264demuxer = GST_H264DEMUXER (object);

  g_hash_table_unref (h264demuxer->pad_indexes);
  
  G_OBJECT_CLASS(parent_class)->finalize(object);
}

G_DEFINE_TYPE(GstH264Demuxer, gst_h264demuxer, GST_TYPE_ELEMENT);

/* GObject vmethod implementations */

/* initialize the plugin's class */
static void
gst_h264demuxer_class_init (GstH264DemuxerClass * klass)
{
  GObjectClass *gobject_class;
  GstElementClass *gstelement_class;

  gobject_class = (GObjectClass *) klass;
  gstelement_class = (GstElementClass *) klass;

  GST_DEBUG("gst_h264demuxer_class_init");

  parent_class = (GstElementClass *)g_type_class_peek_parent(klass);

  /* Overide base class functions */
  gobject_class->set_property = GST_DEBUG_FUNCPTR(gst_h264demuxer_set_property);
  gobject_class->get_property = GST_DEBUG_FUNCPTR(gst_h264demuxer_get_property);
  gobject_class->finalize = GST_DEBUG_FUNCPTR(gst_h264demuxer_finalize);

  /* Install properties */
  g_object_class_install_property (gobject_class, PROP_SILENT,
      g_param_spec_boolean ("silent", "Silent",
                            "Produce verbose output ?",
                            TRUE, G_PARAM_READWRITE));
  
  pspec_alloc_pad = g_param_spec_object ("alloc-pad", "Allocation Src Pad",
      "The pad ALLOCATION queries will be proxied to (DEPRECATED, has no effect)",
      GST_TYPE_PAD,
      (GParamFlags)(G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS | G_PARAM_DEPRECATED));
  g_object_class_install_property (gobject_class, PROP_ALLOC_PAD,
      pspec_alloc_pad);

  /* Set sink and src pad capabilities */
  gst_element_class_add_static_pad_template (gstelement_class, &src_factory);
  gst_element_class_add_static_pad_template (gstelement_class, &sink_factory);

  /* overide request pad function */
  gstelement_class->request_new_pad = GST_DEBUG_FUNCPTR (gst_h264demuxer_request_new_pad);
  gstelement_class->release_pad = GST_DEBUG_FUNCPTR (gst_h264demuxer_release_pad);
  
  /* Set metadata describing the element */
  gst_element_class_set_static_metadata (gstelement_class,
      "H264Demuxer Plugin",
      "H264Demuxer Plugin",
      DESCRIPTION, "Seungho Nam <shnam48@kaist.ac.kr>");
}

/* initialize the new element
 * instantiate pads and add them to element
 * set pad calback functions
 * initialize instance structure
 */
static void
gst_h264demuxer_init (GstH264Demuxer * h264demuxer)
{
  GST_DEBUG("gst_h264demuxer_init");

  /* sink pad */
  h264demuxer->sinkpad = gst_pad_new_from_static_template (&sink_factory, "sink");
  gst_pad_set_event_function (h264demuxer->sinkpad,
                              GST_DEBUG_FUNCPTR (gst_h264demuxer_sink_event));
  gst_pad_set_chain_function (h264demuxer->sinkpad,
                              GST_DEBUG_FUNCPTR (gst_h264demuxer_chain));
  GST_PAD_SET_PROXY_CAPS (h264demuxer->sinkpad);
  gst_element_add_pad (GST_ELEMENT (h264demuxer), h264demuxer->sinkpad);

  /* src pad is request pad */

  /* Initialize all property variables to default values */
  h264demuxer->silent = TRUE;
  h264demuxer->gops = NULL;
  h264demuxer->n_gops = 0;
  h264demuxer->bufs = NULL;
  h264demuxer->pad_indexes = g_hash_table_new(NULL, NULL);
  h264demuxer->next_pad_index = 0;
}

static gboolean
forward_sticky_events (GstPad * pad, GstEvent ** event, gpointer user_data)
{
  GstPad *srcpad = GST_PAD_CAST (user_data);
  GstFlowReturn ret;

  ret = gst_pad_store_sticky_event (srcpad, *event);
  if (ret != GST_FLOW_OK) {
    GST_DEBUG_OBJECT (srcpad, "storing sticky event %p (%s) failed: %s", *event,
        GST_EVENT_TYPE_NAME (*event), gst_flow_get_name (ret));
  }

  return TRUE;
}

static void
gst_h264demuxer_notify_alloc_pad (GstH264Demuxer * h264demuxer)
{
  g_object_notify_by_pspec ((GObject *) h264demuxer, pspec_alloc_pad);
}

/* when get new request pad, it will be called */
static GstPad *
gst_h264demuxer_request_new_pad (GstElement * element, GstPadTemplate * templ,
    const gchar * name_templ, const GstCaps * caps)
{
  gchar *name;
  GstPad *srcpad;
  GstH264Demuxer *h264demuxer;
  GstPadMode mode;
  gboolean res;
  guint index = 0;

  h264demuxer = GST_H264DEMUXER (element);

  GST_DEBUG_OBJECT (h264demuxer, "requesting pad");

  GST_OBJECT_LOCK (h264demuxer);

  if (name_templ && sscanf (name_templ, "src_%u", &index) == 1) {
    GST_INFO_OBJECT (h264demuxer, "name: %s (index %d)", name_templ, index);
    if (g_hash_table_contains (h264demuxer->pad_indexes, GUINT_TO_POINTER (index))) {
      GST_ERROR_OBJECT (element, "pad name %s is not unique", name_templ);
      GST_OBJECT_UNLOCK (h264demuxer);
      return NULL;
    }
    if (index >= h264demuxer->next_pad_index)
      h264demuxer->next_pad_index = index + 1;
  } else {
    index = h264demuxer->next_pad_index;
    
    while (g_hash_table_contains (h264demuxer->pad_indexes, GUINT_TO_POINTER (index)))
      index++;

    h264demuxer->next_pad_index = index + 1;
  }

  g_hash_table_insert (h264demuxer->pad_indexes, GUINT_TO_POINTER (index), NULL);

  name = g_strdup_printf ("src_%u", index);

  GST_DEBUG_OBJECT (h264demuxer, "<request pad> name: %s (index %d)", name, index);
  srcpad = GST_PAD_CAST (g_object_new (GST_TYPE_H264DEMUXER_PAD,
          "name", name, "direction", templ->direction, "template", templ,
          NULL));
  GST_H264DEMUXER_PAD_CAST (srcpad)->index = index;
  g_free (name);

  //mode = h264demuxer->sink_mode;
  mode = GST_PAD_MODE_PUSH; // consider only push mode

  GST_OBJECT_UNLOCK (h264demuxer);

  /* Always push mode. */
  switch (mode) {
    case GST_PAD_MODE_PULL:
      /* we already have a src pad in pull mode, and our pull mode can only be
         SINGLE, so fall through to activate this new pad in push mode */
    case GST_PAD_MODE_PUSH:
      res = gst_pad_activate_mode (srcpad, GST_PAD_MODE_PUSH, TRUE);
      break;
    default:
      res = TRUE;
      break;
  }

  if (!res)
    goto activate_failed;

  gst_pad_set_activatemode_function (srcpad,
      GST_DEBUG_FUNCPTR (gst_h264demuxer_src_activate_mode));
  //gst_pad_set_query_function (srcpad, GST_DEBUG_FUNCPTR (gst_h264demuxer_src_query));
  //gst_pad_set_getrange_function (srcpad,
  //    GST_DEBUG_FUNCPTR (gst_h264demuxer_src_get_range));
  GST_OBJECT_FLAG_SET (srcpad, GST_PAD_FLAG_PROXY_CAPS);
  /* Forward sticky events to the new srcpad */
  gst_pad_sticky_events_foreach (h264demuxer->sinkpad, forward_sticky_events, srcpad);
  gst_element_add_pad (GST_ELEMENT_CAST (h264demuxer), srcpad);

  return srcpad;

  /* ERRORS */
activate_failed:
  {
    gboolean changed = FALSE;

    GST_OBJECT_LOCK (h264demuxer);
    GST_DEBUG_OBJECT (h264demuxer, "warning failed to activate request pad");
    if (h264demuxer->srcpad == srcpad) {
      h264demuxer->srcpad = NULL;
      changed = TRUE;
    }
    GST_OBJECT_UNLOCK (h264demuxer);
    gst_object_unref (srcpad);
    if (changed) {
      gst_h264demuxer_notify_alloc_pad (h264demuxer);
    }
    return NULL;
  }
}

/* Change src pad mode.
 * But this plugin does not support pull mode.
 * So always pushmode, and This function will do nothing
 */
static gboolean
gst_h264demuxer_src_activate_mode (GstPad * pad, GstObject * parent, GstPadMode mode,
    gboolean active)
{
  GstH264Demuxer *h264demuxer;
  gboolean res;
  GstPad *sinkpad;

  h264demuxer = GST_H264DEMUXER (parent);

  switch (mode) {
    case GST_PAD_MODE_PULL:
    {
      GST_ERROR_OBJECT (h264demuxer, "This plugin does not support pull mode.");
      res = FALSE;
      break;
    }
    default:
      res = TRUE;
      break;
  }

  return res;

  /* ERRORS */
cannot_pull:
  {
    GST_OBJECT_UNLOCK (h264demuxer);
    GST_INFO_OBJECT (h264demuxer, "Cannot activate in pull mode, pull-mode "
        "set to NEVER");
    return FALSE;
  }
cannot_pull_multiple_srcs:
  {
    GST_OBJECT_UNLOCK (h264demuxer);
    GST_INFO_OBJECT (h264demuxer, "Cannot activate multiple src pads in pull mode, "
        "pull-mode set to SINGLE");
    return FALSE;
  }
sink_activate_failed:
  {
    GST_INFO_OBJECT (h264demuxer, "Failed to %sactivate sink pad in pull mode",
        active ? "" : "de");
    return FALSE;
  }
}

static void
gst_h264demuxer_release_pad (GstElement * element, GstPad * pad)
{
  GstH264Demuxer *h264demuxer;
  gboolean changed = FALSE;
  guint index;

  h264demuxer = GST_H264DEMUXER (element);

  GST_DEBUG_OBJECT (h264demuxer, "releasing pad");

  GST_OBJECT_LOCK (h264demuxer);
  index = GST_H264DEMUXER_PAD_CAST (pad)->index;
  /* mark the pad as removed so that future pad_alloc fails with NOT_LINKED. */
  GST_H264DEMUXER_PAD_CAST (pad)->removed = TRUE;
  if (h264demuxer->srcpad == pad) {
    h264demuxer->srcpad = NULL;
    changed = TRUE;
  }
  GST_OBJECT_UNLOCK (h264demuxer);

  gst_object_ref (pad);
  gst_element_remove_pad (GST_ELEMENT_CAST (h264demuxer), pad);

  gst_pad_set_active (pad, FALSE);

  gst_object_unref (pad);

  if (changed) {
    gst_h264demuxer_notify_alloc_pad (h264demuxer);
  }

  GST_OBJECT_LOCK (h264demuxer);
  g_hash_table_remove (h264demuxer->pad_indexes, GUINT_TO_POINTER (index));
  GST_OBJECT_UNLOCK (h264demuxer);
}

/* Function called when a property of the element is set. Standard
 * boilerplate.
 */
static void
gst_h264demuxer_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec)
{
  GstH264Demuxer *h264demuxer = GST_H264DEMUXER (object);
  
  switch (prop_id) {
    case PROP_SILENT:
      h264demuxer->silent = g_value_get_boolean (value);
      break;
    case PROP_ALLOC_PAD:
    {
      GstPad *pad = (GstPad *) g_value_get_object (value);
      GST_OBJECT_LOCK (pad);
      if (GST_OBJECT_PARENT (pad) == GST_OBJECT_CAST (object))
        h264demuxer->srcpad = pad;
      else
        GST_WARNING_OBJECT (object, "Tried to set alloc pad %s which"
            " is not my pad", GST_OBJECT_NAME (pad));
      GST_OBJECT_UNLOCK (pad);
      break;
    }
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

static void
gst_h264demuxer_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec)
{
  GstH264Demuxer *h264demuxer = GST_H264DEMUXER (object);

  switch (prop_id) {
    case PROP_SILENT:
      g_value_set_boolean (value, h264demuxer->silent);
      break;
    case PROP_ALLOC_PAD:
      g_value_set_object (value, h264demuxer->srcpad);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

/* GstElement vmethod implementations */

/* free function for each buffer */
static void
gst_h264demuxer_free_bufs(gpointer data){
  GstBuffer* buf = GST_BUFFER_CAST(data);
  gst_buffer_unref(buf);
}

static void
gst_h264demuxer_free_gop(gpointer data){
  GList* bufs = (GList*)data;
  g_list_free_full(bufs, gst_h264demuxer_free_bufs);
}

/* push one buffer function */
GstH264Demuxer* foreach_debug_h264demuxer;
static void
gst_h264demuxer_push_foreach_gop(gpointer buf, gpointer pad){
  GST_LOG_OBJECT(foreach_debug_h264demuxer, "%" GST_TIME_FORMAT " buf pushed", GST_TIME_ARGS(GST_BUFFER_CAST(buf)->pts));
  gst_pad_push(GST_PAD_CAST(pad), GST_BUFFER_CAST(buf));
}

/* when EOS split gops and push to each src pads */
static gboolean
gst_h264demuxer_split_and_push_buffer (GstH264Demuxer * h264demuxer)
{
  /* 
   * gops : GList*, List of gop
   * gop  : GList*, List of buf, data of gops
   * buf  : GstBuffer, data of gop
  */
  GList *pads, *gops;
  guint32 cookie;
  guint n_pads, n_gops, n_gops_per_pad;
  guint gop_s_index, gop_e_index;
  gboolean ret, cret;

  GST_OBJECT_LOCK (h264demuxer);
  pads = GST_ELEMENT_CAST (h264demuxer)->srcpads;
  gops = h264demuxer->gops;
  foreach_debug_h264demuxer = h264demuxer;
  /* special case for zero pads */
  if (G_UNLIKELY (!pads))
    goto no_pads;

  n_pads = GST_ELEMENT_CAST(h264demuxer)->numsrcpads;
  n_gops = h264demuxer->n_gops;

  /* special case for zero GOP */
  if(n_gops == 0)
    goto no_gops;
  
  /* special case which can not spread to all pads */
  if(n_gops < n_pads){
    GST_WARNING_OBJECT(h264demuxer, "Too many pads. Given Gop is %d, but Pad is %d. "\
                                    "Some pads are not work.", n_gops, n_pads);
    while(gops){
      GList *gop = (GList*)gops->data;
      GstPad *pad = GST_PAD_CAST(pads->data);
      gst_object_ref(pad);
      GST_OBJECT_UNLOCK(h264demuxer);

      /* push one gop and free list (not buffers) */
      GST_DEBUG_OBJECT(h264demuxer, "push to %s pad", GST_PAD_NAME(pad));
      g_list_foreach(gop, gst_h264demuxer_push_foreach_gop, (gpointer)pad);
      g_list_free(gop);

      GST_OBJECT_LOCK (h264demuxer);
      gst_object_unref(pad);
      pads = g_list_next(pads);
      gops = g_list_next(gops);
    }
    g_list_free(h264demuxer->gops);
    h264demuxer->gops = NULL;
    GST_OBJECT_UNLOCK(h264demuxer);

    return TRUE;
  }

  /* split gops */
  n_gops_per_pad = n_gops / n_pads;
  gop_s_index = 0;
  gop_e_index = n_gops_per_pad - 1;
  for(int i=0; i < n_pads; i++){
    GstPad *pad = GST_PAD_CAST(pads->data);
    gst_object_ref(pad);
    GST_OBJECT_UNLOCK(h264demuxer);

    /* set each pads' gops (start of gops list which each pads will push) */
    GST_DEBUG_OBJECT(h264demuxer, "push to %s pad (%dth gop ~ %dth gop)",
                    GST_PAD_NAME(pad), gop_s_index+1, gop_e_index+1);
    GST_H264DEMUXER_PAD_CAST(pad)->gops = g_list_nth(gops, gop_s_index);

    gop_s_index += n_gops_per_pad;
    gop_e_index += n_gops_per_pad;
    if(i == n_pads - 2)       // to last pads remain datas are pushed
      gop_e_index = n_gops - 1;
    
    GST_OBJECT_LOCK (h264demuxer);
    gst_object_unref(pad);
    pads = g_list_next(pads);
  }

  /* for each pad, push gop */
  pads = GST_ELEMENT_CAST (h264demuxer)->srcpads; // initailize pads index
  for(int i_gop_per_pad=0; i_gop_per_pad < n_gops_per_pad; i_gop_per_pad++){
    guint pad_index = 0;
    for(GList* pad_list = pads; pad_list; pad_list=g_list_next(pad_list)){
      GstPad *pad = GST_PAD_CAST(pad_list->data);
      gst_object_ref(pad);
      GST_OBJECT_UNLOCK(h264demuxer);

      GST_DEBUG_OBJECT(h264demuxer, "push %dth gop to %s pad",
                       n_gops_per_pad * pad_index + i_gop_per_pad + 1,
                       GST_PAD_NAME(pad));
      GList* gop = (GList*)(GST_H264DEMUXER_PAD_CAST(pad)->gops->data);
      
      g_list_foreach(gop, gst_h264demuxer_push_foreach_gop, (gpointer)pad);
      g_list_free(gop);

      GST_H264DEMUXER_PAD_CAST(pad)->gops = g_list_next(GST_H264DEMUXER_PAD_CAST(pad)->gops);

      GST_OBJECT_LOCK (h264demuxer);
      gst_object_unref(pad);
      pad_index++;
    }
  }

  /* there are remain gops */
  gops = g_list_nth(gops, n_gops_per_pad * n_pads);
  if(gops){
    guint gop_index = n_gops_per_pad * n_pads + 1;
    GstPad *pad = GST_PAD_CAST(g_list_last(pads)->data);
    gst_object_ref(pad);
    GST_OBJECT_UNLOCK(h264demuxer);

    /* push n_gops_per_pad gop and free list (not buffers) */
    while(gops){
      GST_DEBUG_OBJECT(h264demuxer, "push %dth gop to %s pad",
                       gop_index,
                       GST_PAD_NAME(pad));
      GList *gop = (GList*)gops->data;

      /* push one gop and free list (not buffers) */
      g_list_foreach(gop, gst_h264demuxer_push_foreach_gop, (gpointer)pad);
      g_list_free(gop);

      gops = g_list_next(gops);
      gop_index++;
    }

    GST_OBJECT_LOCK (h264demuxer);
    gst_object_unref(pad);
  }
  g_list_free(h264demuxer->gops);
  h264demuxer->gops = NULL;
  GST_OBJECT_UNLOCK(h264demuxer);
  
  return TRUE;

  /* ERRORS */
no_pads:
  {
    GST_ERROR_OBJECT (h264demuxer, "there are no pads");
    ret = FALSE;
    goto end;
  }
no_gops:
  {
    GST_ERROR_OBJECT (h264demuxer, "there are no available gops");
    ret = FALSE;
    goto end;
  }
end:
  {
    /* remove all gops */
    if(h264demuxer->gops){
      g_list_free_full(h264demuxer->gops, gst_h264demuxer_free_gop);
      h264demuxer->gops = NULL;
    }

    GST_OBJECT_UNLOCK (h264demuxer);
    return ret;
  }
}

/* this function handles sink events */
static gboolean
gst_h264demuxer_sink_event (GstPad * pad, GstObject * parent,
    GstEvent * event)
{
  GstH264Demuxer *h264demuxer = GST_H264DEMUXER (parent);
  gboolean ret = TRUE;

  GST_LOG_OBJECT (h264demuxer, "Received %s event: %" GST_PTR_FORMAT,
      GST_EVENT_TYPE_NAME (event), event);

  switch (GST_EVENT_TYPE (event)) {
    case GST_EVENT_EOS:
      /* append last GOP chunk */
      if(h264demuxer->bufs){
        h264demuxer->gops = g_list_append(h264demuxer->gops, (gpointer)h264demuxer->bufs);
        h264demuxer->bufs = NULL;
        h264demuxer->n_gops++;
        GST_DEBUG_OBJECT(h264demuxer,
                    "%uth gop<LAST> is appended",
                    h264demuxer->n_gops);
      }
      GST_INFO_OBJECT(h264demuxer,
                    "EOS event is detected. Push data to each pad.");
      /* split and push data to each pad */
      gst_h264demuxer_split_and_push_buffer(h264demuxer);
      GST_INFO_OBJECT(h264demuxer,
                    "Datas are pushed to each pad.");
      /* foward EOS to each src pad. by using default pad event */
    default:
      ret = gst_pad_event_default (pad, parent, event);
      break;
  }
  return ret;
}

/* chain function
 * this function does the actual processing
 */
static GstFlowReturn
gst_h264demuxer_chain (GstPad * pad, GstObject * parent, GstBuffer * buf)
{
  GstH264Demuxer *h264demuxer = GST_H264DEMUXER (parent);
  GstFlowReturn ret = GST_FLOW_OK;

  GST_LOG_OBJECT(h264demuxer, "%" GST_TIME_FORMAT " buf arrive", GST_TIME_ARGS(GST_BUFFER_CAST(buf)->pts));
  GST_LOG_OBJECT(h264demuxer, "%" BUFFER_FLAG_FORMAT, BUFFER_FLAG_ARGS(buf));

  /* Detect IDR. make new GOP */
  if (!GST_BUFFER_FLAG_IS_SET(buf, GST_BUFFER_FLAG_DELTA_UNIT)){
    GST_BUFFER_FLAG_SET(buf, GST_BUFFER_FLAG_DISCONT);
    if(h264demuxer->bufs){
      h264demuxer->gops = g_list_append(h264demuxer->gops, (gpointer)h264demuxer->bufs);
      h264demuxer->n_gops++;

      GST_DEBUG_OBJECT(h264demuxer,
                    "%uth gop is appended",
                    h264demuxer->n_gops);
    }
    h264demuxer->bufs = NULL; // reset gop buf
  }

  /* append buffer to list */
  h264demuxer->bufs = g_list_append(h264demuxer->bufs, (gpointer)buf);

  return ret;
}


/* entry point to initialize the plug-in
 * initialize the plug-in itself
 * register the element factories and other features
 */
static gboolean
h264demuxer_plugin_init (GstPlugin * plugin)
{
  GST_DEBUG_CATEGORY_INIT(gst_h264demuxer_debug, "h264demuxer", 0, "h264demuxer plugin");
  return gst_element_register(plugin, "h264demuxer", GST_RANK_PRIMARY,
                              GST_TYPE_H264DEMUXER);
}

/* gstreamer looks for this structure to register plugins
 *
 * exchange the string 'Template plugin' with your plugin description
 */
GST_PLUGIN_DEFINE (GST_VERSION_MAJOR, GST_VERSION_MINOR, h264demuxer, DESCRIPTION,
                   h264demuxer_plugin_init, VERSION, LICENSE, BINARY_PACKAGE, URL)
