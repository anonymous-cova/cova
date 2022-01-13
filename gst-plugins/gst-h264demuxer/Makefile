#enable this flag to use optimized confidencefilter plugin
#it can also be exported from command line
USE_OPTIMIZED_DSEXAMPLE?=0
CUDA_VER=11.1
ifeq ($(CUDA_VER),)
  $(error "CUDA_VER is not set")
endif
TARGET_DEVICE = $(shell gcc -dumpmachine | cut -f1 -d -)
CXX:= g++

SRCS:= gsth264demuxer.cpp

INCS:= $(wildcard *.h)
LIB:=libgsth264demuxer.so

NVDS_VERSION:=5.1

CFLAGS+= -fPIC -DDS_VERSION=\"5.1.0\" \
	 -I/usr/local/cuda-$(CUDA_VER)/include \
	 -I/opt/nvidia/deepstream/deepstream-$(NVDS_VERSION)/sources/includes

GST_INSTALL_DIR?=/opt/nvidia/deepstream/deepstream-$(NVDS_VERSION)/lib/gst-plugins/
LIB_INSTALL_DIR?=/opt/nvidia/deepstream/deepstream-$(NVDS_VERSION)/lib/

LIBS := -shared -Wl,-no-undefined \
	-L/usr/local/cuda-$(CUDA_VER)/lib64/ -lcudart -ldl \
	-lnppc -lnppig -lnpps -lnppicc -lnppidei \
	-L$(LIB_INSTALL_DIR) -lnvdsgst_helper -lnvdsgst_meta -lnvds_meta \
	-lnvbufsurface -lnvbufsurftransform -lnppist \
	-Wl,-rpath,$(LIB_INSTALL_DIR) -fpermissive

OBJS:= $(SRCS:.cpp=.o)
PKGS:= gstreamer-1.0 gstreamer-base-1.0 gstreamer-video-1.0

CFLAGS+=$(shell pkg-config --cflags $(PKGS)) \
		-DGST_USE_UNSTABLE_API -fpermissive -O2
LIBS+=$(shell pkg-config --libs $(PKGS))

all: $(LIB)

%.o: %.cpp $(INCS) Makefile
	@echo $(CFLAGS)
	$(CXX) -c -o $@ $(CFLAGS) $<

$(LIB): $(OBJS) Makefile
	@echo $(CFLAGS)
	$(CXX) -o $@ $(OBJS) $(LIBS)

install: $(LIB)
	cp -rv $(LIB) $(GST_INSTALL_DIR)

clean:
	rm -rf $(OBJS) $(LIB)
