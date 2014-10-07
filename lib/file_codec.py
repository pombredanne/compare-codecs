#!/usr/bin/python
"""A base class for all codecs using encode-to-file."""

import encoder
import os
import re
import subprocess

class FileCodec(encoder.Codec):
  """Base class for file-using codecs.
  Subclasses MUST define:
  - EncodeCommandLine
  - DecodeCommandLine
  - ResultData
  """
  def __init__(self, name, cache=None):
    super(FileCodec, self).__init__(name, cache)

  def Execute(self, parameters, bitrate, videofile, workdir):
    nullinput = open('/dev/null', 'r')
    encodedfile = '%s/%s.%s' % (workdir, videofile.basename, self.extension)
    commandline = self.EncodeCommandLine(
      parameters, bitrate, videofile, encodedfile)
                                         
    print commandline
    result = {}
    with open('/dev/null', 'r') as nullinput:
      subprocess_cpu_start = os.times()[2]
      returncode = subprocess.call(commandline, shell=True, stdin=nullinput)
      subprocess_cpu = os.times()[2] - subprocess_cpu_start
      print "Encode took %f seconds" % subprocess_cpu
      if returncode:
        raise Exception("Encode failed with returncode %d" % returncode)
      result['encode_cputime'] = subprocess_cpu
      bitrate = videofile.MeasuredBitrate(os.path.getsize(encodedfile))

    tempyuvfile = "%s/%stempyuvfile.yuv" % (workdir, videofile.basename)
    if os.path.isfile(tempyuvfile):
      print "Removing tempfile before decode:", tempyuvfile
      os.unlink(tempyuvfile)
    commandline = self.DecodeCommandLine(videofile, encodedfile, tempyuvfile)
    print commandline
    with open('/dev/null', 'r') as nullinput:
      subprocess_cpu_start = os.times()[2]
      returncode = subprocess.call(commandline, shell=True,
                                stdin=nullinput)
      subprocess_cpu = os.times()[2] - subprocess_cpu_start
      print "Decode took %f seconds" % subprocess_cpu
      result['decode_cputime'] = subprocess_cpu
      commandline = encoder.Tool("psnr") + " %s %s %d %d 9999" % (
        videofile.filename, tempyuvfile, videofile.width,
        videofile.height)
      print commandline
      psnr = subprocess.check_output(commandline, shell=True, stdin=nullinput)
    os.unlink(tempyuvfile)
    print "Bitrate", bitrate, "PSNR", psnr
    result['bitrate'] = int(bitrate)
    result['psnr'] = float(psnr)
    result.update(self.ResultData(encodedfile))

    return result

  # Below are the fallback implementations of the interfaces
  # that the subclasses have to implement.
  def EncodeCommandLine(self, parameters, bitrate, videofile, encodedfile):
    """This function returns the command line that should be executed
    in order to turn an YUV file into an encoded file."""
    # pylint: disable=W0613,R0201
    raise encoder.Error('EncodeCommandLine not defined')

  def DecodeCommandLine(self, videofile, encodedfile, yuvfile):
    """This function returns the command line that should be executed
    in order to turn an encoded file into an YUV file."""
    # pylint: disable=W0613,R0201
    raise encoder.Error('DecodeCommandLine not defined')

  def ResultData(self, encodedfile):
    """Returns additional fields that the codec may know how to generate."""
    # pylint: disable=W0613,R0201
    return {}

# Tools that may be called upon by the codec implementation if needed.
def MatroskaFrameInfo(encodedfile):
  # Run the mkvinfo tool across the file to get frame size info.
  commandline = 'mkvinfo -v %s' % encodedfile
  print commandline
  mkvinfo = subprocess.check_output(commandline, shell=True)
  frameinfo = []
  for line in mkvinfo.splitlines():
    m = re.search(r'Frame with size (\d+)', line)
    if m:
      # The mkvinfo tool gives frame size in bytes. We want bits.
      frameinfo.append({'size': int(m.group(1))*8})
      
  return frameinfo